'''
这个模块在直播用的codebase中是可以运行的。但是，还没有对开源版本进行适配。
'''
import asyncio
import json
from config import MONITOR_SERVER_PORT
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
from fastapi.templating import Jinja2Templates
from google.cloud import translate_v2
templates = Jinja2Templates(directory="./")

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/streamer")
async def get_stream():
    return FileResponse('templates/streamer.html')

@app.get("/subtitle")
async def get_subtitle():
    return FileResponse('templates/subtitle.html')

@app.get("/{lanlan_name}", response_class=HTMLResponse)
async def get_index(request: Request, lanlan_name: str):
    # Point FileResponse to the correct path relative to where server.py is run
    return templates.TemplateResponse("templates/viewer.html", {
        "request": request,
        "lanlan_name": lanlan_name
    })


# 存储所有连接的客户端
connected_clients = set()
subtitle_clients = set()
current_subtitle = ""
should_clear_next = False

def is_japanese(text):
    import re
    # 检测平假名、片假名、汉字
    japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF]')
    return bool(japanese_pattern.search(text))

# 简单的日文到中文翻译（这里需要你集成实际的翻译API）
translate_client = translate_v2.Client()
async def translate_japanese_to_chinese(text):
    # 这里应该调用实际的翻译服务，比如Google Translate API或百度翻译API
    # 为了演示，这里返回一个占位符
    # 你需要根据实际情况实现翻译功能
    results = translate_client.translate(
        values=[text],
        target_language="zh-CN",
        source_language="ja"
    )
    return results[0]['translatedText']


@app.websocket("/subtitle_ws")
async def subtitle_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"字幕客户端已连接: {websocket.client}")

    # 添加到字幕客户端集合
    subtitle_clients.add(websocket)

    try:
        # 发送当前字幕（如果有）
        if current_subtitle:
            await websocket.send_json({
                "type": "subtitle",
                "text": current_subtitle
            })

        # 保持连接
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"字幕客户端已断开: {websocket.client}")
    finally:
        subtitle_clients.discard(websocket)


# 广播字幕到所有字幕客户端
async def broadcast_subtitle():
    global current_subtitle, should_clear_next
    if should_clear_next:
        await clear_subtitle()
        should_clear_next = False
        # 给一个短暂的延迟让清空动画完成
        await asyncio.sleep(0.3)

    clients = subtitle_clients.copy()
    for client in clients:
        try:
            await client.send_json({
                "type": "subtitle",
                "text": current_subtitle
            })
        except Exception as e:
            print(f"字幕广播错误: {e}")
            subtitle_clients.discard(client)


# 清空字幕
async def clear_subtitle():
    global current_subtitle
    current_subtitle = ""

    clients = subtitle_clients.copy()
    for client in clients:
        try:
            await client.send_json({
                "type": "clear"
            })
        except Exception as e:
            print(f"清空字幕错误: {e}")
            subtitle_clients.discard(client)

# 主服务器连接端点
@app.websocket("/sync/{lanlan_name}")
async def sync_endpoint(websocket: WebSocket, lanlan_name:str):
    await websocket.accept()
    print(f"主服务器已连接: {websocket.client}")

    try:
        while True:
            try:
                global current_subtitle
                data = await asyncio.wait_for(websocket.receive_text(), timeout=25)

                # 广播到所有连接的客户端
                data = json.loads(data)

                if data.get("type") == "gemini_response":
                    # 发送到字幕显示
                    subtitle_text = data.get("text", "")
                    current_subtitle += subtitle_text
                    if subtitle_text:
                        await broadcast_subtitle()

                elif data.get("type") == "turn end":
                    print('turn end')
                    # 处理回合结束
                    if current_subtitle:
                        # 检查是否为日文，如果是则翻译
                        if is_japanese(current_subtitle):
                            translated_text = await translate_japanese_to_chinese(current_subtitle)
                            current_subtitle = translated_text
                            clients = subtitle_clients.copy()
                            for client in clients:
                                try:
                                    await client.send_json({
                                        "type": "subtitle",
                                        "text": translated_text
                                    })
                                except Exception as e:
                                    print(f"翻译字幕广播错误: {e}")
                                    subtitle_clients.discard(client)

                    # 清空字幕区域，准备下一条
                    global should_clear_next
                    should_clear_next = True

                if data.get("type") != "heartbeat":
                    await broadcast_message(data)
            except asyncio.exceptions.TimeoutError:
                pass
    except WebSocketDisconnect:
        print(f"主服务器已断开: {websocket.client}")
    except Exception as e:
        print(f"同步端点错误: {e}")


# 二进制数据同步端点
@app.websocket("/sync_binary/{lanlan_name}")
async def sync_binary_endpoint(websocket: WebSocket, lanlan_name:str):
    await websocket.accept()
    print(f"主服务器二进制连接已建立: {websocket.client}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=25)
                if len(data)>4:
                    await broadcast_binary(data)
            except asyncio.exceptions.TimeoutError:
                pass
    except WebSocketDisconnect:
        print(f"主服务器二进制连接已断开: {websocket.client}")
    except Exception as e:
        print(f"二进制同步端点错误: {e}")
        import traceback
        traceback.print_exc()


# 客户端连接端点
@app.websocket("/ws/{lanlan_name}")
async def websocket_endpoint(websocket: WebSocket, lanlan_name:str):
    await websocket.accept()
    print(f"查看客户端已连接: {websocket.client}")

    # 添加到连接集合
    connected_clients.add(websocket)

    try:
        # 保持连接直到客户端断开
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"查看客户端已断开: {websocket.client}")
    finally:
        connected_clients.remove(websocket)


# 广播消息到所有客户端
async def broadcast_message(message):
    clients = connected_clients.copy()
    for client in clients:
        try:
            await client.send_json(message)
        except Exception as e:
            print(f"广播错误: {e}")
            try:
                connected_clients.remove(client)
            except:
                pass


# 广播二进制数据到所有客户端
async def broadcast_binary(data):
    clients = connected_clients.copy()
    for client in clients:
        try:
            await client.send_bytes(data)
        except Exception as e:
            print(f"二进制广播错误: {e}")
            try:
                connected_clients.remove(client)
            except:
                pass


# 定期清理断开的连接
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_disconnected_clients())


async def cleanup_disconnected_clients():
    while True:
        try:
            # 检查并移除已断开的客户端
            for client in list(connected_clients):
                try:
                    await client.send_json({"type": "heartbeat"})
                except Exception as e:
                    print("广播错误:", e)
                    connected_clients.remove(client)
            await asyncio.sleep(60)  # 每分钟检查一次
        except Exception as e:
            print(f"清理客户端错误: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    uvicorn.run("monitor:app", host="0.0.0.0", port=MONITOR_SERVER_PORT, reload=True)
