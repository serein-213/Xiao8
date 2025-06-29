"""
本模块用于将lanlan的消息转发至所有相关服务器，包括：
1. Bullet Server。对实时内容进行监听并与直播间弹幕进行交互。
2. Monitor Server。将实时内容转发至所有副终端。副终端会同步播放与主终端完全相同的内容，但不具备交互性。同一时间只有一个主终端可以交互。
3. Memory Server。对对话历史进行总结、分析，并转为持久化记忆。
注意，cross server是一个单向的转发器，不会将任何内容回传给主进程。如需回传，目前仍需要建立专门的双向连接。
"""

import ssl

import asyncio
import time
import pickle
import aiohttp
from config import MONITOR_SERVER_PORT, MEMORY_SERVER_PORT, COMMENTER_SERVER_PORT
from datetime import datetime
import json
import requests
import re
from utils.frontend_utils import contains_chinese, replace_blank, replace_corner_mark, remove_bracket, spell_out_number, \
    is_only_punctuation, split_paragraph
emoji_pattern = re.compile(r'[^\w\u4e00-\u9fff\s>][^\w\u4e00-\u9fff\s]{2,}[^\w\u4e00-\u9fff\s<]', flags=re.UNICODE)
emoji_pattern2 = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)
emotion_pattern = re.compile('<(.*?)>')


def normalize_text(text):  # 对文本进行基本预处理
    text = text.strip()
    text = replace_blank(text)

    text = emoji_pattern2.sub('', text)
    text = emoji_pattern.sub('', text)
    text = emotion_pattern.sub("", text)
    if is_only_punctuation(text):
        return ""
    return text

async def keep_reader(ws: aiohttp.ClientWebSocketResponse):
    while not ws.closed:
        try:
            await ws.receive(timeout=30)
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            break


