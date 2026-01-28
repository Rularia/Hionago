import sys, os, requests, random, threading, multiprocessing, json, datetime
from io import BytesIO
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                               QLabel, QHBoxLayout, QScrollArea, QFrame, QToolTip, QMenu, QMessageBox)
from PySide6.QtCore import QTimer, Qt, Signal, QObject
from PySide6.QtGui import QPixmap, QImage, QAction
from PIL import Image
import datetime


# 导入路径配置
try:
    from config import FAVORITES_PATH, VIKA_TOKEN, VIKA_ID, RESOURCE_DIR
except ImportError:
    VIKA_TOKEN = ""
    VIKA_ID = ""
    RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resource")
    FAVORITES_PATH = os.path.join(RESOURCE_DIR, "favorites.txt")
    
    # --- 辅助函数：从 JSON 加载角色颜色 ---
def get_char_colors():
    settings_path = os.path.join(RESOURCE_DIR, "settings.json")
    default_colors = {"Nagomu": "#5D4037", "Hiori": "#1B2647"}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    "Nagomu": data.get("color_nagomu", default_colors["Nagomu"]),
                    "Hiori": data.get("color_hiori", default_colors["Hiori"])
                }
        except: pass
    return default_colors
# =================核心抽图模块=================
class VikaCore(QObject):
    image_loaded = Signal(QPixmap)

    def __init__(self):
        super().__init__()
        # ✅ 已脱敏：从 config 导入，不再硬编码
        self.api_token = VIKA_TOKEN 
        self.datasheet_id = VIKA_ID
        self.field_name = "附件"

    def random_pick(self):
        # 基础校验
        if not self.api_token or not self.datasheet_id:
            print("VikaCore Error: 维格表 API Token 或 Datasheet ID 未配置。")
            return

        try:
            url = f"https://api.vika.cn/fusion/v1/datasheets/{self.datasheet_id}/records"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            resp = requests.get(url, headers=headers, timeout=10).json()
            records = resp.get("data", {}).get("records", [])
            
            if records:
                lucky = random.choice(records)
                imgs = lucky.get("fields", {}).get(self.field_name, [])
                if imgs:
                    data = requests.get(imgs[0].get("url"), timeout=10).content
                    img = Image.open(BytesIO(data))
                    img.thumbnail((500, 500))
                    
                    byte_arr = BytesIO()
                    img.save(byte_arr, format='PNG')
                    qimg = QImage.fromData(byte_arr.getvalue())
                    pixmap = QPixmap.fromImage(qimg)
                    self.image_loaded.emit(pixmap)
        except Exception as e:
            print(f"VikaCore Error: {e}")

