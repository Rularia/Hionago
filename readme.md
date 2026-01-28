* # 🎭 AI Desktop CP Theatre | AI 桌面 CP 剧场 

  [English Version](#english-version) | [简体中文说明](#简体中文说明)

  ---

  ## 🏮 简体中文说明

  本项目是一个通用型 AI 桌面互动剧场框架。不同于传统桌宠，它侧重于多角色之间的互动对戏，支持用户自定义形象、音色及对话逻辑。该项目旨在提供一个低门槛、可快速使用的桌面交互方案。

  ### 🌟 核心功能与特性
  * **零部署运行**：基于 SiliconFlow (硅基流动) API，无需本地部署大模型或配置高性能显卡。
  * **多角色联动**：支持双角色同台互动。系统可自动识别对话身份，并驱动 Live2D 或图片资产实时切换表情进行“对戏”。
  * **高度自定义**：
      * **视觉资产**：原生支持 Live2D 模型，并提供静态图片及 GIF 作为兜底显示。
      * **音色克隆**：内置 VoiceExpert 语音工具，支持通过 ASR 识别与语音上传实现自定义音色同步。
      * **UI 定制**：用户可自定义对话气泡样式、按钮及全局主题颜色（支持 Hex 颜色代码）。
  * **多样化展示模式**：除了常规对话气泡，内置独创的“贴吧体/论坛体”剧本模式，支持逐条显示长篇剧情，适合剧场创作者。
  * **情感语义引擎**：内置 16 个通用情感槽位的语义字典，确保 AI 表情切换与文本情感精准对齐。
  * **轻量环境感知**：具备屏幕感知能力，可读取当前活动窗口标题。AI 能根据用户当前的任务（如编程、看视频）进行实时互动吐槽。
  * **云端图库同步**：集成 Vika (维格表) API，支持画师建库共享，可在桌面上随机抽取展示画稿。

  ### 📺 视频教程 (Bilibili)
  * **项目演示：**
  * **配置教学：**[此处填入你的 BV 号链接]

  ### 🚀 快速上手 (EXE 便携版)
  1.  **下载路径**: [蓝奏云链接] (密码: `6666`) | [GitHub Releases]
  2.  **环境准备**: 运行前请确保安装 Visual C++ 2015-2022 运行库。
  3.  **路径规范**: 请务必解压至 **全英文路径** 运行，否则 Live2D 核心组件可能加载失败。
  4.  **项目状态**: 本项目目前为 Final Version (最终版)，逻辑已稳定脱敏。

  ---

  ## 🌎 English Version

  A universal AI Desktop Interaction Framework designed for multi-character synchronization and immersive storytelling.

  ### 🌟 Highlights
  * **Zero Deployment**: Powered by SiliconFlow API; no local GPU cluster required.
  * **Dual-Character Sync**: AI perceives identities and performs real-time expression changes based on context.
  * **High Customization**: Supports Live2D/GIFs/Images, custom voice cloning, and UI theme modifications.
  * **Unique Display**: Traditional chat bubbles plus a unique "Forum-style" Mode for long-form storytelling.
  * **Context Awareness**: Recognizes active window titles to initiate relevant conversations.
  * **Cloud Gallery**: Vika-based image gallery integration for artist groups to share artwork.

  ### 📺 Video Tutorials (Bilibili)

  * **Project Showcase:** [Link to your showcase video]
  * **Setup & Configuration:** [Link to your tutorial video]

  ### 🚀 Quick Start (Portable EXE)

  1. **Download:** [Lanzou Link] (Passcode: `6666`)
  2. **Prerequisites:** Ensure [Microsoft Visual C++ 2015-2022 Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) is installed.
  4. **Project Status:** This is the **Final Version**. The logic has been stabilized and sensitive information has been sanitized. No further major updates are planned.

  ---

  ## ⚙️ 源码运行  |  Running from Source(For Developers)

  ```bash
  pip install -r requirements.txt
  python main.py

## 📄 Credits

- **Development**: [Rularia]
- **Illustrator**: [鱼骨] (Special Thanks!)
- **Technology**: PySide6, Live2D SDK, SiliconFlow API.