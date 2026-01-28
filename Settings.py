# -*- coding: utf-8 -*-
"""
Project: HioNago AI Desktop Pet
Character Series: Ichiyanagi Nagomu Series (一柳和系列)
---------------------------------------------------------
[ Credits ]
Development: [Rularia]
Illustrator: [鱼骨] (Special Thanks!)
---------------------------------------------------------
Message: Please support the Ichiyanagi Nagomu series!
Copyright (c) 2026. All rights reserved.
"""
# Settings.py 修正整合版 (新增角色名定义与语音一键上传功能)
import sys, os, config, json, re
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor
from settings_logic import SettingsLogic
from asset_logic import AssetLogic

class IntegratedSettings(QWidget):
    def __init__(self):

        super().__init__()
        self.logic = SettingsLogic()
        self.setWindowTitle("桌面剧场 - 深度设置管理")
        self.resize(1150, 850)
        
        # --- 核心修复：先初始化容器，再进行 UI 构建和数据加载 ---
        self.l2d_edits = {}
        self.exp_edits = {}
# 1. 定义初始映射 (使用 self 变成全局可用)
        self.CHAR_MAP = {
            "Hiori": {"id": "Hiori", "default_label": "角色A", "current_name": "Hiori"},
            "Nagomu": {"id": "Nagomu", "default_label": "角色B", "current_name": "Nagomu"}
        }
        
        # 2. 定义存放 UI 引用（GroupBox）的容器，方便后面修改标题
        self.dynamic_groups = {"Hiori": [], "Nagomu": []}

# --- 修复 KeyError：在这里直接初始化 Key ---
        self.exp_forms_static = {"Hiori": None, "Nagomu": None}
        self.exp_forms_l2d = {"Hiori": None, "Nagomu": None}
        self.exp_rows_static = {"Hiori": [], "Nagomu": []}
        self.exp_rows_l2d = {"Hiori": [], "Nagomu": []}
        self.semantic_entries = {"Hiori": [], "Nagomu": []} 
        
        self.v_rows = {"Hiori": [], "Nagomu": []}
        self.l2d_edits = {}

        self.init_ui()
        self.load_to_ui()
        # --- 关键修复：在这里接通信号线 ---
        self.setup_connections() 
        
        # --- 进阶：初始化时强制刷新一次标题（让加载的名字立即生效） ---
        self.update_ui_titles("Hiori", self.h_name.text())
        self.update_ui_titles("Nagomu", self.n_name.text())
        # 这行会调用扫描函数，此时 exp_rows 已存在
    def setup_connections(self):
        """当名字输入框内容改变时，触发更新"""
        self.h_name.textChanged.connect(lambda t: self.update_ui_titles("Hiori", t))
        self.n_name.textChanged.connect(lambda t: self.update_ui_titles("Nagomu", t))

    def update_ui_titles(self, char_id, new_name):
        """核心函数：遍历所有登记过的组件，更新它们的标题"""
        # 如果用户把名字删光了，显示“角色A/B”作为占位
        display_text = new_name.strip() if new_name.strip() else self.CHAR_MAP[char_id]["default_label"]
        
        # 同步更新缓存中的 current_name
        self.CHAR_MAP[char_id]["current_name"] = display_text
            
        # 遍历所有登记过的 GroupBox 标题
        if char_id in self.dynamic_groups:
            for item in self.dynamic_groups[char_id]:
                widget = item["widget"]
                template = item["template"]
                # 只有当 widget 还没被销毁时才更新
                if widget:
                    widget.setTitle(template.format(display_text))
