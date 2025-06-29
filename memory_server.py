from memory import CompressedRecentHistoryManager, SemanticMemory, ImportantSettingsManager, TimeIndexedMemory
from fastapi import FastAPI
import json
import uvicorn
from langchain_core.messages import convert_to_messages
from uuid import uuid4
from config import MASTER_NAME, MEMORY_SERVER_PORT
from pydantic import BaseModel
from config import NAME_MAPPING
import re

class HistoryRequest(BaseModel):
    input_history: str

app = FastAPI()

# 初始化组件
recent_history_manager = CompressedRecentHistoryManager()
semantic_manager = SemanticMemory(recent_history_manager)
settings_manager = ImportantSettingsManager()
time_manager = TimeIndexedMemory(recent_history_manager)


@app.post("/process/{lanlan_name}")
def process_conversation(request: HistoryRequest, lanlan_name: str):
    try:
        uid = str(uuid4())
        input_history = convert_to_messages(json.loads(request.input_history))
        recent_history_manager.update_history(input_history, lanlan_name)
        """
        下面屏蔽了两个模块，因为这两个模块需要消耗token，但当前版本实用性近乎于0。尤其是，Qwen与GPT等旗舰模型相比性能差距过大。
        """
        # settings_manager.extract_and_update_settings(input_history, lanlan_name)
        # semantic_manager.store_conversation(uid, input_history, lanlan_name)
        time_manager.store_conversation(uid, input_history, lanlan_name)
        return {"status": "processed"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.post("/renew/{lanlan_name}")
def process_conversation_for_renew(request: HistoryRequest, lanlan_name: str):
    try:
        uid = str(uuid4())
        input_history = convert_to_messages(json.loads(request.input_history))
        recent_history_manager.update_history(input_history, lanlan_name, detailed=True)
        # settings_manager.extract_and_update_settings(input_history, lanlan_name)
        # semantic_manager.store_conversation(uid, input_history, lanlan_name)
        time_manager.store_conversation(uid, input_history, lanlan_name)
        return {"status": "processed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/get_recent_history/{lanlan_name}")
def get_recent_history(lanlan_name: str):
    history = recent_history_manager.get_recent_history(lanlan_name)
    name_mapping = NAME_MAPPING.copy()
    name_mapping['ai'] = lanlan_name
    result = f"开始聊天前，{lanlan_name}又在脑海内整理了近期发生的事情。\n"
    for i in history:
        if i.type == 'system':
            result += i.content + "\n"
        else:
            result += f"{name_mapping[i.type]} | {'\n'.join([j['text'] for j in i.content if j['type']=='text'])}\n"
    return result

@app.get("/search_for_memory/{lanlan_name}/{query}")
def get_memory(query: str, lanlan_name:str):
    return semantic_manager.query(query, lanlan_name)

@app.get("/get_settings/{lanlan_name}")
def get_settings(lanlan_name: str):
    result = f"{lanlan_name}记得{json.dumps(settings_manager.get_settings(lanlan_name), ensure_ascii=False)}"
    return result

@app.get("/new_dialog/{lanlan_name}")
def new_dialog(lanlan_name: str):
    m1 = re.compile('$$.*?$$')
    name_mapping = NAME_MAPPING.copy()
    name_mapping['ai'] = lanlan_name
    result = f"\n========{lanlan_name}的内心活动========\n{lanlan_name}的脑海里经常想着自己和{MASTER_NAME}的事情，她记得{json.dumps(settings_manager.get_settings(lanlan_name), ensure_ascii=False)}\n\n"
    result += f"开始聊天前，{lanlan_name}又在脑海内整理了近期发生的事情。\n"
    for i in recent_history_manager.get_recent_history(lanlan_name):
        if type(i.content) == str:
            result += f"{name_mapping[i.type]} | {i.content}\n"
        else:
            result += f"{name_mapping[i.type]} | {'\n'.join([m1.sub(j['text'], '') for j in i.content if j['type'] == 'text'])}\n"
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=MEMORY_SERVER_PORT)