# =================对话卡片组件=================
class DialogueCard(QFrame):
    delete_requested = Signal()  # 用于通知主界面刷新列表
    fav_clicked_signal = Signal(str) # 用于收藏按钮

    def __init__(self, full_line, dialogue_data):
        super().__init__()
        self.full_line = full_line       
        self.dialogue_data = dialogue_data 
        self.setFrameShape(QFrame.StyledPanel)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # 加载角色颜色配置
        self.colors = get_char_colors() 

        self.setStyleSheet("""
            DialogueCard { 
                background-color: #FFFFFF; border-radius: 12px; 
                border: 1px solid #E2E8F0; margin: 4px; padding: 12px;
            }
            DialogueCard:hover { border-color: #3182CE; background-color: #F8FAFC; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 解析对话内容
        dialogue_segments = dialogue_data.split(" || ")
        for segment in dialogue_segments:
            if ":" in segment:
                try:
                    name_part, content_part = segment.split(":", 1)
                    name = name_part.strip()
                    char_color = self.colors.get(name, "#4A5568")
                    
                    # 提取正文（去掉可能的脚本标记 @）
                    display_text = content_part.split("@")[-1].strip() if "@" in content_part else content_part.strip()
                    
                    row_label = QLabel(f"<b style='color: {char_color};'>{name}</b><br/>{display_text}")
                    row_label.setWordWrap(True)
                    row_label.setStyleSheet("color: #4A5568; font-size: 13px; line-height: 140%; border: none; background: transparent;")
                    # 允许穿透点击，确保右键能触发在卡片上
                    row_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                    
                    layout.addWidget(row_label)
                except: continue

        # 特殊逻辑：如果是“剧本模式”或带有剧本标签，显示收藏按钮
        if full_line == "Story Mode" or "剧本" in full_line:
            self.fav_btn = QPushButton("⭐ 收藏整段剧本")
            self.fav_btn.setContextMenuPolicy(Qt.NoContextMenu) # 防止按钮拦截右键
            self.fav_btn.setStyleSheet("""
                QPushButton { background: #F6AD55; color: white; font-weight: bold; border-radius: 6px; padding: 8px; }
                QPushButton:hover { background: #ED8936; }
            """)
            self.fav_btn.clicked.connect(lambda: self.fav_clicked_signal.emit(self.dialogue_data))
            layout.addWidget(self.fav_btn)

    # ======= 核心右键菜单逻辑 (确保在类内) =======
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #CBD5E0; padding: 4px; border-radius: 4px; }
            QMenu::item { padding: 6px 25px; border-radius: 2px; }
            QMenu::item:selected { background-color: #EBF8FF; color: #2B6CB0; }
        """)
        
        copy_action = QAction("📋 复制全文内容", self)
        copy_action.triggered.connect(self.do_copy)
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑 从收藏中移除", self)
        delete_action.triggered.connect(self.do_delete)
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())

    def do_copy(self):
        # 将 || 换行符还原为普通的换行
        clean_text = self.dialogue_data.replace(" || ", "\n")
        QApplication.clipboard().setText(clean_text)
        # 在鼠标位置显示气泡提示
        QToolTip.showText(QCursor.pos(), "✅ 内容已复制到剪贴板")

    def do_delete(self):
        reply = QMessageBox.question(self, "确认移除", "确定要将这段对话从收藏档案中移除吗？", 
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(FAVORITES_PATH):
                    with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    # 过滤掉当前行
                    new_lines = [l for l in lines if l.strip() != self.full_line.strip()]
                    
                    with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    
                    # 发送信号让主界面重载
                    self.delete_requested.emit()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")


class StoryScriptCard(QWidget):
    """论坛体剧本展示窗口：支持逐条显示与楼层样式"""
    fav_clicked_signal = Signal(str)

    def __init__(self, title, dialogue_data):
        super().__init__()
        self.dialogue_data = dialogue_data
        self.segments = dialogue_data.split(" || ")
        self.current_index = 0
        
        self.setWindowTitle(title)
        self.resize(500, 700)
        self.setStyleSheet("background-color: #F0F2F5; font-family: 'Microsoft YaHei';")
        
        # 主布局
        self.layout = QVBoxLayout(self)
        
        # 顶部标题栏
        header = QLabel(f"💬 贴吧剧场：{title}")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1A202C; padding: 10px;")
        self.layout.addWidget(header)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.content_layout.setSpacing(15)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

        # 底部按钮（初始隐藏，播完显示）
        self.footer = QHBoxLayout()
        self.btn_fav = QPushButton("⭐ 收藏整段剧本")
        self.btn_fav.setStyleSheet("background: #3182CE; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        self.btn_fav.hide() 
        self.btn_fav.clicked.connect(lambda: self.fav_clicked_signal.emit(self.dialogue_data))
        
        self.footer.addWidget(self.btn_fav)
        self.layout.addLayout(self.footer)

        # 角色颜色映射
        self.colors = get_char_colors() # 从 JSON 加载 # 论坛体可以使用更鲜艳的色调

        # 启动定时器，逐条显示（间隔 800ms）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.display_next_post)
        self.timer.start(2000)

    def display_next_post(self):
        if self.current_index >= len(self.segments):
            self.timer.stop()
            self.btn_fav.show() # 播完了显示收藏按钮
            return

        seg = self.segments[self.current_index]
        if ":" in seg:
            try:
                name_part, content_part = seg.split(":", 1)
                name = name_part.strip()
                color = self.colors.get(name, "#4A5568")
                text = content_part.split("@")[-1].strip() if "@" in content_part else content_part.strip()

                # 创建回帖容器
                post_frame = QFrame()
                post_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: white;
                        border: 1px solid #E2E8F0;
                        border-radius: 4px;
                    }}
                """)
                post_layout = QVBoxLayout(post_frame)
                post_layout.setContentsMargins(12, 10, 12, 10)

                # 论坛页眉：#楼层 角色名 发表于 时间
                header_layout = QHBoxLayout()
                floor_num = f"#{self.current_index + 1}"
                
                # 模拟时间：每层楼间隔几秒
                now = datetime.datetime.now()
                fake_time = (now + datetime.timedelta(seconds=self.current_index * 5)).strftime("%Y-%m-%d %H:%M:%S")

                header_text = f"<span style='color: #718096; font-weight: bold;'>{floor_num}</span> " \
                              f"<span style='color: {color}; font-weight: 800;'>{name}</span>"
                
                header_label = QLabel(header_text)
                time_label = QLabel(f"发表于 {fake_time}")
                time_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
                time_label.setAlignment(Qt.AlignRight)

                header_layout.addWidget(header_label)
                header_layout.addStretch()
                header_layout.addWidget(time_label)

                # 正文
                content_label = QLabel(text)
                content_label.setWordWrap(True)
                content_label.setStyleSheet("color: #2D3748; font-size: 14px; margin-top: 5px; line-height: 150%;")

                post_layout.addLayout(header_layout)
                post_layout.addWidget(content_label)

                self.content_layout.addWidget(post_frame)
                
                # 自动滚动到底部
                QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
                    self.scroll.verticalScrollBar().maximum()
                ))

            except Exception as e:
                print(f"Post layout error: {e}")

        self.current_index += 1        
##-----------
            
            
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #CBD5E0; padding: 4px; border-radius: 4px; }
            QMenu::item { padding: 6px 25px; border-radius: 2px; }
            QMenu::item:selected { background-color: #EBF8FF; color: #2B6CB0; }
        """)
        
        copy_action = QAction("📋 复制全文内容", self)
        copy_action.triggered.connect(self.do_copy)
        menu.addAction(copy_action)
        menu.addSeparator()
        
        delete_action = QAction("🗑 从收藏中移除", self)
        delete_action.triggered.connect(self.do_delete)
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())

    def do_copy(self):
        clean_text = self.dialogue_data.replace(" || ", "\n")
        QApplication.clipboard().setText(clean_text)
        QToolTip.showText(self.mapToGlobal(self.rect().center()), "✅ 内容已复制")

    def do_delete(self):
        reply = QMessageBox.question(self, "确认移除", "确定要将这段对话从收藏档案中移除吗？", 
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(FAVORITES_PATH):
                    with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    new_lines = [l for l in lines if l.strip() != self.full_line.strip()]
                    
                    with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    
                    self.delete_requested.emit()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")
                
    # 在 card.py 的 DialogueCard 中添加
# 在布局最后添加一个关闭按钮
        self.close_btn = QPushButton("× 关闭窗口")
        self.close_btn.setStyleSheet("""
            QPushButton { 
                background-color: #E2E8F0; color: #4A5568; 
                border-radius: 6px; padding: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #CBD5E0; }
        """)
        self.close_btn.clicked.connect(self.window().close if self.window() else self.close)
        layout.addWidget(self.close_btn)

# =================抽图悬浮窗与主窗口部分=================
class ImageFloatingWin(QLabel):
    def __init__(self, pixmap):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setPixmap(pixmap)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - pixmap.width()) // 2 + random.randint(-60, 60)
        y = (screen.height() - pixmap.height()) // 2 + random.randint(-60, 60)
        self.move(x, y)
        self.show()
    def mousePressEvent(self, event):
        self.close()

