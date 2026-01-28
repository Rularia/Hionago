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
# config.py
import os, json, requests, sys

# 1. 确定根目录
if getattr(sys, 'frozen', False):
    # 打包后的 main.exe 所在目录
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 源码运行所在的目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 统一转为标准路径格式，防止 Windows 路径符干扰
BASE_DIR = BASE_DIR.replace("\\", "/")

# 2. 定义文件夹名 (请确保这里与你硬盘上的文件夹名字一模一样)
RESOURCE_FOLDER_NAME = "Resource"
SPRITE_FOLDER_NAME   = "Sprites"
MODEL_FOLDER_NAME    = "Model" # 如果你硬盘上叫 hionago_model，请改成 hionago_model

# 3. 组合路径
RESOURCE_DIR = os.path.join(BASE_DIR, RESOURCE_FOLDER_NAME).replace("\\", "/")
SPRITE_DIR   = os.path.join(BASE_DIR, SPRITE_FOLDER_NAME).replace("\\", "/")
MODEL_DIR    = os.path.join(BASE_DIR, MODEL_FOLDER_NAME).replace("\\", "/")

# 4. 具体文件路径
# 注意：cat.model3.json 必须在 MODEL_DIR 文件夹内
MODEL_PATH = os.path.join(MODEL_DIR, "cat.model3.json").replace("\\", "/")
JSON_PATH  = os.path.join(RESOURCE_DIR, "settings.json").replace("\\", "/")
# ... 其他路径同理

# 5. 状态检查 (非常重要)
# 如果模型文件找不到，USE_STATIC_IMAGE 会变成 True
USE_STATIC_IMAGE = not os.path.exists(MODEL_PATH)

# ================= 调试辅助 (打包后如果读不到，可以生成一个 debug.txt 看看) =================
# 你可以暂时取消下面代码的注释，运行一次 EXE，它会在旁边生成一个路径清单
# with open(os.path.join(BASE_DIR, "path_debug.txt"), "w", encoding="utf-8") as f:
#     f.write(f"BASE_DIR: {BASE_DIR}\n")
#     f.write(f"MODEL_PATH: {MODEL_PATH}\n")
#     f.write(f"EXISTS: {os.path.exists(MODEL_PATH)}\n")# config.py

# --- 具体文件路径 ---

API_JSON         = os.path.join(RESOURCE_DIR, "api_credentials.json").replace("\\", "/")
DEFAULT_JSON     = os.path.join(RESOURCE_DIR, "default_settings.json").replace("\\", "/")
ASSETS_DIR       = os.path.join(RESOURCE_DIR, "Assets").replace("\\", "/")
APP_ICON_PATH    = os.path.join(ASSETS_DIR, "hionago.ico").replace("\\", "/")
THINKING_GIF_PATH = os.path.join(ASSETS_DIR, "thinking.gif").replace("\\", "/")
SUPPLEMENT_PATH = os.path.join(ASSETS_DIR, "supplement.json").replace("\\", "/")


# 运行产物 (也在 EXE 同级)
VOICE_DIR         = os.path.join(RESOURCE_DIR, "output_audio").replace("\\", "/")
CHAT_HISTORY_PATH = os.path.join(RESOURCE_DIR, "chat_history.txt").replace("\\", "/")
FAVORITES_PATH    = os.path.join(RESOURCE_DIR, "favorites.txt").replace("\\", "/")

# 检查模型是否存在 (用于调试)
USE_STATIC_IMAGE = not os.path.exists(MODEL_PATH)
if USE_STATIC_IMAGE:
    print(f"DEBUG: 找不到模型，尝试路径: {MODEL_PATH}")
    
# ================= 2. 天气抓取逻辑 (腾讯接口) =================
def get_weather_data(city_name="北京"):
    try:
        url = "https://wis.qq.com/weather/common"
        params = {"source": "pc", "weather_type": "observe", "province": city_name, "city": city_name}
        resp = requests.get(url, params=params, timeout=1.2)
        if resp.status_code == 200:
            data = resp.json()
            if data["status"] == 200:
                obs = data["data"]["observe"]
                weather, temp = obs["weather"], obs["degree"]
                icon = "☀️" if "晴" in weather else "🌧️" if "雨" in weather else "☁️"
                return f"{icon} {weather} {temp}°C"
    except: pass
    return "☁️ 天气更新中"