###____________________

    def init_ui(self):
        main_lay = QHBoxLayout(self)
        self.nav = QListWidget(); self.nav.setFixedWidth(200)
        self.nav.addItems(["🎭 剧本人设", "⚙️ 对话策略", "✨ 表情映射", "👁 Live2D 参数", "🎙 音色克隆", "📡 接口与地点", "📂 图库档案"])
        
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_script())      # 0
        self.stack.addWidget(self._page_modes())       # 1
        self.stack.addWidget(self._page_expressions()) # 2
        self.stack.addWidget(self._page_l2d())         # 3
        self.stack.addWidget(self._page_voice())       # 4
        self.stack.addWidget(self._page_api())         # 5
        self.stack.addWidget(self._page_files())       # 6
        
        right_lay = QVBoxLayout(); right_lay.addWidget(self.stack)
        self.btn_save = QPushButton("💾 保存并应用全部修改"); self.btn_save.setFixedHeight(50)
        self.btn_save.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.handle_save); right_lay.addWidget(self.btn_save)
        
        main_lay.addWidget(self.nav); main_lay.addLayout(right_lay)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

    def _page_script(self):
        p = QWidget(); l = QVBoxLayout(p)
        
        # 角色姓名输入 (新增)
        name_lay = QHBoxLayout()
        self.h_name = QLineEdit(); self.n_name = QLineEdit()
        self.h_name.setPlaceholderText("例如: Hiori"); self.n_name.setPlaceholderText("例如: Nagomu")
        name_lay.addWidget(QLabel("角色A 姓名:")); name_lay.addWidget(self.h_name)
        name_lay.addWidget(QLabel("角色B 姓名:")); name_lay.addWidget(self.n_name)
        l.addLayout(name_lay)
        
        # 2. 角色别名输入 (新增)
        alias_lay = QHBoxLayout()
        self.h_alias = QLineEdit(); self.n_alias = QLineEdit()
        self.h_alias.setPlaceholderText("别名(英文逗号分隔), 如: 日织酱,高远")
        self.n_alias.setPlaceholderText("别名(英文逗号分隔), 如: 和先生,阿和")
        alias_lay.addWidget(QLabel("角色A 别名:")); alias_lay.addWidget(self.h_alias)
        alias_lay.addWidget(QLabel("角色B 别名:")); alias_lay.addWidget(self.n_alias)
        l.addLayout(alias_lay)

        # 人设文本
        self.h_p = QTextEdit(); self.n_p = QTextEdit(); self.prompt = QTextEdit()
        l.addWidget(QLabel("角色A 人设:")); l.addWidget(self.h_p)
        l.addWidget(QLabel("角色B 人设:")); l.addWidget(self.n_p)
        
        # 角色颜色
        color_lay = QHBoxLayout()
        self.h_color = QLineEdit(); self.n_color = QLineEdit()
        color_lay.addWidget(QLabel("角色A 颜色(HEX):")); color_lay.addWidget(self.h_color)
        color_lay.addWidget(QLabel("角色B 颜色(HEX):")); color_lay.addWidget(self.n_color)
        l.addLayout(color_lay)

        # 角色称呼映射 (日语纠音)
        l.addWidget(QLabel("角色称呼/读音映射 (JSON格式, 用于TTS纠音):"))
        self.name_map = QLineEdit()
        self.name_map.setPlaceholderText('{"和先生": "なごさん", "日织": "ひおり"}')
        l.addWidget(self.name_map)