class VikaApp(QWidget):
    def __init__(self):
        super().__init__()
        self.core = VikaCore()
        self.core.image_loaded.connect(self.display_image)
        self.previews = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("收藏档案库")
        self.resize(550, 800)
        self.setStyleSheet("background-color: #EDF2F7; font-family: 'Microsoft YaHei';")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        self.btn_pick = QPushButton("🎲 随机抽取角色画稿")
        self.btn_pick.setFixedHeight(50)
        self.btn_pick.setStyleSheet("""
            QPushButton { 
                background-color: #4A5568; color: white; border-radius: 12px; 
                font-weight: bold; font-size: 14px; margin-bottom: 5px;
            }
            QPushButton:hover { background-color: #2D3748; }
        """)
        self.btn_pick.clicked.connect(self.action_pick)
        self.main_layout.addWidget(self.btn_pick)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        
        self.waterfall_layout = QHBoxLayout(self.container)
        self.waterfall_layout.setContentsMargins(0, 0, 0, 0)
        self.waterfall_layout.setSpacing(10)
        self.waterfall_layout.setAlignment(Qt.AlignTop)

        self.columns = [QVBoxLayout() for _ in range(2)]
        for col in self.columns:
            col.setAlignment(Qt.AlignTop)
            col.setSpacing(0)
            self.waterfall_layout.addLayout(col)

        self.load_favorites()
        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)

    def clear_layout(self):
        for col in self.columns:
            while col.count():
                item = col.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def load_favorites(self):
        self.clear_layout()
        if not os.path.exists(FAVORITES_PATH): return
        try:
            with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                valid_count = 0
                for line in reversed(lines):
                    line = line.strip()
                    if "|" in line and ":" in line:
                        dialogue_data = line.split("|", 1)[-1].strip()
                        if dialogue_data:
                            card = DialogueCard(line, dialogue_data)
                            card.delete_requested.connect(self.load_favorites)
                            self.columns[valid_count % 2].addWidget(card)
                            valid_count += 1
        except Exception as e:
            print(f"Card load error: {e}")

    def action_pick(self):
        threading.Thread(target=self.core.random_pick, daemon=True).start()

    def display_image(self, pixmap):
        win = ImageFloatingWin(pixmap)
        self.previews.append(win)
        if len(self.previews) > 5: self.previews.pop(0).close()

if __name__ == "__main__":
    multiprocessing.freeze_support() 
    app = QApplication(sys.argv)
    window = VikaApp()
    window.show()
    sys.exit(app.exec())