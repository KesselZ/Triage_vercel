import os
import base64
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, validator
import asyncio
import json

from .utils.ai_client import get_next_question, generate_diagnosis
from .utils.voice_services import speech_to_text, text_to_speech_stream, decode_base64_audio
from .utils.doubao_streaming_asr import DoubaoStreamingASR


# 支持的模型列表
SUPPORTED_MODELS = [
    "grok-4-1-fast-non-reasoning",
    "doubao-seed-1-6-thinking-250715", 
    "deepseek-v3.2-exp"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_index():
    """返回前端首页 public/index.html"""
    index_path = os.path.join(BASE_DIR, "..", "public", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


class ChatRequest(BaseModel):
    # history 中的每一项至少包含 role/content，但前端还会带上 options、selectedOptions 等字段
    # 因此前端发来的是 Dict[str, Any]，不能用 Dict[str, str] 否则会导致 422 验证失败
    history: List[Dict[str, Any]]
    model: str = "grok-4-1-fast-non-reasoning"  # 默认模型
    
    @validator('model')
    def validate_model(cls, v):
        if v not in SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {v}. 支持的模型: {', '.join(SUPPORTED_MODELS)}")
        return v

class TTSRequest(BaseModel):
    text: str

@app.post("/api/chat/next")
async def chat_next(request: ChatRequest):
    """问诊接口"""
    print("🔥 [FastAPI-index.py] /api/chat/next 被调用")
    result = await get_next_question(request.history, request.model)
    return result

@app.post("/api/chat/diagnose")
async def chat_diagnose(request: ChatRequest):
    """诊断接口"""
    print("🔥 [FastAPI-index.py] /api/chat/diagnose 被调用")
    result = await generate_diagnosis(request.history, request.model)
    return result

@app.post("/api/chat/tts-stream")
async def text_to_speech_stream_endpoint(request: TTSRequest):
    """文本转语音 - 流式返回版本（边生成边播放）"""
    print("🔥 [FastAPI-index.py] /api/chat/tts-stream 被调用")
    try:
        # 返回流式音频响应
        return StreamingResponse(
            text_to_speech_stream(request.text),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS streaming service error: {str(e)}")

@app.post("/api/chat/stt")
async def speech_to_text_endpoint(request: Request):
    """语音转文字 - 支持JSON和FormData格式"""
    print("🔥 [FastAPI-index.py] /api/chat/stt 被调用")
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # JSON格式（base64编码）
            body = await request.json()
            audio_base64 = body.get("audio_data")
            mime_type = body.get("mime_type", "audio/webm")
            language = body.get("language", "zh")
            
            if not audio_base64:
                raise HTTPException(status_code=400, detail="audio_data field is required")
            
            audio_data = decode_base64_audio(audio_base64)
            filename = "audio.webm"
        else:
            # FormData格式（原始文件上传）
            form = await request.form()
            if "file" not in form:
                raise HTTPException(status_code=400, detail="file field is required")
            
            file = form["file"]
            audio_data = await file.read()
            filename = file.filename
            mime_type = file.content_type
            language = form.get("language", "zh")
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Audio data is empty")
        
        if "application/json" not in content_type and not mime_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        result = await speech_to_text(audio_data, filename, mime_type, language)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT service error: {str(e)}")


@app.websocket("/api/chat/streaming-asr")
async def streaming_asr_websocket(websocket: WebSocket):
    """
    流式语音识别 WebSocket 端点（支持多轮识别）
    
    协议：
    1. 前端连接后发送 {"action": "start"} 开始识别
    2. 前端持续发送音频数据（二进制）
    3. 前端发送 {"action": "stop"} 结束识别
    4. 后端返回识别结果 {"type": "partial/final", "text": "..."}
    5. 可以重复步骤1-4进行多轮识别
    """
    await websocket.accept()
    print("📡 [WebSocket] 客户端已连接")
    
    # 从环境变量获取豆包凭证
    app_id = os.getenv("DOUBAO_APP_ID", "9369539387")
    access_token = os.getenv("DOUBAO_ACCESS_TOKEN", "EVHujvbAnGM-OW0T3WHHO1YF8ZHRzINa")
    
    try:
        # 保持连接，支持多轮识别
        while True:
            client = None
            receive_task = None
            
            try:
                # 等待前端发送 start 命令
                data = await websocket.receive_json()
                if data.get("action") != "start":
                    print(f"⚠️  [WebSocket] 收到非 start 命令: {data}")
                    continue
                
                print("🎤 [WebSocket] 开始新一轮识别")
                
                # 初始化豆包客户端
                client = DoubaoStreamingASR(
                    app_id=app_id,
                    token=access_token,
                    mode="async",
                    sample_rate=16000
                )
                
                # 连接到豆包服务
                await client.connect()
                await client.send_start_request()
                
                # 创建接收任务
                async def receive_results():
                    """接收豆包识别结果并转发给前端"""
                    try:
                        while True:
                            result = await client.receive_result()
                            if result is None:
                                break
                            
                            if result['text']:
                                # 转发给前端
                                await websocket.send_json({
                                    "type": "final" if result['is_final'] else "partial",
                                    "text": result['text']
                                })
                                print(f"📤 [WebSocket] {'最终' if result['is_final'] else '临时'}: {result['text']}")
                                
                                if result['is_final']:
                                    break
                    except Exception as e:
                        print(f"❌ [WebSocket] 接收结果错误: {e}")
                
                receive_task = asyncio.create_task(receive_results())
                
                # 接收前端音频数据
                while True:
                    try:
                        message = await websocket.receive()
                        
                        if "bytes" in message:
                            # 音频数据
                            audio_data = message["bytes"]
                            await client.send_audio_chunk(audio_data, is_last=False)
                            
                        elif "text" in message:
                            # 控制命令
                            data = json.loads(message["text"])
                            if data.get("action") == "stop":
                                print("⏸️  [WebSocket] 收到停止命令")
                                # 发送结束标记
                                await client.send_audio_chunk(b'', is_last=True)
                                # 等待最终结果
                                await receive_task
                                break
                            elif data.get("action") == "start":
                                # 新一轮识别，退出当前循环
                                print("🔄 [WebSocket] 收到新的 start 命令，准备新一轮识别")
                                break
                                
                    except WebSocketDisconnect:
                        print("🔌 [WebSocket] 客户端断开连接")
                        return
                    except Exception as e:
                        print(f"❌ [WebSocket] 处理消息错误: {e}")
                        await websocket.send_json({"type": "error", "message": str(e)})
                        break
                
                # 发送完成信号
                await websocket.send_json({"type": "done"})
                print("✅ [WebSocket] 本轮识别完成，等待下一轮...")
                
            finally:
                # 清理本轮资源
                if receive_task and not receive_task.done():
                    receive_task.cancel()
                if client:
                    await client.close()
                    
    except WebSocketDisconnect:
        print("🔌 [WebSocket] 客户端主动断开")
    except Exception as e:
        print(f"❌ [WebSocket] 错误: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        print("🔌 [WebSocket] 连接已关闭")
