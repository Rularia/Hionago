import os, re, json, traceback
from openai import OpenAI
import config

class LLMService:
    def __init__(self):
        # 1. 加载配置
        self.settings = {}
        settings_path = os.path.join(config.RESOURCE_DIR, "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except: pass

        self.client = OpenAI(api_key=config.API_KEY, base_url=config.LLM_API_BASE)
        self.history_file = config.CHAT_HISTORY_PATH
        
        # 维持阿和表情
        self.last_nagomu_exp_val = 0.0 
        self.last_nagomu_tag = "normal"

    def _get_approximate_exp(self, char_id, raw_tag):
        """ 语义归类：根据角色获取对应的数字索引 """
        t = str(raw_tag).lower()
        # 修正：根据角色动态获取地图键名
        map_key = f"emotion_semantic_map_{char_id}"
        semantic_map = self.settings.get(map_key, {})
        
        for exp_val, keywords in semantic_map.items():
            if any(word in t for word in keywords):
                # 返回字符串形式的索引，如 "3.0"，方便后续查找文件名
                return str(exp_val)
            
        return "0.0" # 找不到时的默认索引

    def _get_char_id(self, item):
        """ 身份识别：保留日织/阿和逻辑，同时支持通用别名 """
        label = str(item.get("speaker", "")).strip()
        
        # 1. 优先查配置表（通用的逻辑）
        resolved = config.ALIAS_MAP.get(label)
        if resolved: return resolved
        
        # 2. 保留你的特定逻辑：日织/阿和关键词判定
        label_l = label.lower()
        if any(x in label_l for x in ["nagomu", "阿和", "和"]): return "Nagomu"
        if any(x in label_l for x in ["hiori", "日织", "日織"]): return "Hiori"

        # 3. 台词补全逻辑（通过对话内容互推身份）
        text = (str(item.get("ja", "")) + str(item.get("zh", ""))).lower()
        if any(n in text for n in ["阿和", "和さん", "名探偵", "nagomu"]): return "Hiori"
        if any(n in text for n in ["日织", "日織", "hiori"]): return "Nagomu"
        
        # 默认返回
        return "Hiori"

    def _clean_text(self, text, is_speech=True, alt_text=""):
        """
        is_speech: 是否为语音字段。
        - True: 必须删掉所有括号内容（防止 TTS 读出“括号笑声”），无论什么语言。
        - False: 保留括号内的动作描写（用于 UI 气泡显示）。
        """
        raw = str(text).strip()
        
        # 救急补全
        if (not raw or raw == "None" or raw == "") and "|" in str(alt_text):
            parts = str(alt_text).split("|")
            raw = parts[0] if is_speech else parts[-1]

        # 分离处理
        for sep in ['|', '｜']:
            if sep in raw:
                raw = raw.split(sep)[0] if is_speech else raw.split(sep)[-1]
        
        # 移除名字前缀
        raw = re.sub(r'^.*?[:：\s]+', '', raw, flags=re.IGNORECASE)

        if is_speech:
            # 无论什么语言，只要是语音字段，统一剔除中英文括号、日文括号及其内容
            raw = re.sub(r'[\(\uff08\[\u3010].*?[\)\uff09\]\u3011]', '', raw)
        else:
            # 中文显示字段：保留括号，只统一特定称呼（可选）
            raw = raw.replace("阿和先生", "阿和").replace("和先生", "阿和")
            
        return raw.strip()

###---------

    def _save_history(self, user_text, script_results):
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(f"\n[USER_INPUT]: {user_text}\n")
                for s in script_results:
                    f.write(f"{s['char']}|{s['emotion']}: {s['ja']}|{s['zh']}\n")
        except: pass

    def get_full_response(self, forced_char, user_text, mode_key="short", window_info=""):
        try:
            # 1. 基础配置准备
            modes = config.get_safe_modes()
            cfg = modes.get(mode_key, modes.get("short", {}))
            limit = cfg.get("context_limit", 20)
            
            # --- 修复：移除硬编码，直接使用 Setting 中的 desc ---
            mode_desc = cfg.get("desc", f"当前是 {mode_key} 模式，请合适地进行回复。")

            # 2. 核心拦截逻辑：判断是否进入“屏幕感知模式”
            is_perceive_mode = bool(window_info) and ("打个招呼" in user_text or not user_text)
            
            perceive_instruction = ""
            if is_perceive_mode:
                perceive_instruction = (
                    f"### [环境感知指令]\n"
                    f"你发现用户正在使用窗口：【{window_info}】。\n"
                    f"请以此开启话题，不要只说‘欢迎回来’。如果是编程工具就调侃代码，是网页就问在看什么，语气要符合人设。"
                )

            # 3. 读取历史记录（确保在 user_content 之前定义 history_str）
            history_str = ""
            if os.path.exists(self.history_file):
                try:
                    with open(self.history_file, "r", encoding="utf-8") as f:
                        history_str = "".join(f.readlines()[-limit:])
                except: pass

            # 4. 构造统一的 System Prompt
            system_prompt = f"""
{config.get_current_prompt()}

### [行为准则]
1. {perceive_instruction if is_perceive_mode else "当前是普通的日常对话，请正常回应。"}
2. 必须返回 JSON 数组，严禁包含任何 Markdown 标记。
3. 字段包含: "speaker", "emotion", "ja", "zh"。
4. "zh" 字段必须保留括号内的动作描写（例如："(轻笑)还在忙吗？"）。
5. {mode_desc}
"""
            # 5. 调试与发送
            print(f"DEBUG: 感知启动={is_perceive_mode} | 窗口='{window_info}'")
            user_content = f"【历史记录】:\n{history_str}\n\n【当前输入】: {user_text}"
            
            response = self.client.chat.completions.create(
                model=config.LLM_MODEL, 
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": user_content}
                ],
                temperature=0.8
            )
            
            raw = response.choices[0].message.content or ""
            print(f"📥 LLM 原始 JSON:\n{raw}")
            
            # 6. 解析逻辑（保持不变）
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if not match: return []
            data_list = json.loads(match.group(), strict=False)
            
            full_script = []
            for item in data_list:
                char_id = self._get_char_id(item)
                raw_tag = str(item.get("emotion", "normal")).lower()

                # 语义映射：如果映射表里没词，就会变 0.0
                exp_key = self._get_approximate_exp(char_id, raw_tag)
                
                links = self.settings.get("valid_asset_tags", {}).get("links", {})
                file_name = links.get(char_id, {}).get(exp_key, "")

            # 这里的 ja_clean 现在是“通用语种语音字段”
                # 只要你在 Prompt 里要求 'ja' 字段生成用户想要的语言即可
                ja_clean = self._clean_text(item.get("ja", ""), is_speech=True, alt_text=item.get("zh", ""))
                zh_clean = self._clean_text(item.get("zh", ""), is_speech=False, alt_text=item.get("ja", ""))

                # 2. 构造最终脚本
                full_script.append({
                    "char": char_id,  # 这里会通过你保留的识别逻辑区分日织/阿和
                    "emotion": raw_tag,
                    "exp": int(float(exp_key)),
                    "file_name": file_name, # 必须保留这个，否则 Live2D 无法切换动作文件
                    "ja": ja_clean,
                    "zh": zh_clean
                })
            
            self._save_history(user_text, full_script)
            return full_script
            
        except Exception as e:
            print(f"❌ 获取回复失败: {e}")
            traceback.print_exc()
            return []
