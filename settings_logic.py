# settings_logic.py
import json, os, requests, config

class SettingsLogic:
    def __init__(self):
        self.api_json = config.API_JSON
        self.settings_json = config.JSON_PATH
        self.raw_voice_dir = os.path.join(config.RESOURCE_DIR, "rawvoice")

    def scan_l2d_params(self):
        """解析 demomodel.cdi3.json 获取完整参数 ID 和中文名"""
        params = []
        model3_file = config.MODEL_PATH
        model_dir = os.path.dirname(model3_file)
        try:
            with open(model3_file, 'r', encoding='utf-8-sig') as f:
                model3_data = json.load(f)
                cdi_rel = model3_data.get("FileReferences", {}).get("DisplayInfo")
            if cdi_rel:
                cdi_path = os.path.join(model_dir, cdi_rel)
                with open(cdi_path, 'r', encoding='utf-8-sig') as f:
                    cdi_data = json.load(f)
                    for p in cdi_data.get("Parameters", []):
                        params.append({"id": p.get("Id"), "name": p.get("Name")})
        except: pass
        return params

    def scan_l2d_expressions(self):
        """解析 cat.model3.json 获取表情文件列表"""
        exps = []
        try:
            with open(config.MODEL_PATH, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                expressions = data.get("FileReferences", {}).get("Expressions", [])
                for e in expressions:
                    exps.append({"file": e.get("File")})
        except: pass
        return exps

    def batch_sync_voices(self, tts_url, tts_key, tts_model, tasks):
        """批量同步音色"""
        results = {}
        headers = {"Authorization": f"Bearer {tts_key}"}
        for task in tasks:
            path = os.path.join(self.raw_voice_dir, task['file'])
            if not os.path.exists(path): continue
            try:
                with open(path, "rb") as f:
                    resp = requests.post(f"{tts_url}/uploads/audio/voice", 
                                         headers=headers, files={"file": f}, 
                                         data={"model": tts_model, "customName": f"{task['char']}_{task['emo_key']}"})
                    if resp.status_code == 200:
                        uri = resp.json().get("uri")
                        if task['char'] not in results: results[task['char']] = {}
                        results[task['char']][task['emo_key']] = uri
            except: continue
        return results

    def vika_upload_logic(self, file_path):
        """Vika 图片上传"""
        api_data, _ = self.load_all_data()
        token = api_data.get("vika_token")
        ds_id = api_data.get("vika_datasheet_id")
        if not (token and ds_id): return
        try:
            base_url = f"https://api.vika.cn/fusion/v1/datasheets/{ds_id}"
            headers = {"Authorization": f"Bearer {token}"}
            with open(file_path, 'rb') as f:
                resp = requests.post(f"{base_url}/attachments", headers=headers, files={'file': f})
                att_data = resp.json().get('data')
            requests.post(f"{base_url}/records", headers=headers, json={"records": [{"fields": {"附件": [att_data]}}]})
        except: pass

    def load_all_data(self):
        api_data, cur_data = {}, {}
        if os.path.exists(self.api_json):
            with open(self.api_json, 'r', encoding='utf-8') as f: api_data = json.load(f)
        if os.path.exists(self.settings_json):
            with open(self.settings_json, 'r', encoding='utf-8') as f: cur_data = json.load(f)
        return api_data, cur_data

# settings_logic.py 中的 save_all_configs

    def save_all_configs(self, api_bundle, script_bundle, mode_bundle, l2d_bundle, exp_bundle, voice_map):
        try:
            with open(self.api_json, 'w', encoding='utf-8') as f:
                json.dump({**api_bundle, "voice_settings": voice_map}, f, indent=4)
            
            with open(self.settings_json, 'w', encoding='utf-8') as f:
                json.dump({
                    **script_bundle, 
                    "dialogue_modes": mode_bundle, 
                    "l2d_params": l2d_bundle, 
                    "expression_map": exp_bundle # 统一存储
                }, f, ensure_ascii=False, indent=4)
            return True, "配置保存成功"
        except Exception as e: return False, str(e)
        
        
    def upload_to_siliconflow(self, file_path, custom_name, api_key):
        """
        专门针对硅基流动的 CosyVoice 上传逻辑
        """
        url = "https://api.siliconflow.cn/v1/uploads/audio/voice"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # 根据硅基文档，通常需要 model, customName 以及对应的文本内容
        data = {
            "model": "FunAudioLLM/CosyVoice2-0.5B", 
            "customName": custom_name,
            "text": "Check voice consistency" # 这里的文本是参考文本，可根据需要修改
        }
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                
            if resp.status_code == 200:
                # 返回的是类似 {"uri": "sf:voice:xxx"}
                return resp.json().get("uri")
            else:
                print(f"上传失败: {resp.text}")
                return None
        except Exception as e:
            print(f"上传异常: {e}")
            return None

    def get_raw_voices(self):
        if not os.path.exists(self.raw_voice_dir): os.makedirs(self.raw_voice_dir)
        return [f for f in os.listdir(self.raw_voice_dir) if f.endswith(('.mp3', '.wav'))]