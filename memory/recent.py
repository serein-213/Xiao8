from datetime import datetime
from config import RECENT_LOG, SUMMARY_MODEL, OPENROUTER_API_KEY, OPENROUTER_URL, NAME_MAPPING
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, messages_to_dict, messages_from_dict
import json
import os

from config.prompts_sys import recent_history_manager_prompt, detailed_recent_history_manager_prompt, further_summarize_prompt

class CompressedRecentHistoryManager:
    def __init__(self, max_history_length=10):
        
        self.llm = ChatOpenAI(model=SUMMARY_MODEL, base_url=OPENROUTER_URL, api_key=OPENROUTER_API_KEY, temperature=0.4)
        self.max_history_length = max_history_length
        self.log_file_path = RECENT_LOG
        self.user_histories = {}
        for ln in self.log_file_path:
            if os.path.exists(self.log_file_path[ln]):
                with open(self.log_file_path[ln], encoding='utf-8') as f:
                    self.user_histories[ln] = messages_from_dict(json.load(f))
            else:
                self.user_histories[ln] = []


    def update_history(self, new_messages, lanlan_name, detailed=False):
        if os.path.exists(self.log_file_path[lanlan_name]):
            with open(self.log_file_path[lanlan_name], encoding='utf-8') as f:
                self.user_histories[lanlan_name] = messages_from_dict(json.load(f))

        try:
            self.user_histories[lanlan_name].extend(new_messages)

            if len(self.user_histories[lanlan_name]) > self.max_history_length:
                # 压缩旧消息
                to_compress = self.user_histories[lanlan_name][:-self.max_history_length+1]
                compressed = [self.compress_history(to_compress, lanlan_name, detailed)[0]]

                # 只保留最近的max_history_length条消息
                self.user_histories[lanlan_name] = compressed + self.user_histories[lanlan_name][-self.max_history_length+1:]
        except Exception as e:
            print("Error when updating history: ", e)
            import traceback
            traceback.print_exc()

        with open(self.log_file_path[lanlan_name], "w", encoding='utf-8') as f:
            json.dump(messages_to_dict(self.user_histories[lanlan_name]), f, indent=2, ensure_ascii=False)


    # detailed: 保留尽可能多的细节
    def compress_history(self, messages, lanlan_name, detailed=False):
        # 使用LLM总结和压缩消息
        name_mapping = NAME_MAPPING.copy()
        name_mapping['ai'] = lanlan_name
        messages_text = "\n".join([f"{name_mapping[msg.type]} | {"\n".join([(i.get("text", "|" +i["type"]+ "|") if isinstance(i, dict) else str(i)) for i in msg.content]) if type(msg.content)!=str else f"{name_mapping[msg.type]} | {msg.content}"}" for msg in messages])
        if not detailed:
            prompt = recent_history_manager_prompt % messages_text
        else:
            prompt = detailed_recent_history_manager_prompt % messages_text

        retries = 0
        while retries < 3:
            try:
                # 尝试将响应内容解析为JSON
                response_content = self.llm.invoke(prompt).content
                if response_content.startswith("```"):
                    response_content = response_content.replace('```json','').replace('```', '')
                summary_json = json.loads(response_content)
                # 从JSON字典中提取对话摘要，假设摘要存储在名为'key'的键下
                if '对话摘要' in summary_json:
                    print(f"💗摘要结果：{summary_json['对话摘要']}")
                    summary = summary_json['对话摘要']
                    if len(summary) > 500:
                        summary = self.further_compress(summary)
                        if summary is None:
                            continue
                    return SystemMessage(content=f"先前对话的备忘录: {summary}"), summary_json['对话摘要']
                else:
                    print('💥 摘要failed: ', response_content)
                    retries += 1
            except Exception as e:
                print('摘要模型失败：', e)
                # 如果解析失败，重试
                retries += 1
        # 如果所有重试都失败，返回None
        return SystemMessage(content=f"先前对话的备忘录: 无。"), ""

    def further_compress(self, initial_summary):
        retries = 0
        while retries < 3:
            try:
                # 尝试将响应内容解析为JSON
                response_content = self.llm.invoke(further_summarize_prompt % initial_summary).content
                if response_content.startswith("```"):
                    response_content = response_content.replace('```json', '').replace('```', '')
                summary_json = json.loads(response_content)
                # 从JSON字典中提取对话摘要，假设摘要存储在名为'key'的键下
                if '对话摘要' in summary_json:
                    print(f"💗第二轮摘要结果：{summary_json['对话摘要']}")
                    return summary_json['对话摘要']
                else:
                    print('💥 第二轮摘要failed: ', response_content)
                    retries += 1
            except Exception as e:
                print('摘要模型失败：', e)
                retries += 1
        return None

    def get_recent_history(self, lanlan_name):
        if os.path.exists(self.log_file_path[lanlan_name]):
            with open(self.log_file_path[lanlan_name], encoding='utf-8') as f:
                self.user_histories[lanlan_name] = messages_from_dict(json.load(f))
        return self.user_histories[lanlan_name]

    def clear_history(self, lanlan_name):
        """
        清除用户的聊天历史
        """
        self.user_histories[lanlan_name] = []
