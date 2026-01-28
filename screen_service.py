import win32gui
import win32process
import os

class ScreenService:
    def __init__(self):
        self.my_pid = os.getpid()

    def get_active_window_title(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return "桌面"

            _, foreground_pid = win32process.GetWindowThreadProcessId(hwnd)

            # 如果当前是自己，才进行穿透
            if foreground_pid == self.my_pid:
                curr_hwnd = hwnd
                # 限制搜索深度，防止死循环
                for _ in range(15): 
                    curr_hwnd = win32gui.GetWindow(curr_hwnd, 2) # GW_HWNDNEXT
                    if not curr_hwnd: break
                    
                    # 快速检查：必须可见
                    if not win32gui.IsWindowVisible(curr_hwnd):
                        continue
                        
                    # 获取类名通常比获取标题快，可以先过滤系统类
                    class_name = win32gui.GetClassName(curr_hwnd)
                    if class_name in ["IME", "MSCTFIME UI", "CompatWindowDesktopReplacement"]:
                        continue

                    title = win32gui.GetWindowText(curr_hwnd)
                    # 标题长度过滤，排除掉干扰项
                    if title and len(title) > 2 and title not in ["Program Manager", "任务栏"]:
                        return title
                return "桌面"
            else:
                title = win32gui.GetWindowText(hwnd)
                return title if title else "桌面"
        except Exception:
            return "神秘空间"

    # ... get_context_hint 保持不变 ...
    def get_context_hint(self, title):
        """
        基于窗口标题提供场景暗示
        """
        t = title.lower()
        
        # 排除掉 Python 解释器本身的标题干扰
        if "python" in t or "visual studio code" in t:
            return "用户似乎正在专注地编写代码或调试项目"

        # 创作与文档
        if any(x in t for x in ["word", "notion", "vnote", "obsidian", "wps", "excel", "book"]):
            return "用户正在记录重要文档或进行文字创作"
            
        # 娱乐与视频
        if any(x in t for x in ["bilibili", "youtube", "netflix", "potplayer"]):
            return "用户正在观看视频休息，气氛很轻松"
            
        # 浏览器
        if any(x in t for x in ["edge", "chrome", "firefox", "browser"]):
            return "用户正在浏览网页，寻找资料或冲浪"
            
        # 游戏
        if any(x in t for x in ["steam", "genshin", "starrail", "honkai", "game"]):
            return "检测到游戏运行中，用户进入了游戏时光"
            
        return "用户正在操作电脑，处理某些事务"

if __name__ == "__main__":
    # 测试代码
    service = ScreenService()
    import time
    print("3秒后开始捕获，请切换到其他窗口...")
    time.sleep(3)
    current = service.get_active_window_title()
    print(f"当前窗口: {current}")
    print(f"场景暗示: {service.get_context_hint(current)}")