# --- 新增：Prompt 编写说明卡片 ---
        guide_gb = QGroupBox("📝 系统提示词 (Prompt) 编写指南")
        guide_lay = QVBoxLayout(guide_gb)
        guide_text = QLabel(
            "为了让 AI 识别你设置的人设，请在模板中务必包含以下变量：<br>"
            "• <b style='color: #E67E22;'>{HIORI_INFO}</b> : 自动替换为上方角色A的人设内容<br>"
            "• <b style='color: #E67E22;'>{NAGOMU_INFO}</b> : 自动替换为上方角色B的人设内容<br>"
            "<small style='color: #7F8C8D;'>* 建议结构：### 角色设定 \n 角色A: {HIORI_INFO} ...</small>"
        )
        guide_text.setWordWrap(True)
        guide_lay.addWidget(guide_text)
        l.addWidget(guide_gb)
        l.addWidget(QLabel("系统 Prompt 模板:")); l.addWidget(self.prompt)
        return p

    def _page_modes(self):
        p = QWidget(); l = QVBoxLayout(p); self.mode_inputs = {}
        for k in ["short", "medium", "story"]:
            gb = QGroupBox(f"策略: {k.upper()}"); fl = QFormLayout(gb)
            r = QLineEdit(); t = QDoubleSpinBox(); t.setRange(0, 2.0); t.setSingleStep(0.1)
            c = QSpinBox(); c.setRange(1, 2000)
            fl.addRow("描述 (desc):", r); fl.addRow("温度 (temp):", t); fl.addRow("上下文轮数:", c)
            self.mode_inputs[k] = {"rounds": r, "temp": t, "limit": c}; l.addWidget(gb)
        return p



            # ... 剩下的 grid 代码保持不变 ...
            # Settings.py 中的 _page_expressions 完整块
    def _page_expressions(self):
        p = QWidget(); main_lay = QVBoxLayout(p)
        sem_lay = QHBoxLayout()
        
        for char_id in ["Hiori", "Nagomu"]:
            # 获取当前应显示的名称
            d_name = self.CHAR_MAP[char_id]["current_name"]
            
            gb = QGroupBox(f"🧠 {d_name} 情绪语义定义")
            # --- 关键：登记这个 GroupBox ---
            self.dynamic_groups[char_id].append({"widget": gb, "template": "🧠 {} 情绪语义定义"})
            
            grid = QGridLayout(gb)
            for i in range(16): # 扩展到 16 行
                id_e = QLineEdit(); id_e.setFixedWidth(45)
                id_e.setPlaceholderText("待定") # ID 留空代表暂无对应资产
                kw_e = QLineEdit(); kw_e.setPlaceholderText("输入匹配关键词，逗号分隔...")
                grid.addWidget(QLabel(f"{i+1}."), i, 0)
                grid.addWidget(id_e, i, 1)
                grid.addWidget(kw_e, i, 2)
                self.semantic_entries[char_id].append({'id': id_e, 'kw': kw_e})
            sem_lay.addLayout(QVBoxLayout()); sem_lay.itemAt(sem_lay.count()-1).layout().addWidget(gb)
        
        main_lay.addLayout(sem_lay)

        # 2. 下方：资产映射（使用选项卡分离 Static 和 L2D）
        asset_tabs = QTabWidget()
        
        # --- 创建静态图 Tab ---
        static_w = QWidget(); static_lay = QHBoxLayout(static_w)
        for cid in ["Hiori", "Nagomu"]:
            d_name = self.CHAR_MAP[cid]["current_name"] # 获取初始显示名
            gb = QGroupBox(f"🖼️ {d_name} 静态图分配")
            # 关键：登记动态更新
            self.dynamic_groups[cid].append({"widget": gb, "template": "🖼️ {} 静态图分配"})
            v = QVBoxLayout(gb); scroll = QScrollArea(); scroll.setWidgetResizable(True)
            container = QWidget(); form = QFormLayout(container)
            self.exp_forms_static[cid] = form # 绑定变量
            scroll.setWidget(container); v.addWidget(scroll); static_lay.addWidget(gb)
        asset_tabs.addTab(static_w, "静态图/GIF 资产")

        # --- 创建 Live2D Tab ---
        l2d_w = QWidget(); l2d_lay = QHBoxLayout(l2d_w)
        for cid in ["Hiori", "Nagomu"]:
            d_name = self.CHAR_MAP[cid]["current_name"]
            gb = QGroupBox(f"🎭 {d_name} Live2D 表情分配")
            # 关键：登记动态更新
            self.dynamic_groups[cid].append({"widget": gb, "template": "🎭 {} Live2D 表情分配"})
            v = QVBoxLayout(gb); scroll = QScrollArea(); scroll.setWidgetResizable(True)
            container = QWidget(); form = QFormLayout(container)
            self.exp_forms_l2d[cid] = form # 绑定变量
            scroll.setWidget(container); v.addWidget(scroll); l2d_lay.addWidget(gb)
        asset_tabs.addTab(l2d_w, "Live2D 模型表情")

        main_lay.addWidget(asset_tabs)

        btn_scan = QPushButton(" 🔄 刷新本地文件并同步所有编号 ")
        btn_scan.setFixedHeight(45); btn_scan.clicked.connect(self.handle_expression_scan)
        main_lay.addWidget(btn_scan)
        
        return p


