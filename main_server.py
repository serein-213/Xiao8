# -*- coding: utf-8 -*-
import asyncio
import json
import traceback
import sys
import uuid
import logging
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from main_helper import core as core, cross_server as cross_server
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
templates = Jinja2Templates(directory="./")
from config import LANLAN_PROMPT, MASTER_NAME, her_name, MAIN_SERVER_PORT

from multiprocessing import Process, Queue, Event
import os
import atexit

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'lanlan_server_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def cleanup():
    logger.info("Starting cleanup process")
    for k in sync_message_queue:
        while sync_message_queue[k] and not sync_message_queue[k].empty():
            sync_message_queue[k].get_nowait()
        sync_message_queue[k].close()
        sync_message_queue[k].join_thread()
    logger.info("Cleanup completed")
atexit.register(cleanup)
sync_message_queue = {}
sync_shutdown_event = {}
session_manager = {}
session_id = {}
sync_process = {}
for k in LANLAN_PROMPT:
    sync_message_queue[k] = Queue()
    sync_shutdown_event[k] = Event()
    session_manager[k] =  core.LLMSessionManager(sync_message_queue[k], k, LANLAN_PROMPT[k].replace('{LANLAN_NAME}', k).replace('{MASTER_NAME}', MASTER_NAME))
    session_id[k] = None
    sync_process[k] = None
lock = asyncio.Lock()

# --- FastAPI App Setup ---
app = FastAPI()

# *** CORRECTED STATIC FILE MOUNTING ***
# Mount the 'static' directory under the URL path '/static'
# When a request comes in for /static/app.js, FastAPI will look for the file 'static/app.js'
# relative to where the server is running (gemini-live-app/).
app.mount("/static", StaticFiles(directory="static"), name="static")


# *** CORRECTED ROOT PATH TO SERVE index.html ***
@app.get("/", response_class=HTMLResponse)
async def get_default_index(request: Request): # 这个接口在直播版代码里是不存在的。为了方便新手用户，增加了一个默认页面。
    # Point FileResponse to the correct path relative to where server.py is run
    return templates.TemplateResponse("templates/index.html", {
        "request": request,
        "lanlan_name": her_name,
        "model_path": f"/static/live2d/mao_pro.model3.json" 
    })

@app.get("/{lanlan_name}", response_class=HTMLResponse)
async def get_index(request: Request, lanlan_name: str):
    # Point FileResponse to the correct path relative to where server.py is run
    return templates.TemplateResponse("templates/index.html", {
        "request": request,
        "lanlan_name": lanlan_name,
        "model_path": f"/static/live2d/mao_pro.model3.json" # TODO: 根据lanlan_name动态加载模型. 实现起来很简单，但是用户需要手动配置、还需要调整大小和位置，当前版本先不增加复杂度
    })

@app.on_event("startup")
async def startup_event():
    global sync_process
    logger.info("Starting sync connector processes")
    # 启动同步连接器进程
    for k in sync_process:
        if sync_process[k] is None:
            sync_process[k] = Process(
                target=cross_server.sync_connector_process,
                args=(sync_message_queue[k], sync_shutdown_event[k], k, "ws://localhost:8002", {'bullet': False, 'monitor': False})
            )
            sync_process[k].start()
            logger.info(f"同步连接器进程已启动 (PID: {sync_process[k].pid})")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Shutting down sync connector processes")
    # 关闭同步服务器连接
    for k in sync_process:
        if sync_process[k] is not None:
            sync_shutdown_event[k].set()
            sync_process[k].join(timeout=3)  # 等待进程正常结束
            if sync_process[k].is_alive():
                sync_process[k].terminate()  # 如果超时，强制终止
    logger.info("同步连接器进程已停止")


@app.websocket("/ws/{lanlan_name}")
async def websocket_endpoint(websocket: WebSocket, lanlan_name: str):
    await websocket.accept()
    this_session_id = uuid.uuid4()
    async with lock:
        global session_id
        session_id[lanlan_name] = this_session_id
    logger.info(f"⭐websocketWebSocket accepted: {websocket.client}, new session id: {session_id[lanlan_name]}, lanlan_name: {lanlan_name}")

    try:
        while True:
            data = await websocket.receive_text()
            if session_id[lanlan_name] != this_session_id:
                await session_manager[lanlan_name].send_status(f"切换至另一个终端...")
                await websocket.close()
                break
            message = json.loads(data)
            action = message.get("action")
            # logger.debug(f"WebSocket received action: {action}") # Optional debug log

            if action == "start_session":
                session_manager[lanlan_name].active_session_is_idle = False
                input_type = message.get("input_type")
                if input_type in ['audio', 'screen', 'camera']:
                    asyncio.create_task(session_manager[lanlan_name].start_session(websocket, message.get("new_session", False)))
                else:
                    await session_manager[lanlan_name].send_status(f"Invalid input type: {input_type}")

            elif action == "stream_data":
                asyncio.create_task(session_manager[lanlan_name].stream_data(message))

            elif action == "end_session":
                session_manager[lanlan_name].active_session_is_idle = False
                asyncio.create_task(session_manager[lanlan_name].end_session())

            elif action == "pause_session":
                session_manager[lanlan_name].active_session_is_idle = True

            else:
                logger.warning(f"Unknown action received: {action}")
                await session_manager[lanlan_name].send_status(f"Unknown action: {action}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}")
    except Exception as e:
        error_message = f"WebSocket handler error: {e}"
        logger.error(f"💥 {error_message}")
        logger.error(traceback.format_exc())
        try:
            await session_manager[lanlan_name].send_status(f"Server error: {e}")
        except:
            pass
    finally:
        logger.info(f"Cleaning up WebSocket resources: {websocket.client}")
        await session_manager[lanlan_name].cleanup()

# --- Run the Server ---
# (Keep your existing __main__ block)
if __name__ == "__main__":
    import uvicorn

    logger.info("--- Starting FastAPI Server ---")
    # Use os.path.abspath to show full path clearly
    logger.info(f"Serving static files from: {os.path.abspath('static')}")
    logger.info(f"Serving index.html from: {os.path.abspath('templates/index.html')}")
    logger.info(f"Access UI at: http://127.0.0.1:{MAIN_SERVER_PORT} (or your network IP:{MAIN_SERVER_PORT})")
    logger.info("-----------------------------")
    # Run from the directory containing server.py (gemini-live-app/)
    uvicorn.run("main_server:app", host="0.0.0.0", port=MAIN_SERVER_PORT, reload=False)

