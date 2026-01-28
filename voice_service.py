# voice_service.py
import os, re, pygame, hashlib
from openai import OpenAI
import config 

class VoiceService:
    def __init__(self):
        # --- 新增：像 LLMService 一样加载最新的本地设置 ---
        self.settings = {}
        settings_path = os.path.join(config.RESOURCE_DIR, "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except: pass
        # ----------------------------------------------
        self.api_url = getattr(config, "TTS_API_URL", "https://api.siliconflow.cn/v1")
        self.client = OpenAI(api_key=config.API_KEY, base_url=self.api_url)
        self.tts_model = getattr(config, "TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B")
        
        try: pygame.mixer.init()
        except: print("音频初始化失败")

# voice_service.py 

    def clean_japanese_for_tts(self, text: str) -> str:
        # 核心修复：确保从最新的 config 加载映射
        import config
        name_map = getattr(config, "NAME_PRONUNCIATION_MAP", {})
        
        t = text
        # 遍历字典进行替换，例如 {"日织": "ひおり"}
        for raw, pron in name_map.items():
            t = t.replace(raw, pron)
            
        # 移除所有括号及其内容
        t = re.sub(r'[\(\uff08].*?[\)\uff09]', '', t)
        # 仅保留日语有效字符，防止 TTS 报错
        return "".join(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFFー、。！？]', t)).strip("、。 ")
    
    def get_file_path(self, char_name, text):
        """ 统一的路径生成逻辑，供本项目所有模块调用 """
        ja_clean = self.clean_japanese_for_tts(text)
        md5_name = hashlib.md5(f"{char_name}_{ja_clean}".encode("utf-8")).hexdigest()
        # 统一使用 v_ 前缀
        return os.path.join(config.VOICE_DIR, f"v_{md5_name}.mp3")

    def speak(self, char_name, emotion, text):
        """ 合成并播放语音 """
        # 2. 这里改用 self.settings 读取，确保拦截生效
        if not self.settings.get("enable_voice", True):
            return
        # ------------------------------------------
        try:
            if not os.path.exists(config.VOICE_DIR): os.makedirs(config.VOICE_DIR)
            ja_clean = self.clean_japanese_for_tts(text)
            if not ja_clean: return
            
            # 使用统一的路径获取函数
            path = self.get_file_path(char_name, text)

            if os.path.exists(path): 
                return self._play_audio(path)

            # 获取情绪对应的 voice_id
            char_v = config.VOICE_MAP.get(char_name, {})
            # 如果找不到指定情绪（如 dark），则尝试使用默认（如 serene 或第一个可用音色）
            voice_id = char_v.get(emotion) or next(iter(char_v.values()), None)

            with self.client.audio.speech.with_streaming_response.create(
                model=self.tts_model,
                voice=voice_id, 
                input="、、、 " + ja_clean, 
                response_format="mp3",
                extra_body={"temperature": 0.0001, "top_p": 0.01}
            ) as res:
                res.stream_to_file(path)
            self._play_audio(path)
        except Exception as e: 
            print(f"语音合成失败: {e}")

    def _play_audio(self, path):
        if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()