# live2d_core.py 
import live2d.v3 as live2d
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCursor
import config 
import os

class Live2DView(QOpenGLWidget):
    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.model = None
        self.cur_x, self.cur_y = 0, 0
        self.current_exp_val = 0.0 # 记录当前表情等级 (0.0-3.0)
        
        self.setMouseTracking(True)
        
        # 路径安全检查：防止中文路径导致黑屏
        if any(ord(c) > 127 for c in os.path.abspath(model_path)):
            print("⚠️ 警告: 模型路径包含非英文，可能导致加载失败。")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_and_track)
        self.timer.start(33)

    def update_and_track(self):
        """ 实时同步鼠标坐标并刷新绘图 """
        if not self.model: return
        
        w = self.width() if self.width() > 0 else 1
        h = self.height() if self.height() > 0 else 1
        
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        
        # 计算映射坐标并严格限制在 -1.0 到 1.0
        self.cur_x = max(-1.0, min(1.0, (local_pos.x() / w) * 2 - 1))
        self.cur_y = max(-1.0, min(1.0, -((local_pos.y() / h) * 2 - 1)))
        
        self.update() 

    def set_expression(self, exp_id):
        """ 切换表情：更新表情数值映射 """
        try:
            self.current_exp_val = float(exp_id)
        except Exception as e:
            print(f"表情设置错误: {e}")

    def initializeGL(self):
        try:
            live2d.init()
            live2d.glInit()
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(self.model_path)
            # 这里的 Scale 配合 ResizeGL 使用，确保比例正常
            self.model.SetScale(1.1) 
        except Exception as e:
            print(f"Live2D 初始化失败: {e}")

    def paintGL(self):
        if not self.model: return
        live2d.clearBuffer(0, 0, 0, 0)
        
        # --- 1. 获取动态配置 (从 config.py 读取，带兜底) ---
        pm_eye = getattr(config, "L2D_EYE_PARAMS", {})
        pm_offset = getattr(config, "L2D_OFFSET_PARAMS", ["Param", "Param2"])
        pm_expr = getattr(config, "L2D_EXPRESSION_PARAMS", ["Paramangry", "Parambroweyes"])

        # --- 2. 基础视角与视线同步 ---
        self.model.SetParameterValue(pm_eye.get("angle_x", "ParamAngleX"), self.cur_x * 30, 1.0)
        self.model.SetParameterValue(pm_eye.get("angle_y", "ParamAngleY"), self.cur_y * 30, 1.0)
        self.model.SetParameterValue(pm_eye.get("mouse_x", "ParamMouseX"), self.cur_x * 30, 1.0)
        self.model.SetParameterValue(pm_eye.get("mouse_y", "ParamMouseY"), self.cur_y * 30, 1.0)
        
        # --- 3. 团子/挂件位移同步 ---
        if len(pm_offset) >= 2:
            self.model.SetParameterValue(pm_offset[0], self.cur_x * 15, 1.0) # X 轴偏移
            self.model.SetParameterValue(pm_offset[1], self.cur_y * 15, 1.0) # Y 轴偏移

        # --- 4. 表情控制同步 ---
        for param_id in pm_expr:
            self.model.SetParameterValue(param_id, self.current_exp_val, 1.0)
        
        self.model.Update()
        self.model.Draw()

    def resizeGL(self, w, h):
        """ ✅ 核心修复：保持等比例缩放，防止孩子变扁 """
        if self.model:
            side = min(w, h) if min(w, h) > 0 else 1
            self.model.Resize(side, side)

    def closeEvent(self, event):
        if self.model:
            live2d.dispose()
        live2d.quit()
        super().closeEvent(event)