# Settings.py 内部

    
# Settings.py 中的 handle_expression_scan 修正
    def handle_expression_scan(self):
        """ 彻底修正：增加安全检查并闭合循环 """
        l2d_dir = os.path.dirname(config.MODEL_PATH)
        scan_targets = [
            {
                "id": "static",
                "dir": config.SPRITE_DIR,
                "exts": ('.png', '.jpg', '.jpeg', '.gif'),
                "prefix": "", 
                "forms": self.exp_forms_static,
                "store": self.exp_rows_static
            },
            {
                "id": "l2d",
                "dir": l2d_dir,
                "exts": ".exp3.json",
                "prefix": "live2d_expression", 
                "forms": self.exp_forms_l2d,
                "store": self.exp_rows_l2d
            }
        ]

        for target in scan_targets:
            t_dir = target["dir"]
            if not os.path.exists(t_dir): continue

            for char_id in ["Hiori", "Nagomu"]:
                # --- 安全检查：确保布局已初始化 ---
                form = target["forms"].get(char_id)
                if form is None: continue 

                # 1. 清理旧 UI 列表
                while form.rowCount() > 0: 
                    form.removeRow(0)
                target["store"][char_id] = []
                
                try:
                    all_files = os.listdir(t_dir)
                    valid_files = [f for f in all_files if f.lower().endswith(target["exts"])]
                    if target["id"] == "l2d":
                        valid_files = [f for f in valid_files if f.lower().startswith(target["prefix"])]
                    
                    valid_files.sort()
                    
                    counters = 0
                    for f in valid_files:
                        # 角色归属判定
                        if char_id.lower() in f.lower() or (char_id == "Nagomu" and "hiori" not in f.lower()):
                            code = f"{float(counters):.1f}"
                            label = QLabel(code)
                            label.setStyleSheet("color: #00ff00; font-weight: bold; padding-left: 10px;")
                            form.addRow(f, label)
                            target["store"][char_id].append({"file": f, "code": code})
                            counters += 1
                except Exception as e:
                    print(f"扫描异常: {e}")
            ###_________________
            
    def _page_l2d(self):
        p = QWidget(); l = QVBoxLayout(p); btn = QPushButton("🔍 解析模型参数")
        btn.clicked.connect(self.handle_l2d_scan)
        l.addWidget(QLabel("<b>👁 参数映射 (cdi3.json)</b>")); l.addWidget(btn)
        self.l2d_form = QFormLayout(); c = QWidget(); c.setLayout(self.l2d_form)
        s = QScrollArea(); s.setWidget(c); s.setWidgetResizable(True); l.addWidget(s)
        return p

    def handle_l2d_scan(self):
        params = self.logic.scan_l2d_params()
        while self.l2d_form.rowCount() > 0: self.l2d_form.removeRow(0)
        self.l2d_edits = {}
        for p in params:
            pid, pname = p["id"], p["name"]; edit = QLineEdit(); edit.setPlaceholderText(pid)
            self.l2d_form.addRow(f"{pname} ({pid}):", edit); self.l2d_edits[pid] = edit

    def _page_voice(self):
        p = QWidget(); l = QVBoxLayout(p)
        self.v_rows = {"Hiori": [], "Nagomu": []}

        # --- 新增：全局语音开关 ---
        self.enable_voice_cb = QCheckBox("🔊 启用 AI 语音生成 (取消勾选即进入静音模式)")
        self.enable_voice_cb.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        l.addWidget(self.enable_voice_cb)
        
        # ... 原有的 header_lay 等代码保持不变 ...

        # --- 1. 顶部：工具栏 ---
        header_lay = QHBoxLayout()
        header_lay.addWidget(QLabel("<b>🎙 语音资产管理 (Key-URI 联动模式)</b>"))
        header_lay.addStretch()
        upload_btn = QPushButton(" 🛠️ 语音同步工具 ")
        upload_btn.setFixedHeight(30); upload_btn.clicked.connect(self.handle_bulk_voice_upload)
        header_lay.addWidget(upload_btn)
        l.addLayout(header_lay)

        # --- 2. 中间：批量解析框 ---
        parse_gb = QGroupBox("📋 批量字符串同步")
        parse_lay = QVBoxLayout(parse_gb)
        self.voice_paste_input = QTextEdit()
        self.voice_paste_input.setPlaceholderText("在此粘贴 VoiceExpert 生成的 speech:xxxx 字符串...")
        self.voice_paste_input.setFixedHeight(60)
        btn_parse = QPushButton("⚡ 解析并自动对齐 Key")
        btn_parse.clicked.connect(self.handle_parse_voice_paste)
        parse_lay.addWidget(self.voice_paste_input); parse_lay.addWidget(btn_parse)
        l.addWidget(parse_gb)

        # --- 3. 下方：分角色音色表单 ---
        for char_id in ["Hiori", "Nagomu"]:
            d_name = self.CHAR_MAP[char_id]["current_name"]
            gb = QGroupBox(f"🎙️ {d_name} 音色配置")
            
            # --- 核心：登记动态标题更新 ---
            self.dynamic_groups[char_id].append({"widget": gb, "template": "🎙️ {} 音色配置"})
            
            gl = QGridLayout(gb)
            gl.setColumnStretch(0, 2); gl.setColumnStretch(1, 3); gl.setColumnStretch(3, 5)

            gl.addWidget(QLabel("<b>情绪编号</b>"), 0, 0) 
            gl.addWidget(QLabel("<b>备注/Key</b>"), 0, 1)
            gl.addWidget(QLabel("<b>接口 ID (URI)</b>"), 0, 3)

            for i in range(1, 11): # 10 种情绪槽位
                code_edit = QLineEdit(); code_edit.setPlaceholderText("0.0"); code_edit.setFixedWidth(50)
                key_edit = QLineEdit(); uri_edit = QLineEdit()
                
                # 信号绑定逻辑：使用 char_id 确保内部逻辑正确
                key_edit.textChanged.connect(lambda text, u=uri_edit, c=char_id: 
                    self.sync_uri_with_key(text, u, c))
                
                gl.addWidget(code_edit, i, 0)
                gl.addWidget(key_edit, i, 1)
                gl.addWidget(QLabel(" 🔗 "), i, 2)
                gl.addWidget(uri_edit, i, 3)
                
                self.v_rows[char_id].append({
                    "code": code_edit, "key": key_edit, "uri": uri_edit
                })
            l.addWidget(gb)
        
        l.addStretch()
        return p
        
        
    def sync_uri_with_key(self, new_key, uri_edit, char_name):
        """当 Key 改变，实时修正 URI 内部的 customName"""
        current_uri = uri_edit.text().strip()
        if not current_uri or "speech:" not in current_uri: return
        
        # 按照 speech:角色_语气:账号:ID 拆分
        parts = current_uri.split(':')
        if len(parts) >= 4:
            # 这里的 parts[1] 原本是 'Nagomu_shock'，我们根据新 Key 替换它
            new_uri = f"speech:{char_name}_{new_key}:{parts[2]}:{parts[3]}"
            uri_edit.blockSignals(True) # 防止死循环
            uri_edit.setText(new_uri)
            uri_edit.blockSignals(False)
            
    def handle_parse_voice_paste(self):
        import re
        raw_text = self.voice_paste_input.toPlainText().strip()
        if not raw_text: return

        # 匹配格式 speech:角色:Key:完整的URI
        pattern = r"speech:([^:]+):([^:]+):(speech:[^ \n\r]+)"
        matches = re.findall(pattern, raw_text)

        for char_name, key, full_uri in matches:
            target_role = "Hiori" if "Hiori" in char_name else "Nagomu"
            
            # 寻找一个可以填入的位置
            for row in self.v_rows[target_role]:
                # 如果这一行 备注(key) 匹配或者是空的
                if row['key'].text() == key or not row['key'].text():
                    row['key'].setText(key)
                    row['uri'].setText(full_uri)
                    # 提示：你可以在这里根据 key 自动猜测 code，或者让用户手动填编号
                    break
        
        QMessageBox.information(self, "完成", "已完成字符串解析。请手动核对左侧[情绪编号]是否与大字典对齐。")
        
    
    def handle_bulk_voice_upload(self):
        """挂载并运行语音克隆工具"""
        try:
            # 导入你保存的 VoiceExpert 类
            from VoiceExpert import VoiceExpert 
            
            # 将 self 传递进去，使子窗口能实时读取 api_key.text()
            self.voice_expert_window = VoiceExpert(self) 
            
            # 设置为弹窗模式并显示
            self.voice_expert_window.setWindowModality(Qt.WindowModality.NonModal)
            self.voice_expert_window.show()
            
        except ImportError:
            QMessageBox.critical(self, "错误", "找不到 VoiceExpert.py 文件，请确保它在同一目录下。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败: {str(e)}")                
            
    def _page_api(self):
        p = QWidget(); l = QVBoxLayout(p)
        # --- 新增的引导提示部分 ---
        api_guide = QLabel(
            "<b>📡 硅基流动接口配置:</b><br>"
            "1. 请前往 <a href='https://cloud.siliconflow.cn/i/MdPaiBcl' style='color: #3182CE;'><b>硅基流动官网</b></a> 注册并获取 API Key。<br>"
            "2. 填入下方的密钥框后，点击同步按钮激活音色资产。<br>"
            "3. 观测城市用于天气预报接口同步。"
        )
        api_guide.setOpenExternalLinks(True)  # 允许点击 HTML 链接
        api_guide.setWordWrap(True)            # 允许文字自动换行
        api_guide.setStyleSheet("margin-bottom: 5px; color: #4A5568;") # 稍微加点边距和美化颜色
        l.addWidget(api_guide)
        # ------------------------
        g1 = QGroupBox("LLM 大模型接口"); f1 = QFormLayout(g1)
        self.llm_url = QLineEdit(); self.llm_model = QLineEdit(); self.api_key = QLineEdit()
        f1.addRow("Base URL:", self.llm_url); f1.addRow("模型名称:", self.llm_model); f1.addRow("API Key:", self.api_key)
        l.addWidget(g1)
        
