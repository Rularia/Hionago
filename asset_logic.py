import os
import json
import config

class AssetLogic:
    # 丰富版情绪字典 (作为地基)
    DEFAULT_MAP = {
        "0.0": ["平淡", "日常", "冷静", "思考", "normal", "calm"],
        "1.0": ["温柔", "微笑", "注视", "宠溺", "smile", "happy"],
        "2.0": ["戏谑", "腹黑", "调侃", "掌控", "teasing", "s-mode"],
        "3.0": ["优雅", "深沉", "执着", "占有", "elegant", "obsessive"],
        "4.0": ["害羞", "脸红", "无措", "尴尬", "blush", "shy"],
        "5.0": ["受惊", "震撼", "吓一跳", "呆滞", "shock", "surprised"],
        "6.0": ["委屈", "难过", "湿漉漉的眼神", "失落", "sad", "pout"],
        "7.0": ["生气", "威压", "严肃", "低沉", "angry", "serious"],
        "8.0": ["依赖", "求助", "抓住衣角", "不安", "dependent", "help"],
        "9.0": ["受难", "虚弱", "病娇", "喘息", "weak", "hurt"],
        "10.0": ["认真", "侦探模式", "锐利", "推理", "detective", "focus"],
        "11.0": ["困惑", "不解", "歪头", "吐槽", "confused", "question"],
        "12.0": ["得逞", "坏笑", "愉悦", "狂气", "smirk", "laugh"],
        "13.0": ["疲惫", "困倦", "无奈", "叹气", "tired", "sigh"],
        "14.0": ["期待", "闪亮", "好奇", "兴奋", "excited", "sparkle"],
        "15.0": ["空洞", "绝望", "崩坏", "失神", "broken", "empty"]
    }

    @staticmethod
    def _get_merged_map():
        """ 智能合并：DEFAULT_MAP + supplement.json """
        # 1. 以代码中的 DEFAULT_MAP 为基础（深拷贝防止污染）
        final_map = {k: list(v) for k, v in AssetLogic.DEFAULT_MAP.items()}
        
        # 2. 尝试读取外部补充包 (假设路径在 assets/supplement.json)
        # 你可以在 config.py 里定义 SUPPLEMENT_PATH = "assets/supplement.json"
        supp_path = getattr(config, 'SUPPLEMENT_PATH', os.path.join("assets", "supplement.json"))
        
        if os.path.exists(supp_path):
            try:
                with open(supp_path, "r", encoding="utf-8") as f:
                    supp_data = json.load(f)
                
                for code, words in supp_data.items():
                    if code in final_map:
                        # 如果已存在，合并列表并去重
                        updated_words = list(set(final_map[code]) | set(words))
                        final_map[code] = updated_words
                    else:
                        # 如果是新表情代码，直接添加
                        final_map[code] = words
            except Exception as e:
                print(f"读取补充词库失败: {e}")
        
        return final_map

    @staticmethod
    def resolve_output(llm_char_name, llm_tag):
        try:
            with open(config.JSON_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except: return {"char_id": "Nagomu", "exp_code": "0.0", "file": None}

        char_id = "Nagomu"
        # 修正：ALIAS_MAP 逻辑
        alias_map = getattr(config, 'ALIAS_MAP', {})
        for official, aliases in alias_map.items():
            alias_list = [a.strip() for a in str(aliases).split(",")]
            if llm_char_name in alias_list or llm_char_name == official:
                char_id = official
                break

        # --- 核心修改点：获取合并后的词库 ---
        # 优先看 settings.json 是否有覆盖，没有则用我们合并后的“超级词库”
        dict_key = f"emotion_semantic_map_{char_id}"
        merged_base = AssetLogic._get_merged_map()
        semantic_map = settings.get(dict_key, settings.get("emotion_semantic_map", merged_base))
        
        target_code = "0.0"
        tag_l = str(llm_tag).lower().strip()
        
        # 遍历检索
        for code, keywords in semantic_map.items():
            if tag_l in [str(k).lower().strip() for k in keywords]:
                target_code = code
                break
        
        # 资源匹配逻辑保持不变
        is_static = config.USE_STATIC_IMAGE
        tag_section = "links" if is_static else "l2d_links"
        
        links = settings.get("valid_asset_tags", {}).get(tag_section, {}).get(char_id, {})
        file_name = links.get(target_code) or links.get("0.0")

        return {
            "char_id": char_id,
            "exp_code": target_code,
            "file": file_name,
            "is_static": is_static
        }

    # ... get_valid_assets 等其他方法保持不变 ...

    @staticmethod
    def get_valid_assets():
        """ 逻辑层同步：确保 JSON 里的 l2d_links 也是精准过滤后的 """
        settings_path = config.JSON_PATH
        if not os.path.exists(settings_path): return {}

        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # 1. 扫描 Live2D (执行跟 UI 完全一样的严格匹配)
        l2d_links = {"Hiori": {}, "Nagomu": {}}
        l2d_dir = os.path.dirname(config.MODEL_PATH) 
        if os.path.exists(l2d_dir):
            # --- 严格过滤：必须 live2d_expression 开头，且 .exp3.json 结尾 ---
            all_files = os.listdir(l2d_dir)
            filtered_files = [
                f for f in all_files 
                if f.lower().startswith('live2d_expression') and f.lower().endswith('.exp3.json')
            ]
            files = sorted(filtered_files)
            
            counters = {"Hiori": 0, "Nagomu": 0}
            for f in files:
                char = "Hiori" if "hiori" in f.lower() else "Nagomu"
                code = f"{float(counters[char]):.1f}"
                l2d_links[char][code] = f
                counters[char] += 1

        # 2. 扫描静态图并写回 (保持原有逻辑)

        static_links = {"Hiori": {}, "Nagomu": {}}
        if os.path.exists(config.SPRITE_DIR):
            files = sorted([f for f in os.listdir(config.SPRITE_DIR) 
                           if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
            counters = {"Hiori": 0, "Nagomu": 0}
            for f in files:
                char = "Hiori" if "hiori" in f.lower() else "Nagomu"
                code = f"{float(counters[char]):.1f}"
                static_links[char][code] = f
                counters[char] += 1

        settings["valid_asset_tags"] = {
            "active_mode": "static" if config.USE_STATIC_IMAGE else "l2d",
            "links": static_links,
            "l2d_links": l2d_links
        }

        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return settings["valid_asset_tags"]
