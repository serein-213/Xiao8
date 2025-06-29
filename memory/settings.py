import json
from langchain_openai import ChatOpenAI
from config import OPENROUTER_API_KEY, SETTING_PROPOSER_MODEL, SETTING_VERIFIER_MODEL, OPENROUTER_URL, SETTING_STORE, MASTER_NAME, NAME_MAPPING, lanlan_basic_config, master_basic_config
from config.prompts_sys import settings_extractor_prompt, settings_verifier_prompt


class ImportantSettingsManager:
    def __init__(self, settings_file=SETTING_STORE):
        self.settings_file = settings_file
        self.proposer = ChatOpenAI(model=SETTING_PROPOSER_MODEL, base_url=OPENROUTER_URL, api_key=OPENROUTER_API_KEY, temperature=0.5)
        self.verifier = ChatOpenAI(model=SETTING_VERIFIER_MODEL, base_url=OPENROUTER_URL, api_key=OPENROUTER_API_KEY, temperature=0.5)
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        for i in self.settings_file:
            try:
                with open(self.settings_file[i], 'r', encoding='utf-8') as f:
                    self.settings[i] = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self.settings[i] = {i: lanlan_basic_config[i], MASTER_NAME: master_basic_config}

    def save_settings(self, lanlan_name):
        with open(self.settings_file[lanlan_name], 'w', encoding='utf-8') as f:
            json.dump(self.settings[lanlan_name], f, indent=2, ensure_ascii=False)

    def detect_and_resolve_contradictions(self, old_settings, new_settings, lanlan_name):
        # 使用LLM检测矛盾并解决它们
        prompt = settings_verifier_prompt % (json.dumps(old_settings, ensure_ascii=False), json.dumps(new_settings, ensure_ascii=False))
        prompt = prompt.replace("{LANLAN_NAME}", lanlan_name)

        retries = 0
        while retries < 3:
            try:
                response = self.verifier.invoke(prompt)
                result = response.content
                if result.startswith("```"):
                    result = result .replace("```json", "").replace("```", "").strip()
            except Exception as e:
                print("Setting resolver query出错", e)
                retries += 1
                continue
            try:
                merged_settings = json.loads(result)
                return merged_settings
            except json.JSONDecodeError:
                # 如果解析失败，返回新设定
                retries += 1
                print("Setting resolver返回值解析失败。返回值：", response.content)
        return old_settings

    def extract_and_update_settings(self, messages, lanlan_name):
        # 从消息中提取新设定
        name_mapping = NAME_MAPPING.copy()
        name_mapping['ai'] = lanlan_name
        prompt = settings_extractor_prompt % ("\n".join([f"{name_mapping[msg.type]} | {"\n".join([i.get("text", "|" +i["type"]+ "|") for i in msg.content])}" for msg in messages]))
        prompt = prompt.replace('{LANLAN_NAME}', lanlan_name)
        retries = 0
        new_settings = ""
        while retries < 3:
            try:
                response = self.proposer.invoke(prompt)
            except Exception as e:
                print("Setting LLM query出错", e)
                retries += 1
                continue
            try:
                result = response.content
                if result.startswith("```"):
                    result = result .replace("```json", "").replace("```", "").strip()
                new_settings = json.loads(result)
            except json.JSONDecodeError:
                print("Setting LLM返回的设定JSON解析失败。返回值：", response.content)
                retries += 1
            break

        # 检测并解决矛盾
        if len(new_settings)>0:
            self.load_settings()
            self.settings[lanlan_name] = self.detect_and_resolve_contradictions(self.settings[lanlan_name], new_settings, lanlan_name)
            self.save_settings(lanlan_name)

    def get_settings(self, lanlan_name):
        self.load_settings()
        self.settings[lanlan_name][lanlan_name].update(lanlan_basic_config[lanlan_name])
        self.settings[lanlan_name][MASTER_NAME].update(master_basic_config)
        return self.settings[lanlan_name]