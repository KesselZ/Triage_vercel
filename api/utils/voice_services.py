import httpx
import asyncio
import os
import base64
from typing import Dict, Any, Optional, AsyncGenerator
from .doubao_streaming_tts import DoubaoStreamingTTS

async def speech_to_text(audio_data: bytes, filename: str = "audio.webm", mime_type: str = "audio/webm", language: str = "zh") -> Dict[str, Any]:
    """
    语音转文字 - 统一的STT服务
    
    Args:
        audio_data: 音频二进制数据
        filename: 文件名
        mime_type: MIME类型
        language: 语言代码 (zh=中文, en=英文), 默认zh
    
    Returns:
        {"text": "识别到的文本"}
    """
    try:
        # 获取API密钥（支持两种环境变量名）
        api_key = os.getenv('UNIAPI_KEY') or os.getenv('UNIAPI_API_KEY')
        if not api_key:
            raise ValueError("API key not configured")
        
        # 调用UniAPI Whisper-1进行语音识别
        url = "https://api.uniapi.io/v1/audio/transcriptions"
        
        files = {
            "file": (filename, audio_data, mime_type),
            "model": (None, "whisper-1"),
            "language": (None, language)
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            
            transcribed_text = result.get("text", "")
            return {"text": transcribed_text.strip()}
            
    except Exception as e:
        raise Exception(f"Speech recognition failed: {str(e)}")

async def text_to_speech_stream(text: str) -> AsyncGenerator[bytes, None]:
    """
    文字转语音 - 流式版本（边生成边返回）
    
    Args:
        text: 要转换的文本
    
    Yields:
        音频数据块 (bytes)
    """
    try:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        if len(text) > 2000:
            raise ValueError("Text too long (max 2000 characters)")
        
        # 获取豆包凭证
        app_id = os.getenv("DOUBAO_APP_ID", "9369539387")
        access_key = os.getenv("DOUBAO_ACCESS_KEY", "EVHujvbAnGM-OW0T3WHHO1YF8ZHRzINa")
        
        # 创建豆包TTS客户端（使用PCM格式支持真正的流式播放）
        tts_client = DoubaoStreamingTTS(
            app_id=app_id,
            access_key=access_key,
            resource_id="seed-tts-1.0",
            speaker="zh_female_tianxinxiaomei_emo_v2_mars_bigtts",
            audio_format="pcm",
            sample_rate=24000
        )
        
        # 流式合成并返回
        async for audio_chunk in tts_client.synthesize_stream(text.strip()):
            yield audio_chunk
            
    except Exception as e:
        raise Exception(f"Text-to-speech streaming failed: {str(e)}")

def decode_base64_audio(base64_data: str) -> bytes:
    """
    解码base64音频数据
    
    Args:
        base64_data: base64编码的字符串
    
    Returns:
        音频二进制数据
    """
    try:
        return base64.b64decode(base64_data)
    except Exception as e:
        raise Exception(f"Failed to decode base64 audio: {str(e)}")

def encode_audio_to_base64(audio_data: bytes) -> str:
    """
    将音频数据编码为base64
    
    Args:
        audio_data: 音频二进制数据
    
    Returns:
        base64编码的字符串
    """
    try:
        return base64.b64encode(audio_data).decode('utf-8')
    except Exception as e:
        raise Exception(f"Failed to encode audio to base64: {str(e)}")
