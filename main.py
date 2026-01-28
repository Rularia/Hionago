import sys, os, datetime, multiprocessing
from PySide6.QtWidgets import (QApplication, QMainWindow, QLineEdit, QLabel, 
                               QPushButton, QMenu, QMessageBox, QGraphicsDropShadowEffect,
                               QWidget, QVBoxLayout, QScrollArea, QFrame) # 补全了漏掉的导入
from PySide6.QtCore import Qt, QPointF, QTimer, QSize, QRect, QThread, Signal, QPoint, QPropertyAnimation, QEasingCurve
# 补全 QPixmap
from PySide6.QtGui import QRegion, QFontMetrics, QCursor, QPainter, QColor, QBrush, QPen, QMovie, QPixmap, QIcon
from live2d_core import Live2DView

try:
    from panel import HistoryPanel       
    from card import VikaApp, DialogueCard, StoryScriptCard           
    from Settings import IntegratedSettings  
except ImportError as e:
    print(f"模块导入失败: {e}")

import config 

# --- 1. 轻量化提示浮窗 ---
class ToastOverlay(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background: rgba(40, 44, 52, 220);
            color: white;
            border-radius: 12px;
            padding: 5px 12px;
            font-family: 'Microsoft YaHei';
            font-size: 11px;
        """)
        self.hide()
        self.timer = QTimer()
        self.timer.timeout.connect(self.hide)

    def show_msg(self, text, pos):
        self.setText(text)
        self.adjustSize()
        self.move(pos.x() - self.width()//2, pos.y() - 50)
        self.show()
        self.timer.start(1500)

# --- 样式化输入框 ---
class FocusLineEdit(QLineEdit):
    def focusInEvent(self, event):
        self.setStyleSheet(f"background: rgba(255,255,255,0.8); border: 2px solid {config.COLOR_NAGOMU}; border-radius: 10px; padding: 0 35px;")
        super().focusInEvent(event)
    def focusOutEvent(self, event):
        self.setStyleSheet("background: rgba(255,255,255,0.5); border: 1px solid #ccc; border-radius: 10px; padding: 0 35px;")
        super().focusOutEvent(event)

# --- 气泡窗口 ---
class ChatBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(260)
        # 核心修复：开启自定义上下文菜单策略
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 背景容器（用来画主题色圆角矩形）
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(5, 5, 5, 5) # 留出一点边距给滚动条

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setAttribute(Qt.WA_TranslucentBackground)
        # 强制让滚动区域内部背景透明
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.viewport().setAttribute(Qt.WA_TranslucentBackground)
        
        # 滚动条样式（半透明白色）
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 100);
                border-radius: 2px;
            }
        """)

        # 文字标签
        self.label = QLabel()
        self.label.setWordWrap(True)
        # 移除背景设置，只留文字样式
        self.label.setStyleSheet("""
            color: white; 
            padding: 10px; 
            font-family: 'Microsoft YaHei'; 
            font-size: 13px; 
            font-weight: bold; 
            background: transparent;
        """)
        
        self.scroll.setWidget(self.label)
        self.container_layout.addWidget(self.scroll)
        self.main_layout.addWidget(self.container)

        self._bg_color = QColor(config.COLOR_NAGOMU)
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(400)

    def paintEvent(self, event):
        """在这里绘制主题色的方块背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self._bg_color)) # 使用实时传入的主题色
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        # 绘制圆角矩形
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 15, 15)

    def display(self, text, color_str, pos):
        self.opacity_anim.stop()
        self._bg_color = QColor(color_str) # 更新颜色（棕色或蓝色）
        self.label.setText(text)
        
        # 计算高度
        metrics = QFontMetrics(self.label.font())
        rect = metrics.boundingRect(QRect(0, 0, 220, 5000), Qt.TextWordWrap, text)
        
        # 设定高度：最小 80，最大 320（超过则出现进度条）
        target_h = max(80, min(320, rect.height() + 60))
        self.setFixedHeight(target_h)
        
        self.move(pos)
        self.setWindowOpacity(1.0)
        self.show()
        self.update() # 强制重绘背景颜色

    def fade_out(self):
        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.finished.connect(self.hide)
        self.opacity_anim.start()

# --- 语音监听线程 ---
class VoiceWatcher(QThread):
    finished_signal = Signal()
    def run(self):
        import pygame, time
        time.sleep(0.5)
        # 增加安全检查，防止 get_init 报错
        while True:
            try:
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): 
                    time.sleep(0.1)
                else:
                    break
            except: break
        self.finished_signal.emit()
# 新增：专门的异步获取器
# main.py 里的部分

class LLMWorker(QThread):
    finished_all = Signal(list) # 注意：现在只发这一个信号，传回解析好的整个列表

    def __init__(self, llm_service, forced_char, text, mode, window_info=""): 
        super().__init__()
        self.llm = llm_service
        self.forced_char = forced_char
        self.text = text
        self.mode = mode
        self.window_info = window_info # 现在这行代码不会报错了

    def run(self):
        # 对应 llm_service 里的新方法名
# 将 window_info 传给 llm_service 的方法
        # 建议修改 llm_service.py 的 get_full_response 接收这个参数
        result = self.llm.get_full_response(self.forced_char, self.text, self.mode, self.window_info)
        self.finished_all.emit(result)
# --- 主程序 ---
class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        # 1. 基础窗口设置
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(500, 550)

        # 2. 初始化核心服务
        from llm_service import LLMService
        from voice_service import VoiceService
        from screen_service import ScreenService  
        self.llm = LLMService()
        self.voice = VoiceService()
# <--- 导入新服务

        self.screen = ScreenService()             # <--- 实例化感知服务.
        
        # 【新增】初始化思考中 GIF 控件
# main.py 内部的 DesktopPet 类

        # 1. 确保在 __init__ 中调用了初始化函数
        self.init_thinking_gif()

    # --- 修复后的函数定义 ---
    def init_thinking_gif(self):
        """初始化用于显示思考状态的悬浮 GIF"""
        # 注意：以下所有行都必须缩进！
        self.thinking_label = QLabel(self)
        self.thinking_label.setStyleSheet("background: transparent;")
        self.thinking_label.hide() # 初始状态隐藏

        # 检查 config 中定义的路径是否存在
        if hasattr(config, 'THINKING_GIF_PATH') and os.path.exists(config.THINKING_GIF_PATH):
            from PySide6.QtGui import QMovie # 确保使用 PySide6
            from PySide6.QtCore import QSize

            self.thinking_movie = QMovie(config.THINKING_GIF_PATH)
            gif_size = QSize(80, 80) # 建议尺寸，可根据你的 GIF 调整
            self.thinking_movie.setScaledSize(gif_size)
            self.thinking_label.setMovie(self.thinking_movie)
            self.thinking_label.setFixedSize(gif_size)

            # 位置：放在输入框 (y=430) 正上方
            self.thinking_label.move(200, 400) 
        else:
            self.thinking_movie = None
            print("未找到 thinking.gif，请检查 Resource/Assets 目录")

        # 3. 初始化状态变量
        # ... 原有变量 ...
        self.last_seen_title = ""

        self.running_workers = set()
        self.sub_wins = []
        self.script_queue = []
        self.last_full_script = []
        self.run_mode = config.CURRENT_MODE
        self.current_forced_char = None
        self.current_bubble_side = "left"

        # 4. 创建双视图容器 (核心修复)
# --- 修改后的视图加载逻辑：严格二选一 ---
        self.use_live2d = False 
        if not config.USE_STATIC_IMAGE:
            try:
                self.view = Live2DView(config.MODEL_PATH, self)
                self.view.setGeometry(75, 70, 350, 350)
                self.use_live2d = True
                print(">>> 模式确认：Live2D 核心模式")
            except Exception as e:
                print(f"Live2D 加载失败: {e}")
                self.use_live2d = False

        if not self.use_live2d:
            self.view = QLabel(self)
            self.view.setGeometry(120, 120, 300, 300)
            self.view.setAlignment(Qt.AlignCenter)
            self.view.setScaledContents(False)
            self.set_static_emotion(0) # 初始加载一张图
            print(">>> 模式确认：静态图模式（带角色切换）")

        # 5. UI 组件
        self.bubble = ChatBubble()
        self.bubble.customContextMenuRequested.connect(self.show_bubble_menu)
        self.toast = ToastOverlay(self)

        self.input_field = FocusLineEdit(self)
        self.input_field.setGeometry(100, 430, 300, 35)
        self.input_field.setPlaceholderText(" 自由输入 / 点圆点指名...")
        self.input_field.returnPressed.connect(lambda: self.on_send(self.current_forced_char))

        self.btn_n = self.create_role_btn("●", config.COLOR_NAGOMU, 105, 432, "Nagomu")
        self.btn_h = self.create_role_btn("●", config.COLOR_HIORI, 365, 432, "Hiori")

        # 6. 定时器
        self.voice_timer = QTimer(self)
        self.voice_timer.timeout.connect(self.check_voice_status)
        
        # 7. 初始化显示
        self.apply_static_mask()
        self.drag_start_pos = QPointF(0, 0)
        self.pos_at_press = QPointF(0, 0)
        
        # 延迟获取天气
        QTimer.singleShot(1000, self.refresh_weather_async)
            
            
    def on_quit(self):
        """强力退出：释放所有资源并终止进程"""
        print("正在强力清理后台资源并退出...")
        if hasattr(self, 'watcher') and self.watcher.isRunning():
            self.watcher.terminate()
            self.watcher.wait()
        
        import pygame
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            pygame.quit()
        except: pass

        for win in self.sub_wins: win.close()
        self.bubble.close()
        
        QApplication.instance().quit()
        os._exit(0) # 核心：解决 Prompt 不返回

    def create_role_btn(self, text, color, x, y, char_name):
        btn = QPushButton(text, self)
        btn.setGeometry(x, y, 30, 30)
        btn.setStyleSheet(f"QPushButton {{ color: {color}; font-size: 20px; border: none; background: transparent; }}")
        btn.clicked.connect(lambda: self.handle_role_select(char_name, btn))
        return btn

    def handle_role_select(self, char_name, btn):
        """指名功能的触发逻辑"""
        self.current_forced_char = char_name
        text = self.input_field.text().strip()

        # --- 按钮视觉反馈逻辑 (保持原样) ---
        for b in [self.btn_n, self.btn_h]:
            b.setGraphicsEffect(None)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20); shadow.setColor(QColor(255, 255, 255, 200)); shadow.setOffset(0, 0)
        btn.setGraphicsEffect(shadow)
        QTimer.singleShot(500, lambda: btn.setGraphicsEffect(None))
        
        # --- 核心判断逻辑 ---
        if not text:
            # 1. 抓取环境数据
            win_title = self.screen.get_active_window_title()
            win_hint = self.screen.get_context_hint(win_title)
            weather = getattr(config, 'WEATHER_NOW', '未知')
            curr_time = datetime.datetime.now().strftime("%H:%M")
            
            # 2. 构造“感知引导词”
            # 这个 prompt 只有 AI 能看到，不会显示在气泡里
            perceive_prompt = (
                f"（感知启动：现在是 {curr_time}，天气 {weather}。 "
                f"你注意到用户正在：【{win_title}】({win_hint})。 "
                f"请结合以上信息，用你的身份简洁地打个招呼或吐槽一句，不要太生硬。）"
            )
            
            # 3. 触发特殊的发送方法
            self.on_perceive_send(char_name, perceive_prompt)
        else:
            # 如果有输入，执行正常的发送
            self.on_send(char_name)
            
    def on_perceive_send(self, forced_char, prompt_text):
        """专门处理环境感知的异步请求"""
        # 清理当前语音和队列
        self.voice_timer.stop()
        self.script_queue = [] 

        # 启动 LLM 线程 (模式强制设为 short 保证轻量)
        worker = LLMWorker(self.llm, forced_char, prompt_text, "short")
        self.running_workers.add(worker)
        worker.finished_all.connect(lambda s: self.handle_llm_result(worker, s))
        worker.start()
        
###-------------------------
        
        
    def reset_btn_style(self, btn, char_name):
        orig_color = config.COLOR_NAGOMU if char_name == "Nagomu" else config.COLOR_HIORI
        btn.setStyleSheet(f"QPushButton {{ color: {orig_color}; font-size: 20px; border: none; background: transparent; }}")
        btn.setGraphicsEffect(None)

    def apply_static_mask(self):
        """
        确保点击区域覆盖了所有控件
        如果指名点不动，通常是这里没加进去
        """
        # 扩大一点范围以容纳阴影
        model_rect = QRect(130, 110, 265, 310) 
        input_rect = QRect(100, 430, 300, 50)
        # 按钮区域
        btn_n_rect = self.btn_n.geometry()
        btn_h_rect = self.btn_h.geometry()
        
        full_region = QRegion(model_rect).united(QRegion(input_rect)).united(QRegion(btn_n_rect)).united(QRegion(btn_h_rect))
        self.setMask(full_region)

# DesktopPet 类中的相关方法修改

# main.py 约 360 行处

    def on_send(self, forced_char=None):
        text = self.input_field.text().strip()
        if not text and not forced_char: return
        
        effective_text = text if text else "（打个招呼）"
        self.input_field.clear()

        # --- 新增：获取窗口信息 ---
        win_title = self.screen.get_active_window_title() if hasattr(self, 'screen') else ""
        # -----------------------

    # 【新增】显示思考中 GIF
        if self.thinking_movie and self.thinking_movie.isValid():
            self.thinking_label.show()
            self.thinking_label.raise_()
            self.thinking_movie.start()
        
        self.voice_timer.stop()
        self.script_queue = [] 

        # 关键点：实例化 worker 时传入 win_title
        worker = LLMWorker(self.llm, forced_char, effective_text, self.run_mode, window_info=win_title)
        self.running_workers.add(worker)
        worker.finished_all.connect(lambda s: self.handle_llm_result(worker, s))
        worker.start()
# main.py

# --- main.py ---

    def handle_llm_result(self, worker, script_list):
        # 【新增】停止并隐藏思考中 GIF
        if self.thinking_label.isVisible():
            self.thinking_movie.stop()
            self.thinking_label.hide()
        
        # ... (已有的处理 script_list 的代码)
        # ...
        if worker in self.running_workers:
            self.running_workers.remove(worker)
        worker.deleteLater()
        
        if not script_list:
            self.toast.show_msg("😵 AI 暂时断线了...", self.input_field.pos())
            return
        
        self.script_queue = script_list
        self.last_full_script = script_list.copy()

        if self.run_mode == 'story':
            self.bubble.fade_out()
            # 序列化数据
            full_data = " || ".join([f"{d['char']}:{d['ja']}@{d['zh']}" for d in script_list])
            try:
                # 【核心改动】：这里改用 StoryScriptCard
                self.story_win = StoryScriptCard("实时剧本生成", full_data)
                self.story_win.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
                # 连接收藏信号
                self.story_win.fav_clicked_signal.connect(self.save_to_fav)
                self.story_win.show()
                self.sub_wins.append(self.story_win)
            except Exception as e:
                print(f"弹出剧本面板失败: {e}")
                self.play_next_line()
        else:
            # 普通对话模式直接播放
            self.play_next_line()

    # --- 修复右键菜单 ---
    def setup_bubble(self):
        # 确保气泡支持右键
        self.bubble.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bubble.customContextMenuRequested.connect(self.show_bubble_menu)

    def show_bubble_menu(self, pos):
        if not hasattr(self, 'last_full_script') or not self.last_full_script: return
        menu = QMenu(self.bubble)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #ccc; }")
        fav_act = menu.addAction("⭐ 收藏本轮对话")
        action = menu.exec(QCursor.pos())
        if action == fav_act:
            self.save_to_fav()
        
        
    def handle_worker_done(self, worker, script_list):
        if worker in self.running_workers:
            self.running_workers.remove(worker)
        worker.deleteLater()
        self.handle_full_script(script_list)

    def handle_output(self, worker, script_list):
        # 此时线程已完成，处理结果
        self.handle_full_script(script_list)

    def cleanup_worker(self, worker):
        # 任务彻底结束，从集合移除
        if worker in self.running_workers:
            self.running_workers.remove(worker)
        worker.deleteLater()


    def handle_full_script(self, script_list):
        """处理获取到的完整对话列表"""
        if not script_list:
            self.toast.show_msg("😵 AI 暂时断线了...", self.input_field.pos())
            return
            
        self.script_queue = script_list
        self.last_full_script = script_list.copy() # 用于收藏
        
        # 只要拿到列表，就开始播放第一条
        self.play_next_line()


    # main.py 内部逻辑片段
    def play_next_line(self):
        if not hasattr(self, 'script_queue') or not self.script_queue:
            QTimer.singleShot(3000, self.bubble.fade_out)
            return

        line = self.script_queue.pop(0) 
        char_id = str(line["char"])
        exp_num = int(line["exp"]) 
        file_name = line.get("file_name", "") # 拿到 settings.json 里的文件名

        if self.use_live2d:
            if "nagomu" in char_id.lower():
                if hasattr(self.view, 'set_expression'):
                    print(f">>> [Live2D] 表情索引: {exp_num}")
                    self.view.set_expression(exp_num)
        else:
            # ✅ 修复：直接调用我们写好的 sprite_view 逻辑
            # 注意：如果你的主窗口里的显示控件叫 self.static_view，就改用它
            if hasattr(self, 'static_view') and hasattr(self.static_view, 'set_image_by_name'):
                self.static_view.set_image_by_name(file_name)
            elif hasattr(self, 'view') and hasattr(self.view, 'set_image_by_name'):
                self.view.set_image_by_name(file_name)
            else:
                # 如果你还没把控件换成 SpriteView 类，就调用下面的修复版私有方法
                self._update_static_view_fixed(file_name)

        # ... 气泡显示逻辑 ...
        offset_x = 40 if char_id == "Nagomu" else 220
        pos = self.pos() + QPoint(offset_x, -100)
        color = config.COLOR_NAGOMU if char_id == "Nagomu" else config.COLOR_HIORI
        display_name = config.CHAR_NAME_NAGOMU if char_id == "Nagomu" else config.CHAR_NAME_HIORI
        self.bubble.display(f"【{display_name}】\n{line['ja']}\n{line['zh']}", color, pos)

# --- 修改后的语音与跳转逻辑 ---
        
        # 1. 检查当前是否启用了语音 (确保这里的变量名与你 Settings.py 中保存的一致)
        # 如果 config.py 里没有，建议直接从你保存的 settings 字典里取值
        # --- 重点：主程序也直接读取 settings.json 里的开关 ---
        import json
        settings_path = os.path.join(config.RESOURCE_DIR, "settings.json")
        is_voice_enabled = True # 默认开启
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                is_voice_enabled = user_settings.get("enable_voice", True)
        except: pass

        if is_voice_enabled:
            # 开启语音模式：按原逻辑走
            try:
                self.voice.speak(char_id, str(exp_num), line["ja"])
                self.voice_timer.start(500) # 启动定时器监听 pygame 是否播完
            except Exception as e:
                print(f"语音失败: {e}")
                QTimer.singleShot(2000, self.play_next_line)
        else:
            # 静音模式：根据字数计算等待时间
            # 基础 3 秒 + 每个字 200 毫秒
            wait_ms = 3000 + (len(line["zh"]) * 175)
            print(f"静音模式，气泡将停留 {wait_ms}ms")
            QTimer.singleShot(wait_ms, self.play_next_line)
            #——-----------------------

    def _update_static_view_fixed(self, file_name):
        """
        如果在 main.py 内部直接渲染，必须使用这套逻辑：
        彻底销毁旧 Movie，重新创建新 Movie
        """
        if not file_name: return
        path = os.path.join(config.SPRITE_DIR, file_name).replace("\\", "/")
        if not os.path.exists(path):
            print(f"⚠️ 文件不存在: {path}")
            return

        # 获取当前用来显示的那个 Label (可能是 self.view 或 self.static_view)
        target_label = getattr(self, 'static_view', self.view)

        if path.lower().endswith('.gif'):
            # 停止并删除旧的 movie 对象
            if hasattr(self, '_current_movie_obj') and self._current_movie_obj:
                self._current_movie_obj.stop()
                self._current_movie_obj.deleteLater()
            
            # 创建全新的 Movie
            self._current_movie_obj = QMovie(path)
            self._current_movie_obj.setCacheMode(QMovie.CacheAll)
            
            # 确保尺寸正确
            s = target_label.size()
            if s.width() < 10: s = self.size() # 保底用窗口大小
            self._current_movie_obj.setScaledSize(s)
            
            target_label.setMovie(self._current_movie_obj)
            # 延迟 50ms 启动，防止线程冲突
            QTimer.singleShot(50, self._current_movie_obj.start)
            print(f"✅ [main] 已重载 GIF: {file_name}")
        else:
            target_label.setMovie(None)
            pix = QPixmap(path)
            target_label.setPixmap(pix.scaled(target_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            print(f"✅ [main] 已重载 静态图: {file_name}")    
    
    def check_voice_status(self):
        """检查语音是否放完，放完就下一句"""
        import pygame
        try:
            if not pygame.mixer.music.get_busy():
                self.voice_timer.stop()
                self.play_next_line()
        except: self.voice_timer.stop()

    def handle_role_select(self, name, btn):
        """指名功能的正确触发逻辑"""
        self.current_forced_char = name
        # UI反馈
        for b in [self.btn_n, self.btn_h]: b.setGraphicsEffect(None)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20); shadow.setColor(QColor(255,255,255)); shadow.setOffset(0,0)
        btn.setGraphicsEffect(shadow)
        
        # 立即发送，清空指名缓存
        self.on_send(forced_char=name)
        QTimer.singleShot(500, lambda: btn.setGraphicsEffect(None))


    def set_static_emotion(self, target):
        """ 增强版资产扫描：文件名精准匹配 -> 关键词匹配 -> 文件夹首张图兜底 """
        if self.use_live2d: return # Live2D 模式不需要这个

        file_name = None
        all_files = []
        try:
            # 只扫描支持的图片格式
            all_files = [f for f in os.listdir(config.SPRITE_DIR) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        except Exception as e:
            print(f"读取目录失败: {e}")

        if not all_files: return

        # 策略1：寻找包含 target 字符的文件 (target 可能是 'happy' 或 '3')
        target_str = str(target).lower()
        for f in all_files:
            if target_str in f.lower():
                file_name = f
                break
        
        # 策略2：如果策略1没找到，找带 "normal" 关键字的图
        if not file_name:
            for f in all_files:
                if "normal" in f.lower():
                    file_name = f
                    break
        
        # 策略3：最后兜底，直接拿文件夹第一张图
        if not file_name:
            file_name = all_files[0]

        path = os.path.join(config.SPRITE_DIR, file_name).replace("\\", "/")
        
        # 执行渲染
        if path.lower().endswith('.gif'):
            if not hasattr(self, '_movie'):
                self._movie = QMovie(path)
                self.view.setMovie(self._movie)
            else:
                self._movie.setFileName(path)
            self._movie.setScaledSize(self.view.size())
            self._movie.start()
        else:
            self.view.setMovie(None) # 停止动态图
            pix = QPixmap(path)
            self.view.setPixmap(pix.scaled(self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))                
###----------------------save to fav                
                
    def save_to_fav(self):
        try:
            if not self.last_full_script: return
            
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            card_data = " || ".join([f"{d['char']}:{d['ja']}@{d['zh']}" for d in self.last_full_script])
            
            with open(config.FAVORITES_PATH, "a", encoding="utf-8") as f:
                f.write(f"{now} | {card_data}\n")
                
            self.toast.show_msg("✨ 已存入档案", self.input_field.pos() + QPoint(150, 0))
        except Exception as e: 
            print(f"Save error: {e}")

# --- 统一后的角色选择与发送逻辑 ---

    def create_role_btn(self, text, color, x, y, char_name):
        """统一的按钮创建函数"""
        btn = QPushButton(text, self)
        btn.setGeometry(x, y, 30, 30)
        # 初始样式
        btn.setStyleSheet(f"QPushButton {{ color: {color}; font-size: 20px; border: none; background: transparent; }}")
        # 鼠标指针变小手
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.handle_role_select(char_name, btn))
        return btn



    def change_llm_mode(self, mode_key):
        # 1. 更新运行时状态
        self.run_mode = mode_key
        config.CURRENT_MODE = mode_key 
        
        # 2. 定义与菜单一致的名称映射
        mode_name_map = {
            "short": "日常短句",
            "medium": "深度互动",
            "story": "剧本长谈"
        }
        
        # 3. 获取显示名称：优先从映射表找，找不到再尝试从配置找，最后保底“默认”
        m_name = mode_name_map.get(mode_key) or \
                 config.DIALOGUE_MODES.get(mode_key, {}).get('name') or \
                 "默认"
        
        # 4. 弹出提示
        self.toast.show_msg(f"✅ 模式：{m_name}", self.input_field.pos() + QPoint(150, 0))
        
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # 优化样式：增加选中的勾选标志样式
        menu.setStyleSheet("""
            QMenu { background-color: #F0F2F5; color: #4A5568; border: 1px solid #D1D5DB; font-family: 'Microsoft YaHei'; } 
            QMenu::item { padding: 8px 30px 8px 25px; } 
            QMenu::item:selected { background-color: #EBF8FF; color: #3182CE; }
            QMenu::check-indicator { width: 15px; height: 15px; }
        """)

        # 1. 天气与位置显示
        weather = getattr(config, 'WEATHER_NOW', '加载中...')
        menu.addAction(f"📍 {config.CITY} | {weather}").setEnabled(False)
        menu.addSeparator()

        # 2. 动态获取模式配置，增加容错
        all_modes = getattr(config, 'DIALOGUE_MODES', {})
        current_mode_key = getattr(self, 'run_mode', 'short')
        current_mode_name = all_modes.get(current_mode_key, {}).get('name', '默认模式')

# 3. 创建子菜单显示当前模式
# main.py 里的右键菜单部分

        # 1. 获取当前模式的显示名称
        current_mode_key = config.CURRENT_MODE 
        all_modes = config.get_safe_modes()
        current_mode_data = all_modes.get(current_mode_key, {})

        # 定义一个固定的 ID 到中文名的映射
        mode_name_map = {
            "short": "日常短句",
            "medium": "深度互动",
            "story": "剧本长谈"
        }

        # 优先取映射表里的名字，没有再取配置里的 name 或 key
        current_display_name = mode_name_map.get(current_mode_key) or current_mode_data.get('name') or current_mode_key

# 2. 修改菜单标题：去掉“模式切换”和“括号”，只保留表情和名字
        mode_menu = menu.addMenu(f"🎭 {current_display_name}")

# 3. 循环添加子选项
        for m_key, m_val in all_modes.items():
            m_display_name = mode_name_map.get(m_key) or m_val.get('name') or m_key
            
            action = mode_menu.addAction(m_display_name)
            action.setCheckable(True)
            if m_key == current_mode_key:
                action.setChecked(True)
            action.triggered.connect(lambda checked=False, k=m_key: self.change_llm_mode(k))

            
        # 4. 原有功能入口
        act_panel = menu.addAction("📢 语音档案库")
        act_card = menu.addAction("🖼️ 查看收藏图片对话")
        act_set = menu.addAction("⚙️ 剧场核心配置")
        menu.addSeparator()
        act_quit = menu.addAction("❌ 退出剧场")

        action = menu.exec(event.globalPos())

# 3. 处理跳转 (注意：这里去掉了旧的 if action == act_mode 逻辑)
        if action == act_panel: 
            self.p_win = HistoryPanel(); self.p_win.show(); self.sub_wins.append(self.p_win)
        elif action == act_card: 
            self.c_win = VikaApp(); self.c_win.show(); self.sub_wins.append(self.c_win)
        elif action == act_set: 
            self.s_win = IntegratedSettings(); self.s_win.show(); self.sub_wins.append(self.s_win)
        elif action == act_quit: 
            self.on_quit()


    def show_bubble_menu(self, pos):
        if not self.last_full_script: return
        menu = QMenu(self.bubble)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowStaysOnTopHint)
        fav_act = menu.addAction("⭐ 收藏本轮对话")
        action = menu.exec(QCursor.pos())
        if action == fav_act: self.save_to_fav()

    def save_to_fav(self):
        try:
            if not self.last_full_script: return
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            card_data = " || ".join([f"{d['char']}:{d['ja']}@{d['zh']}" for d in self.last_full_script])
            # 使用 config 路径
            with open(config.FAVORITES_PATH, "a", encoding="utf-8") as f: f.write(f"{now} | {card_data}\n")
            self.toast.show_msg("✨ 已存入档案", self.input_field.pos() + QPoint(150, 0))
        except Exception as e: print(f"Save error: {e}")

    def refresh_weather_async(self):
        import threading
        def _get():
            try: config.WEATHER_NOW = config.get_weather_data(config.CITY)
            except: config.WEATHER_NOW = "未知"
        threading.Thread(target=_get, daemon=True).start()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            diff = (event.globalPosition() - self.drag_start_pos).toPoint()
            # 将结果加上 .toPoint() 转换成整数
            self.move(self.pos_at_press + diff)
            if self.bubble.isVisible():
                offset_x = 40 if self.current_bubble_side == "left" else 220
                self.bubble.move(self.pos() + QPoint(offset_x, -80))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.globalPosition()
            self.pos_at_press = self.pos()

    def closeEvent(self, event):
        self.on_quit() # 拦截右上角关闭
        event.accept()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())