# --- TTS 配置 (新增警告提示) ---
        g2 = QGroupBox("TTS 语音接口"); f2 = QFormLayout(g2)
        
        # ⚠️ 新增的 TTS 提示信息
        tts_tip = QLabel(
            "<b>⚠️ 注意：</b><br>"
            "<span style='color: #856404;'>目前国产多语言模型是支持自定义音色的主流选择。虽然由于算法原因（如 F5-TTS）可能会出现“幻觉”或复读，但这是目前兼顾多语言和克隆效果的最佳方案。</span><br>"
            "<small style='color: #666;'>* 如果您不介意固定音色，可以在下方更换模型（如 FishSpeech 等），系统将尝试自动选择默认音色。</small>"
        )
        tts_tip.setWordWrap(True)
        tts_tip.setStyleSheet("""
            background-color: #FFF3CD; 
            border: 1px solid #FFEEBA; 
            border-radius: 4px; 
            padding: 8px; 
            margin-bottom: 5px;
        """)
        f2.addRow(tts_tip) # 将提示添加到表单的第一行
        
        self.tts_url = QLineEdit(); self.tts_model = QLineEdit(); self.tts_key = QLineEdit()
        f2.addRow("TTS Base URL:", self.tts_url); f2.addRow("TTS 模型:", self.tts_model); f2.addRow("TTS API Key:", self.tts_key)
        l.addWidget(g2)
 # --- 快捷访问与城市 ---
        g3 = QGroupBox("📂 快捷访问目录")
        h_lay = QHBoxLayout(g3)
        btn_fav = QPushButton("⭐ 收藏夹"); btn_fav.clicked.connect(lambda: os.startfile(os.path.dirname(config.FAVORITES_PATH)))
        btn_his = QPushButton("🕒 历史记录 (TXT)"); btn_his.clicked.connect(lambda: os.startfile(config.CHAT_HISTORY_PATH))
        btn_aud = QPushButton("🔊 音频输出"); btn_aud.clicked.connect(lambda: os.startfile(config.VOICE_DIR))
        for b in [btn_fav, btn_his, btn_aud]: b.setFixedHeight(35); h_lay.addWidget(b)
        l.addWidget(g3)

        self.city = QLineEdit(); l.addWidget(QLabel("城市定位:")); l.addWidget(self.city)
        l.addStretch(); return p

    def _page_files(self):
        p = QWidget(); l = QVBoxLayout(p); l.addWidget(QLabel("<b>☁️ Vika 资源同步中心</b>"))
        self.up_btn = QPushButton("\n📤 点击批量上传图片至维格表\n"); self.up_btn.setFixedHeight(100)
        self.up_btn.clicked.connect(self.handle_upload); l.addWidget(self.up_btn)
        
        l.addWidget(QLabel("云端管理链接:"))
        self.vika_web_url = QLineEdit(); l.addWidget(self.vika_web_url)
        btn_open = QPushButton("🌐 打开云端管理页面")
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.vika_web_url.text())))
        l.addWidget(btn_open)

        f = QFormLayout(); self.v_token = QLineEdit(); self.v_id = QLineEdit()
        f.addRow("Vika Token:", self.v_token); f.addRow("Sheet ID:", self.v_id)
        l.addLayout(f); l.addStretch(); return p

    def handle_upload(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg)")
        for f in files: self.logic.vika_upload_logic(f)
        QMessageBox.information(self, "完成", "同步结束。")

    def load_to_ui(self):
        # 获取所有数据
        api, cur = self.logic.load_all_data()
        from asset_logic import AssetLogic  # 如果顶部没导，可以留在这里，但建议放顶部
        # 回显开关状态，如果没有设置过则默认开启
        self.enable_voice_cb.setChecked(cur.get("enable_voice", True))
        # 1. API 与 Vika 部分
        self.llm_url.setText(api.get("llm_base_url", config.LLM_API_BASE))
        self.llm_model.setText(api.get("llm_model", "deepseek-ai/DeepSeek-V3.2"))
        self.api_key.setText(api.get("api_key", config.API_KEY))
        self.tts_url.setText(api.get("tts_base_url", config.TTS_API_BASE))
        self.tts_model.setText(api.get("tts_model", config.TTS_MODEL))
        self.tts_key.setText(api.get("tts_key", api.get("api_key", "")))
        self.v_token.setText(api.get("vika_token", config.VIKA_TOKEN))
        self.v_id.setText(api.get("vika_datasheet_id", config.VIKA_ID))
        self.vika_web_url.setText(api.get("vika_web_url", "https://vika.cn/"))
        
        # 2. 基础人设与姓名
        self.city.setText(cur.get("city", config.CITY))
        configs = config.load_all_configs()
        self.prompt.setPlainText(cur.get("prompt_template", configs.get("prompt_template", "")))
        
        self.h_name.setText(cur.get("char_name_hiori", "Hiori"))
        self.n_name.setText(cur.get("char_name_nagomu", "Nagomu"))
        self.h_alias.setText(cur.get("char_alias_hiori", ""))
        self.n_alias.setText(cur.get("char_alias_nagomu", ""))
        
        profiles = cur.get("character_profiles", {})
        self.h_p.setPlainText(profiles.get("Hiori", config.HIORI_INFO))
        self.n_p.setPlainText(profiles.get("Nagomu", config.NAGOMU_INFO))
        
        self.h_color.setText(cur.get("color_hiori", config.COLOR_HIORI))
        self.n_color.setText(cur.get("color_nagomu", config.COLOR_NAGOMU))
        
        # 3. 纠音字典 (此处直接使用顶部导入的 json)
        name_map = cur.get("name_pronunciation_map", config.NAME_PRONUNCIATION_MAP)
        self.name_map.setText(json.dumps(name_map, ensure_ascii=False))

        # 4. 对话策略
        m_cfg = cur.get("DIALOGUE_MODES", config.DIALOGUE_MODES)
        for k, v in self.mode_inputs.items():
            if k in m_cfg:
                v["rounds"].setText(str(m_cfg[k].get("desc", "")))
                v["temp"].setValue(float(m_cfg[k].get("temperature", 0.7)))
                v["limit"].setValue(int(m_cfg[k].get("context_limit", 100)))

        # 5. 表情与资产映射回显
        
