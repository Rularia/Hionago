import requests
import os
import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTextEdit, QFileDialog, QMessageBox, QGroupBox, QApplication)
from PySide6.QtCore import Qt

class VoiceExpert(QWidget):
    def __init__(self, parent_settings=None):
        super().__init__()
        self.setWindowTitle("语音资产全自动工作站 (ASR + 克隆)")
        self.resize(1100, 800)
        self.parent_settings = parent_settings 
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 指令区：保留网页端辅助，备不时之需
        prompt_gb = QGroupBox("🤖 ASR 助手 (支持全语种自动识别)")
        prompt_lay = QVBoxLayout(prompt_gb)
        self.guide_label = QLabel("模式：自动识别。如果识别不准，可以点击下方按钮复制 Prompt 去网页端人工复核。")
        btn_copy_prompt = QPushButton("📋 复制 AI 提示词 (网页端辅助用)")
        btn_copy_prompt.clicked.connect(self.copy_prompt)
        prompt_lay.addWidget(self.guide_label)
        prompt_lay.addWidget(btn_copy_prompt)
        layout.addWidget(prompt_gb)

        # 2. 表格区：展示多段音频任务
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["本地路径", "角色名", "语气(Key)", "音频原文 (ASR自动填充)", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # 3. 操作区
        btn_lay = QHBoxLayout()
        btn_add = QPushButton("➕ 添加多段音频文件")
        btn_add.clicked.connect(self.add_files)
        
        self.btn_asr = QPushButton("🎙️ 批量识别原文 (SenseVoiceSmall)")
        self.btn_asr.setStyleSheet("background-color: #f39c12; color: white;")
        self.btn_asr.clicked.connect(self.batch_asr)

        self.btn_upload = QPushButton("🚀 一键上传并生成 speech 字符串")
        self.btn_upload.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_upload.clicked.connect(self.handle_batch_upload)

        btn_lay.addWidget(btn_add)
        btn_lay.addWidget(self.btn_asr)
        btn_lay.addWidget(self.btn_upload)
        layout.addLayout(btn_lay)

        # 4. 结果区
        self.output_res = QTextEdit()
        self.output_res.setReadOnly(True)
        self.output_res.setPlaceholderText("最终生成的 speech:角色:语气:ID 将在这里显示...")
        layout.addWidget(self.output_res)

    def get_api_key(self):
        if self.parent_settings and hasattr(self.parent_settings, 'api_key'):
            return self.parent_settings.api_key.text().strip()
        return ""

    def copy_prompt(self):
        prompt = "我将上传音频，请识别其原文（无论何种语言），并给出一个英文单词描述其语气(情绪)。格式：\n原文：xxxx\n语气：xxxx"
        QApplication.clipboard().setText(prompt)
        QMessageBox.information(self, "已复制", "提示词已复制！")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择音频", "", "Audio (*.mp3 *.wav)")
        for f in files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f))
            name = self.parent_settings.n_name.text() if self.parent_settings else "Nagomu"
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem("normal")) 
            self.table.setItem(row, 3, QTableWidgetItem("待识别..."))
            self.table.setItem(row, 4, QTableWidgetItem("就绪"))

    def batch_asr(self):
        """采用你提供的 SenseVoiceSmall 官方调用逻辑"""
        api_key = self.get_api_key()
        if not api_key: return QMessageBox.warning(self, "错误", "请先在主界面填入 API Key")

        url = "https://api.siliconflow.cn/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}

        for i in range(self.table.rowCount()):
            path = self.table.item(i, 0).text()
            self.table.setItem(i, 4, QTableWidgetItem("⌛ 识别中..."))
            QApplication.processEvents()

            try:
                # 按照你提供的 files 格式和 payload 进行调用
                files = { "file": (os.path.basename(path), open(path, "rb")) }
                payload = { "model": "FunAudioLLM/SenseVoiceSmall" }
                
                resp = requests.post(url, data=payload, files=files, headers=headers)
                if resp.status_code == 200:
                    text = resp.json().get("text", "")
                    self.table.setItem(i, 3, QTableWidgetItem(text))
                    self.table.setItem(i, 4, QTableWidgetItem("✅ 成功"))
                else:
                    self.table.setItem(i, 4, QTableWidgetItem(f"❌ {resp.status_code}"))
            except Exception as e:
                self.table.setItem(i, 4, QTableWidgetItem("💥 错误"))

    def handle_batch_upload(self):
        """批量克隆逻辑"""
        api_key = self.get_api_key()
        final_list = []
        for i in range(self.table.rowCount()):
            it_path, it_char, it_emo, it_txt = [self.table.item(i, col) for col in range(4)]
            if not it_path or not it_txt: continue
            
            content = it_txt.text().strip()
            if content in ["待识别...", ""]: continue

            try:
                url = "https://api.siliconflow.cn/v1/uploads/audio/voice"
                headers = {"Authorization": f"Bearer {api_key}"}
                with open(it_path.text(), "rb") as f:
                    payload = {
                        "model": "FunAudioLLM/CosyVoice2-0.5B",
                        "customName": f"{it_char.text()}_{it_emo.text()}",
                        "text": content
                    }
                    resp = requests.post(url, headers=headers, files={"file": f}, data=payload)
                    if resp.status_code == 200:
                        uri = resp.json().get("uri")
                        final_list.append(f"speech:{it_char.text()}:{it_emo.text()}:{uri}")
                        self.table.setItem(i, 4, QTableWidgetItem("🚀 上传成功"))
            except: pass
        self.output_res.setPlainText("\n".join(final_list))