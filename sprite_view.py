# sprite_view.py
import os
import time
import threading

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QMovie
from PySide6.QtCore import Qt, Signal, QThread, QTimer

import config


class SpriteView(QLabel):
    # 外部任何线程都用这个发请求，内部保证在 GUI 线程切换
    request_set_image = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)

        self.current_movie: QMovie | None = None

        # debug 节流：避免每一帧都刷屏
        self._last_frame_log_t = 0.0
        self._frame_log_interval = 0.6  # 秒

        # 关键：用队列连接，确保 set_image_by_name 总在 GUI 线程执行
        self.request_set_image.connect(self.set_image_by_name, Qt.QueuedConnection)

        self._dbg("SpriteView init done.")

    # ---------- debug ----------
    def _dbg(self, msg: str):
        # 你可以按需关掉
        tid = threading.get_ident()
        qt_tid = int(QThread.currentThreadId())
        gui_thread = (QThread.currentThread() == self.thread())
        print(f"[SpriteView][gui={gui_thread} py_tid={tid} qt_tid={qt_tid}] {msg}")

    # ---------- Qt events ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 让 GIF 在窗口改变大小后也能继续正确缩放
        if self.current_movie and not self.size().isEmpty():
            self.current_movie.setScaledSize(self.size())
            self._dbg(f"resizeEvent -> scaledSize={self.size().width()}x{self.size().height()}")

    # ---------- core ----------
    def set_image_by_name(self, file_name: str):
        """彻底清理并切换资源（保证在 GUI 线程执行）"""
        if not file_name:
            self._dbg("set_image_by_name called with empty file_name -> return")
            return

        self._dbg(f"set_image_by_name -> {file_name}")

        # 1) 清理旧 movie
        if self.current_movie:
            try:
                self._dbg(
                    f"stop old movie | state={self.current_movie.state()} "
                    f"frame={self.current_movie.currentFrameNumber()}"
                )
                self.current_movie.stop()
                self.current_movie.deleteLater()
            except Exception as e:
                self._dbg(f"stop old movie exception: {e}")
            self.current_movie = None

        # 2) 解除绑定 & 清空显示（建议用 setPixmap(QPixmap()) 比 clear 更“强”）
        self.setMovie(None)
        self.setPixmap(QPixmap())

        # 3) 路径
        path = os.path.join(config.SPRITE_DIR, file_name).replace("\\", "/")
        if not os.path.exists(path):
            self._dbg(f"⚠️ file not found: {path}")
            return

        # 4) 分支渲染
        if path.lower().endswith(".gif"):
            movie = QMovie(path, parent=self)
            movie.setCacheMode(QMovie.CacheAll)

            if not self.size().isEmpty():
                movie.setScaledSize(self.size())

            # 绑定 debug 信号
            self._attach_movie_debug(movie, file_name)

            self.setMovie(movie)
            self.current_movie = movie

            # 有些系统切换时不 jumpToFrame 会停在旧帧错觉
            ok = movie.jumpToFrame(0)
            self._dbg(f"GIF loaded: valid={movie.isValid()} jumpToFrame0={ok}")

            movie.start()
            # 再次确认状态
            self._dbg(f"GIF start -> state={movie.state()} frame={movie.currentFrameNumber()}")

        else:
            pix = QPixmap(path)
            if pix.isNull():
                self._dbg(f"⚠️ pixmap isNull: {path}")
                return

            scaled = pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
            self._dbg(f"Static shown: {file_name} | size={scaled.width()}x{scaled.height()}")

    def _attach_movie_debug(self, movie: QMovie, name: str):
        # 状态变化
        def on_state_changed(state):
            self._dbg(f"[movie:{name}] stateChanged -> {state}")

        # 帧变化（节流）
        def on_frame_changed(frame_no: int):
            now = time.time()
            if now - self._last_frame_log_t >= self._frame_log_interval:
                self._last_frame_log_t = now
                self._dbg(f"[movie:{name}] frameChanged -> {frame_no}")

        # 播放结束（如果不是循环）
        def on_finished():
            self._dbg(f"[movie:{name}] finished() fired")

        movie.stateChanged.connect(on_state_changed)
        movie.frameChanged.connect(on_frame_changed)
        movie.finished.connect(on_finished)