# 1. 回显上方语义字典
# 5. 表情与资产映射回显
# 5. 表情与资产映射回显 (分角色处理)
# 5. 表情与语义映射回显 (适配 16 槽位)
        for char_id in ["Hiori", "Nagomu"]:
            dict_key = f"emotion_semantic_map_{char_id}"
            # 获取数据，如果没有则使用 AssetLogic 的 16 条丰富预设
            semantic_data = cur.get(dict_key, AssetLogic.DEFAULT_MAP)
            
            # 将字典的键值对转为列表，方便按位置填充
            all_items = list(semantic_data.items())
            
            for i, entry in enumerate(self.semantic_entries[char_id]):
                if i < len(all_items):
                    k, v_list = all_items[i]
                    # 如果 key 是 "slot_" 开头，说明是无 ID 的占位符，UI 显示为空
                    entry['id'].setText("" if str(k).startswith("slot_") else str(k))
                    entry['kw'].setText(", ".join(v_list))
                else:
                    entry['id'].setText("")
                    entry['kw'].setText("")

        # 最后触发下方的资产扫描显示
        self.handle_expression_scan()
        
        
        # 6. 音色回显
# 语音回显逻辑修正
        v_map = api.get("voice_settings", {})
        v_remarks = api.get("voice_remarks", {}) # 读取备注

        for char in ["Hiori", "Nagomu"]:
            char_data = v_map.get(char, {})
            char_remarks = v_remarks.get(char, {})
            
            # 获取该角色所有的编号 Key
            all_codes = sorted(list(char_data.keys()))
            
            for i, code in enumerate(all_codes):
                if i < len(self.v_rows[char]):
                    row = self.v_rows[char][i]
                    row['code'].setText(code)
                    row['key'].setText(char_remarks.get(code, "")) # 回显备注
                    row['uri'].setText(char_data.get(code, ""))
                    

