import os
import httpx
import base64

# TTS API配置
API_KEY = 'sk-bpmbUPhf3msR5fM_06Is2VTgUvvq1w4st6q-pR2-1sUIBCWrdm7EdgoO6mo'
BASE_URL = "https://api.uniapi.io/v1"
TTS_MODEL = "tts-1"

async def test_tts():
    """测试TTS API调用"""
    if not API_KEY:
        print("错误：请设置UNIAPI_API_KEY环境变量")
        return
    
    url = f"{BASE_URL}/audio/speech"
    
    # 请求参数
    payload = {
        "model": TTS_MODEL,
        "input": "我是智能AI医生",
        "voice": "alloy",  # 默认声音，可以根据需要调整
        "response_format": "webm"
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        print("正在调用TTS API...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # 保存音频文件
            audio_content = response.content
            with open("test_speech.mp3", "wb") as f:
                f.write(audio_content)
            
            print(f"成功生成音频文件：test_speech.mp3")
            print(f"音频大小：{len(audio_content)} bytes")
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP错误：{e}")
        print(f"响应内容：{e.response.text}")
    except Exception as e:
        print(f"调用失败：{e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tts())