# ================= 3. 加载逻辑 (双重结构兼容版) =================
def load_all_configs():
    def safe_load(path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}

    api_data = safe_load(API_JSON)
    def_data = safe_load(DEFAULT_JSON)
    cur_data = safe_load(JSON_PATH)

    # 兼容你的 settings.json 里的 character_profiles 嵌套结构
    c_prof = cur_data.get("character_profiles", {})
    d_prof = def_data.get("character_profiles", {})

    return {
        "api_key": api_data.get("api_key", ""),
        "vika_token": api_data.get("vika_token", ""),
        "vika_datasheet_id": api_data.get("vika_datasheet_id", ""),
        "llm_base_url": api_data.get("llm_base_url") or "https://api.siliconflow.cn/v1",
        "llm_model": api_data.get("llm_model") or cur_data.get("llm_model") or "deepseek-ai/DeepSeek-V3",
        "tts_base_url": api_data.get("tts_base_url") or "https://api.siliconflow.cn/v1",
        "tts_model": api_data.get("tts_model") or "FunAudioLLM/CosyVoice2-0.5B",
        "voice_settings": api_data.get("voice_settings", {}),
        "city": cur_data.get("city") or def_data.get("city", "北京"),
        "prompt_template": cur_data.get("prompt_template") or def_data.get("prompt_template", ""),
        "char_name_hiori": cur_data.get("char_name_hiori") or def_data.get("char_name_hiori", "Hiori"),
        "char_name_nagomu": cur_data.get("char_name_nagomu") or def_data.get("char_name_nagomu", "Nagomu"),
        "char_alias_hiori": cur_data.get("char_alias_hiori") or def_data.get("char_alias_hiori", ""),
        "char_alias_nagomu": cur_data.get("char_alias_nagomu") or def_data.get("char_alias_nagomu", ""),
        # 读取人设：平面和嵌套都试一遍
        "hiori_info": cur_data.get("hiori_info") or c_prof.get("Hiori") or d_prof.get("Hiori", ""),
        "nagomu_info": cur_data.get("nagomu_info") or c_prof.get("Nagomu") or d_prof.get("Nagomu", ""),
        "color_hiori": cur_data.get("color_hiori") or "#1B2647",
        "color_nagomu": cur_data.get("color_nagomu") or "#5D4037",
        "dialogue_modes": cur_data.get("dialogue_modes") or def_data.get("dialogue_modes") or {},
        "name_pronunciation_map": cur_data.get("name_pronunciation_map") or def_data.get("name_pronunciation_map", {}),
        "expression_map": cur_data.get("expression_map") or def_data.get("expression_map", {})
    }

_c = load_all_configs()

# ================= 4. 全量导出变量 (对齐 Settings.py 的所有需求) =================
API_KEY = _c["api_key"]
VIKA_TOKEN = _c["vika_token"]
VIKA_ID = _c["vika_datasheet_id"]
LLM_MODEL = _c["llm_model"]
VOICE_MAP = _c["voice_settings"]
LLM_API_BASE = _c["llm_base_url"]
TTS_API_BASE = _c["tts_base_url"]
TTS_MODEL = _c["tts_model"]
COLOR_HIORI = _c["color_hiori"]
COLOR_NAGOMU = _c["color_nagomu"]
CITY = _c["city"]
HIORI_INFO = _c["hiori_info"]
NAGOMU_INFO = _c["nagomu_info"]
WEATHER_NOW = "☁️ 正在同步" 
CHAR_NAME_HIORI = _c["char_name_hiori"]
CHAR_NAME_NAGOMU = _c["char_name_nagomu"]
CHAR_ALIAS_HIORI = _c["char_alias_hiori"]
CHAR_ALIAS_NAGOMU = _c["char_alias_nagomu"]
NAME_PRONUNCIATION_MAP = _c["name_pronunciation_map"]
EXPRESSION_MAP = _c["expression_map"]
DIALOGUE_MODES = _c["dialogue_modes"]
CURRENT_MODE = "short" 
USE_STATIC_IMAGE = not os.path.exists(MODEL_PATH)

def build_alias_map():
    m = {CHAR_NAME_HIORI: "Hiori", CHAR_NAME_NAGOMU: "Nagomu"}
    for a in str(CHAR_ALIAS_HIORI).replace("，", ",").split(","):
        if a.strip(): m[a.strip()] = "Hiori"
    for a in str(CHAR_ALIAS_NAGOMU).replace("，", ",").split(","):
        if a.strip(): m[a.strip()] = "Nagomu"
    return m

ALIAS_MAP = build_alias_map()
def get_char_by_name(text):
    for a, cid in ALIAS_MAP.items():
        if a in text: return cid
    return None
def get_safe_modes(): return DIALOGUE_MODES

# ================= 5. Prompt 生成 (核心强制逻辑) =================
def get_current_prompt():
    global WEATHER_NOW
    if "同步" in WEATHER_NOW: WEATHER_NOW = get_weather_data(CITY)
    # 通过硬编码指令压制“先生”后缀
    STRICT_RULE = "\n### 翻译铁律: 中文回复中，“一柳和”必须称呼为“阿和”，禁止带任何“先生”后缀。日语「和さん」一律翻译为「阿和」。\n"
    full = _c["prompt_template"].replace("{HIORI_INFO}", HIORI_INFO).replace("{NAGOMU_INFO}", NAGOMU_INFO)
    return STRICT_RULE + f"\n[环境: {CITY} {WEATHER_NOW}]\n" + full
