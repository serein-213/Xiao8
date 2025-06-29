from config.api import *
from config.prompts_chara import *

TIME_ORIGINAL_TABLE_NAME = "time_indexed_original"
TIME_COMPRESSED_TABLE_NAME = "time_indexed_compressed"


'''
↓↓↓ 核心人设在这里 ↓↓↓
'''
MASTER_NAME = '哥哥'
her_name = "test" 
master_basic_config = {'性别': '男', '昵称': MASTER_NAME}

lanlan_basic_config = {her_name: {'性别': '女',
                                '年龄': 15,
                                '昵称': ["T酱", "小T"],
                                }}
'''
↑↑↑ 核心人设在这里 ↑↑↑
'''


"""
本项目支持多个角色，但是为了方便新手用户进行配置，临时增加了一个her_name变量来帮助批量设置初始角色的信息。
请将her_name后的字符串修改为角色名称。
"""
NAME_MAPPING = {'human': MASTER_NAME, 'system': "SYSTEM_MESSAGE"}
LANLAN_PROMPT = {her_name: lanlan_prompt}
SEMANTIC_STORE = {her_name: f'memory/store/semantic_memory_{her_name}'}
TIME_STORE = {her_name: f'memory/store/time_indexed_{her_name}'}
SETTING_STORE = {her_name: f'memory/store/settings_{her_name}.json'}
RECENT_LOG = {her_name: f'memory/store/recent_{her_name}.json'}


import json
try:
    with open('core_config.txt', 'r') as f:
        core_cfg = json.load(f)
    if 'coreApiKey' in core_cfg and core_cfg['coreApiKey'] and core_cfg['coreApiKey'] != CORE_API_KEY:
        print(f"Warning: coreApiKey in core_config.txt is updated. Overwriting CORE_API_KEY.")
        CORE_API_KEY = core_cfg['coreApiKey']

except FileNotFoundError:
    pass
except Exception as e:
    print(f"💥 Error parsing core_config.txt: {e}")

if  AUDIO_API_KEY == '':
    AUDIO_API_KEY = CORE_API_KEY
if  OPENROUTER_API_KEY == '':
    OPENROUTER_API_KEY = CORE_API_KEY