# Settings.py -> IntegratedSettings 类中的 handle_save 方法


    def handle_save(self):
        """ 整合保存逻辑：修复 NameError 并分离两套资产表 """
        try:
            # --- 1. 初始化容器，防止 NameError ---
            script_bundle = {} 
            api_bundle = {}
            
            
            # --- 1. 提取剧本模式数据 (Dialogue Modes) ---
            # 这一步将 UI 里的描述、温度、上下文轮数打包
            mode_data = {}
            for k, v in self.mode_inputs.items():
                mode_data[k] = {
                    "desc": v["rounds"].text(),
                    "temperature": v["temp"].value(),
                    "context_limit": v["limit"].value()
                }
# --- 2. 提取分角色语义定义 ---
            for char_id in ["Hiori", "Nagomu"]:
                char_semantic_bundle = {}
                for i, entry in enumerate(self.semantic_entries[char_id]):
                    c_id = entry['id'].text().strip()
                    kws_raw = entry['kw'].text().strip()
                    
                    # 即使没有 ID (c_id)，只要有关键词，也用 row_索引 作为 Key 保存
                    # 这样下次 load_to_ui 时内容就不会消失
                    save_key = c_id if c_id else f"slot_{i}"
                    if kws_raw:
                        kws = [k.strip() for k in kws_raw.split(",") if k.strip()]
                        char_semantic_bundle[save_key] = kws
                script_bundle[f"emotion_semantic_map_{char_id}"] = char_semantic_bundle         # --- 3. 提取两套资产映射 (核心修改点) ---
            # 扫描得到的静态图/GIF 映射
            exp_static_bundle = {}
            for cid in ["Hiori", "Nagomu"]:
                for item in self.exp_rows_static[cid]:
                    exp_static_bundle[item["file"]] = item["code"]

            # 扫描得到的 Live2D 精准表情映射
            exp_l2d_bundle = {}
            for cid in ["Hiori", "Nagomu"]:
                for item in self.exp_rows_l2d[cid]:
                    exp_l2d_bundle[item["file"]] = item["code"]

            # 将数据存入 script_bundle，确保 AssetLogic 能够正确读取
            script_bundle["expression_map"] = exp_static_bundle      # 供静态模式使用
            script_bundle["l2d_expression_map"] = exp_l2d_bundle     # 供 Live2D 模式使用


            # --- 4. 提取语音配置 ---
            voice_map = {"Hiori": {}, "Nagomu": {}}
            voice_remarks = {"Hiori": {}, "Nagomu": {}}
            for char in ["Hiori", "Nagomu"]:
                for row in self.v_rows[char]:
                    code = row['code'].text().strip()
                    if code and row['uri'].text().strip():
                        voice_map[char][code] = row['uri'].text().strip()
                        voice_remarks[char][code] = row['key'].text().strip()
            
            api_bundle["voice_settings"] = voice_map
            api_bundle["voice_remarks"] = voice_remarks

            # --- 5. 提取其他基础配置 ---
            l2d_bundle = {k: v.text().strip() for k, v in self.l2d_edits.items()}
            mode_data = {}
            for k, v in self.mode_inputs.items():
                mode_data[k] = {
                    "desc": v["rounds"].text(),
                    "temperature": v["temp"].value(),
                    "context_limit": v["limit"].value()
                }

            api_bundle.update({
                "api_key": self.api_key.text().strip(),
                "llm_base_url": self.llm_url.text().strip(),
                "llm_model": self.llm_model.text().strip(),
                "tts_base_url": self.tts_url.text().strip(),
                "tts_model": self.tts_model.text().strip(),
                "tts_key": self.tts_key.text().strip(),
                "vika_token": self.v_token.text().strip() if hasattr(self, 'v_token') else "",
                "vika_datasheet_id": self.v_id.text().strip() if hasattr(self, 'v_id') else "",
                "vika_web_url": self.vika_web_url.text().strip() if hasattr(self, 'vika_web_url') else ""
            })

            # 完善剧本配置包 (整合前面的 semantic_bundle)
            script_bundle.update({
                "char_name_hiori": self.h_name.text().strip(),
                "char_name_nagomu": self.n_name.text().strip(),
                "char_alias_hiori": self.h_alias.text().strip(),
                "char_alias_nagomu": self.n_alias.text().strip(),
                "hiori_info": self.h_p.toPlainText().strip(),
                "nagomu_info": self.n_p.toPlainText().strip(),
                "name_pronunciation_map": json.loads(self.name_map.text().strip()) if self.name_map.text().strip() else {},
                "prompt_template": self.prompt.toPlainText().strip(),
# --- 核心修改：使用正确的变量名，并同时保存两套映射 ---
                "expression_map": exp_static_bundle,     # 存图片/GIF映射
                "l2d_expression_map": exp_l2d_bundle,    # 存Live2D表情映射
                "color_hiori": self.h_color.text().strip(),
                "color_nagomu": self.n_color.text().strip(),
                "enable_voice": self.enable_voice_cb.isChecked(),
                "city": self.city.text().strip()
            })

# --- 6. 执行物理保存 ---
            # 这里的参数对应你的 SettingsLogic.save_all_configs
            ok, msg = self.logic.save_all_configs(
                api_bundle, 
                script_bundle, 
                mode_data, # mode_data 
                {}, # l2d_bundle
                exp_static_bundle, 
                voice_map
            )

            if ok:
                # 关键：保存后立即刷新 AssetLogic 的单例索引
                from asset_logic import AssetLogic
                AssetLogic.get_valid_assets() 
                QMessageBox.information(self, "完成", "设置已成功保存，资源索引已同步。")
            else:
                QMessageBox.warning(self, "保存失败", f"逻辑层报错: {msg}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "致命错误", f"保存流程崩溃: {e}")            

            
            
if __name__ == "__main__":
    app = QApplication(sys.argv); win = IntegratedSettings(); win.show(); sys.exit(app.exec())