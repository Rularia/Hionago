# panel.py
import sys, os, hashlib, datetime, multiprocessing
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QHBoxLayout, QLabel, 
                             QMenu, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from voice_service import VoiceService
from config import VOICE_DIR, CHAT_HISTORY_PATH, FAVORITES_PATH, COLOR_HIORI, COLOR_NAGOMU

class HistoryPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("语音档案库")
        self.resize(760, 800)
        
        # 界面美化样式
        self.setStyleSheet("""
            QWidget { background-color: #F0F2F5; color: #333333; font-family: 'Microsoft YaHei'; font-size: 13px; }
            QLabel#Title { font-size: 18px; font-weight: bold; color: #4A5568; margin-bottom: 5px; }
            QListWidget { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 8px; outline: none; }
            QListWidget::item { border-bottom: 1px solid #F3F4F6; padding: 2px; }
            QListWidget::item:selected { background-color: #EBF8FF; }
            QPushButton { background-color: #6B7280; border: none; border-radius: 5px; color: white; padding: 10px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #4B5563; }
            QPushButton#PrimaryBtn { background-color: #3182CE; }
            QPushButton#PrimaryBtn:hover { background-color: #2B6CB0; }
            QPushButton#FavBtn { background-color: #ED8936; }
            QPushButton#FavBtn:hover { background-color: #DD6B20; }
            QPushButton#DeleteBtn { background-color: #E53E3E; }
            QPushButton#DeleteBtn:hover { background-color: #C53030; }
        """)
        
        self.voice = VoiceService()
        self.history_file = CHAT_HISTORY_PATH 
        self.fav_file = FAVORITES_PATH       
        
        self.initUI()
        self.load_history()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("📢 语音档案库")
        title_label.setObjectName("Title")
        layout.addWidget(title_label)
        
        sub_label = QLabel("双击播放语音 | 右键单条管理 | 勾选下方按钮执行批量操作")
        sub_label.setStyleSheet("color: #718096; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(sub_label)
        
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self.play_line)
        layout.addWidget(self.list_widget)
        
        # 按钮布局区：按照您的建议调整顺序
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.load_history)
        
        self.btn_fav = QPushButton("⭐ 收藏选中")
        self.btn_fav.setObjectName("FavBtn")
        self.btn_fav.clicked.connect(self.add_to_favorites)
        
        self.btn_batch = QPushButton("📦 批量音频")
        self.btn_batch.setObjectName("PrimaryBtn")
        self.btn_batch.clicked.connect(self.batch_generate)

        # 批量删除放在最右边
        self.btn_delete = QPushButton("🗑️ 批量删除")
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.clicked.connect(self.batch_delete)
        
        btn_layout.addWidget(self.btn_refresh, 1)
        btn_layout.addWidget(self.btn_fav, 1)
        btn_layout.addWidget(self.btn_batch, 1)
        btn_layout.addWidget(self.btn_delete, 1)
        layout.addLayout(btn_layout)

    def get_actual_path(self, char_name, ja_text):
        return self.voice.get_file_path(char_name, ja_text)

    def load_history(self):
        """ 加载并渲染历史记录，中文放大并与日文平等排版 """
        sb = self.list_widget.verticalScrollBar()
        current_pos = sb.value() 
        self.list_widget.clear()
        
        if not os.path.exists(self.history_file): return
        
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    line = line.strip()
                    # 匹配 llm_service 写入格式: char|emotion: ja|zh
                    if not line or line.startswith("[USER") or "|" not in line: continue
                    
                    try:
                        # 1. 解析数据
                        char_part, rest = line.split("|", 1)
                        if ":" not in rest: continue
                        emo_part, content = rest.split(":", 1)
                        ja, zh = content.rsplit("|", 1) if "|" in content else (content, "")

                        data = {
                            'char': char_part.strip("[] "),
                            'emo': emo_part.strip(),
                            'ja': ja.strip(),
                            'zh': zh.strip()
                        }

                        # 2. 检测本地文件 (用于显示已存档状态)
                        audio_path = self.voice.get_file_path(data['char'], data['ja'])
                        is_stored = os.path.exists(audio_path)

                        # 3. UI 渲染
                        item = QListWidgetItem(self.list_widget)
                        item.setData(Qt.UserRole, data)
                        
                        container = QWidget()
                        # 设置背景色区分角色，去掉所有边框
                        bg_color = "#F0F7FF" if data['char'] in ['Hiori', '高远日织'] else "#FFF9F9"
                        container.setStyleSheet(f"background-color: {bg_color}; border: none; border-radius: 8px; margin: 4px;")
                        
                        layout = QHBoxLayout(container)
                        layout.setContentsMargins(15, 10, 15, 10) # 增加内边距
                        

                        cb = QCheckBox()
                        cb.setFixedSize(24, 24) # 缩减整体占用空间
                        cb.setStyleSheet("""
                            QCheckBox::indicator {
                                width: 16px;
                                height: 16px;
                                border: 1.5px solid #A0AEC0; /* 边框细一点，颜色稍浅 */
                                border-radius: 3px;
                                background-color: white;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #4299E1; /* 选中色保持明亮 */
                                border-color: #3182CE;
                            }
                            QCheckBox::indicator:hover {
                                border-color: #718096; /* 悬停时稍微加深 */
                            }
                        """)
                        layout.addWidget(cb)
                        
                        
                        text_layout = QVBoxLayout()
                        text_layout.setSpacing(6) # 日语和中文之间的间距
                        
                        # 标题栏：角色名 + 已存档标识
                        status_html = "<span style='color:#48BB78; font-size: 12px;'> ● 已存档</span>" if is_stored else ""
                        name_label = QLabel(f"<b style='color:#4A5568; font-size: 13px;'>{data['char']}</b> <span style='color:#A0AEC0; font-size: 11px;'>[{data['emo']}]</span>{status_html}")
                        
                        # 日语台词：加粗并放大
                        ja_label = QLabel(data['ja'] or "...")
                        ja_label.setStyleSheet("color: #1A202C; font-size: 14px; font-weight: 500; border: none; background: transparent;")
                        ja_label.setWordWrap(True)
                        
                        # 中一台词：放大并加重颜色，与日语排在一起
                        zh_label = QLabel(data['zh'])
                        zh_label.setStyleSheet("color: #2D3748; font-size: 13px; border: none; background: transparent;")
                        zh_label.setWordWrap(True)
                        
                        text_layout.addWidget(name_label)
                        text_layout.addWidget(ja_label)
                        text_layout.addWidget(zh_label)
                        layout.addLayout(text_layout, 1)

                        if data['ja']:
                            btn = QPushButton("▶")
                            btn.setFixedSize(36, 36)
                            btn.setCursor(Qt.PointingHandCursor)
                            # 点击后调用 voice_service 进行播放/生成
                            btn.clicked.connect(lambda ch=data['char'], e=data['emo'], t=data['ja']: self.voice.speak(ch, e, t))
                            layout.addWidget(btn)

                        item.setSizeHint(container.sizeHint())
                        self.list_widget.addItem(item)
                        self.list_widget.setItemWidget(item, container)

                    except Exception: continue
        except Exception as e:
            print(f"档案库加载失败: {e}")
            
        QTimer.singleShot(20, lambda: self.list_widget.verticalScrollBar().setValue(current_pos))
        
        
    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        data = item.data(Qt.UserRole)
        path = self.voice.get_file_path(data['char'], data['ja'])
        
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: 1px solid #D1D5DB; padding: 5px; }")
        menu.addAction("▶️ 播放此条语音", lambda: self.play_line(item))
        
        act_locate = QAction("📍 定位本地文件", self)
        act_locate.setEnabled(os.path.exists(path))
        act_locate.triggered.connect(lambda: os.system(f'explorer /select,"{os.path.abspath(path)}"'))
        menu.addAction(act_locate)
        
        menu.addSeparator()
        menu.addAction("🗑️ 删除此条记录", lambda: self.delete_history_item(item))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def delete_history_item(self, item):
        data = item.data(Qt.UserRole)
        if QMessageBox.question(self, '确认', '确定删除该记录吗？') == QMessageBox.No: return
        self._execute_delete([data])
        self.load_history()

    def batch_delete(self):
        targets = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            cb = self.list_widget.itemWidget(item).findChild(QCheckBox)
            if cb and cb.isChecked():
                targets.append(item.data(Qt.UserRole))

        if not targets:
            QMessageBox.warning(self, "提示", "请先勾选需要删除的记录")
            return

        if QMessageBox.question(self, '批量删除确认', f'确定永久删除选中的 {len(targets)} 条记录吗？') == QMessageBox.Yes:
            self._execute_delete(targets)
            self.load_history()

    def _execute_delete(self, data_list):
        """ 执行文件和文本行的双重剔除逻辑 """
        try:
            if hasattr(self.voice, 'stop_all'): self.voice.stop_all()

            # 物理删除音频
            for data in data_list:
                audio_path = self.voice.get_file_path(data['char'], data['ja'])
                if os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except: pass

            # 内容指纹匹配删除文本行
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                new_lines = lines
                for data in data_list:
                    target_ja = data['ja'].strip()
                    target_zh = data['zh'].strip()
                    # 过滤掉内容包含目标原文和译文的行
                    new_lines = [line for line in new_lines if not (target_ja in line and target_zh in line)]
                
                with open(self.history_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除操作失败: {e}")

    def add_to_favorites(self):
        fav_list = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            cb = self.list_widget.itemWidget(item).findChild(QCheckBox)
            if cb and cb.isChecked():
                data = item.data(Qt.UserRole)
                fav_list.append(f"{data['char']}:{data['ja']}@{data['zh']}")

        if not fav_list: return QMessageBox.warning(self, "提示", "请先勾选内容")
        
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            record = f"{now} | {' || '.join(fav_list)}\n"
            with open(self.fav_file, "a", encoding="utf-8") as f: f.write(record)
            QMessageBox.information(self, "成功", f"已成功收藏 {len(fav_list)} 条内容")
        except Exception as e: QMessageBox.critical(self, "错误", str(e))

    def play_line(self, item):
        data = item.data(Qt.UserRole)
        self.voice.speak(data['char'], data['emo'], data['ja'])
        QTimer.singleShot(1500, self.load_history)

    def batch_generate(self):
        count = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            cb = self.list_widget.itemWidget(item).findChild(QCheckBox)
            if cb and cb.isChecked() and count < 10:
                data = item.data(Qt.UserRole)
                self.voice.speak(data['char'], data['emo'], data['ja'])
                count += 1
        if count > 0: QTimer.singleShot(2000, self.load_history)

if __name__ == "__main__":
    multiprocessing.freeze_support() 
    app = QApplication(sys.argv)
    window = HistoryPanel()
    window.show()
    sys.exit(app.exec())