def sync_connector_process(message_queue, shutdown_event, lanlan_name, sync_server_url=f"ws://localhost:{MONITOR_SERVER_PORT}", config=None):
    """独立进程运行的同步连接器"""

    # 创建一个新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    chat_history = []
    default_config = {'bullet': True, 'monitor': True}
    if config is None:
        config = {}
    config = default_config | config

    async def maintain_connection(chat_history, lanlan_name):
        sync_session = None
        sync_ws = None
        sync_reader = None
        binary_session = None
        binary_ws = None
        binary_reader = None
        bullet_session = None
        bullet_ws = None
        bullet_reader = None

        user_input_cache = ''
        text_output_cache = '' # lanlan的当前消息
        current_turn = 'user'
        last_screen = None

        while not shutdown_event.is_set():
            try:
                # 如果连接不存在或已关闭，重新连接
                if config['monitor']:
                    if sync_ws is None or sync_ws.closed:
                        if sync_session:
                            await sync_session.close()
                        sync_session = aiohttp.ClientSession()
                        sync_ws = await sync_session.ws_connect(
                            f"{sync_server_url}/sync/{lanlan_name}",
                            heartbeat=10,
                        )
                        # print("[Sync Process] 文本连接已建立")
                        sync_reader = asyncio.create_task(keep_reader(sync_ws))

                    if binary_ws is None or binary_ws.closed:
                        if binary_session:
                            await binary_session.close()
                        binary_session = aiohttp.ClientSession()
                        binary_ws = await binary_session.ws_connect(
                            f"{sync_server_url}/sync_binary/{lanlan_name}",
                            heartbeat=10,
                        )
                        # print("[Sync Process] 二进制连接已建立")
                        binary_reader = asyncio.create_task(keep_reader(binary_ws))

                if config['bullet']:
                    if bullet_ws is None or bullet_ws.closed:
                        if bullet_session:
                            await bullet_session.close()
                        bullet_session = aiohttp.ClientSession()
                        bullet_ws = await bullet_session.ws_connect(
                            f"wss://localhost:{COMMENTER_SERVER_PORT}/sync/{lanlan_name}",
                            ssl=ssl._create_unverified_context()
                        )
                        bullet_reader = asyncio.create_task(keep_reader(bullet_ws))

                # 检查消息队列
                while not message_queue.empty():
                    message = message_queue.get()

                    if message["type"] == "json":
                        if config['monitor'] and sync_ws:
                            await sync_ws.send_json(message["data"])
                        if current_turn == 'user': # 说明是lanlan的新消息
                            if user_input_cache:
                                chat_history.append({'role': 'user', 'content': [{"type": "text","text": user_input_cache.replace('小巴', '小八')}]})
                                user_input_cache = ''
                            current_turn = 'assistant'
                            text_output_cache = datetime.now().strftime('[%Y%m%d %a %H:%M] ')

                            if config['bullet'] and bullet_ws:
                                try:
                                    last_user = last_ai = None
                                    for i in chat_history[::-1]:
                                        if i["role"] == "user":
                                            last_user = i['content'][0]['text']
                                            break
                                    for i in chat_history[::-1]:
                                        if i["role"] == "assistant":
                                            last_ai = i['content'][0]['text']
                                            break

                                    message_data = {
                                        "user": last_user,
                                        "ai": last_ai,
                                        "screen": last_screen
                                    }
                                    binary_message = pickle.dumps(message_data)
                                    await bullet_ws.send_bytes(binary_message)
                                except Exception as e:
                                    print("💥Error when sending to commenter: ", e)

                        if message["data"]["type"] == "gemini_response":
                            text_output_cache += message["data"]["text"]

                    elif message["type"] == "binary":
                        if config['monitor'] and binary_ws:
                            await binary_ws.send_bytes(message["data"])

                    elif message["type"] == "user":  # 准备转录
                        data = message["data"].get("data")
                        input_type = message["data"].get("input_type")
                        if input_type == "transcript": # 暂时只处理语音，后续还需要记录图片
                            if user_input_cache == '' and config['monitor'] and sync_ws:
                                await sync_ws.send_json({'type': 'user_activity'}) #用于打断前端声音播放
                            user_input_cache += data
                        elif input_type == "screen":
                            last_screen = data

                    elif message["type"] == "system":
                        try:
                            if message["data"] == "google disconnected":
                                if len(text_output_cache) > 0:
                                    chat_history.append({'role': 'system', 'content': [
                                        {'type': 'text', 'text': "网络错误，您已断开连接！"}]})
                                text_output_cache = ''

                            if message["data"] == "renew session":
                                current_turn = 'user'
                                text_output_cache = normalize_text(text_output_cache)
                                if len(text_output_cache) > 0:
                                    chat_history.append(
                                            {'role': 'assistant', 'content': [{'type': 'text', 'text': text_output_cache}]})
                                text_output_cache = ''
                                response = requests.post(
                                    f"http://localhost:{MEMORY_SERVER_PORT}/renew/{lanlan_name}",
                                    json={'input_history': json.dumps(chat_history, indent=2, ensure_ascii=False)},
                                )
                                if response.json()['status'] == 'error':
                                    print("💥 Conversation processing error", response.json()['message'])
                                chat_history.clear()

                            if message["data"] == 'turn end': # lanlan的消息结束了
                                current_turn = 'user'
                                text_output_cache = normalize_text(text_output_cache)
                                if len(text_output_cache) > 0:
                                    chat_history.append(
                                        {'role': 'assistant', 'content': [{'type': 'text', 'text': text_output_cache}]})
                                text_output_cache = ''
                                if config['monitor'] and sync_ws:
                                    await sync_ws.send_json({'type': 'turn end'})

                            elif message["data"] == 'session end': # 当前session结束了
                                print("💗开始处理聊天历史")
                                response = requests.post(
                                    f"http://localhost:{MEMORY_SERVER_PORT}/process/{lanlan_name}",
                                    json={'input_history': json.dumps(chat_history, indent=2, ensure_ascii=False)},
                                )
                                if response.json()['status'] == 'error':
                                    print("💥 Conversation processing error", response.json()['message'])
                                text_output_cache = ''  # lanlan的当前消息
                                current_turn = 'user'
                                chat_history.clear()
                        except Exception as e:
                            print('❗️❗️❗️System message error: ', e)
                            import traceback
                            traceback.print_exc()
                    await asyncio.sleep(0.01)
                # 发送心跳
                if config['monitor'] and sync_ws:
                    await sync_ws.send_json({"type": "heartbeat", "timestamp": time.time()})
                if config['monitor'] and binary_ws:
                    await binary_ws.send_bytes(b'\x00\x01\x02\x03')

                # 短暂休眠避免CPU占用过高
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # print(f"[Sync Process] 连接错误: {e}")
                # import traceback
                # traceback.print_exc()
                # 关闭任何可能存在的连接
                if config['monitor']:
                    if sync_ws and not sync_ws.closed:
                        await sync_ws.close()
                    if sync_session:
                        await sync_session.close()
                    if sync_reader:
                        sync_reader.cancel()
                    if binary_ws and not binary_ws.closed:
                        await binary_ws.close()
                    if binary_session:
                        await binary_session.close()
                    if binary_reader:
                        binary_reader.cancel()
                if config['bullet']:
                    if bullet_ws and not bullet_ws.closed:
                        await bullet_ws.close()
                    if bullet_session:
                        await bullet_session.close()
                    if bullet_reader:
                        bullet_reader.cancel()

                sync_ws = None
                binary_ws = None
                bullet_ws = None
                await asyncio.sleep(0.2)  # 重连前等待

        # 关闭资源
        for ws in [sync_ws, binary_ws, bullet_ws]:
            if ws and not ws.closed:
                await ws.close()
        for sess in [sync_session, binary_session, bullet_session]:
            if sess:
                await sess.close()
        for rdr in [sync_reader, binary_reader, bullet_reader]:
            if rdr:
                rdr.cancel()

    try:
        loop.run_until_complete(maintain_connection(chat_history, lanlan_name))
    except Exception as e:
        print(f"[Sync Process] 进程错误: {e}")
    finally:
        loop.close()

        print("[Sync Process] 同步进程已终止")
