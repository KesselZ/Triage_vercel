import os
import httpx
import base64

# STT API配置
API_KEY = 'sk-bpmbUPhf3msR5fM_06Is2VTgUvvq1w4st6q-pR2-1sUIBCWrdm7EdgoO6mo'
BASE_URL = "https://api.uniapi.io/v1"
STT_MODEL = "whisper-1"

async def test_stt():
    """测试STT API调用"""
    if not API_KEY:
        print("错误：请设置API_KEY")
        return
    
    # 首先生成一个测试音频文件（如果还没有的话）
    test_audio_path = "test_speech.mp3"
    if not os.path.exists(test_audio_path):
        print(f"错误：找不到测试音频文件 {test_audio_path}")
        print("请先运行 test.py 生成测试音频")
        return
    
    # 读取音频文件并转换为base64
    with open(test_audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
    
    url = f"{BASE_URL}/audio/transcriptions"
    
    # 使用multipart/form-data格式上传文件
    files = {
        "file": (test_audio_path, audio_data, "audio/mp3"),
        "model": (None, STT_MODEL),
        "language": (None, "zh")
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        print("正在调用STT API...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, files=files)
            response.raise_for_status()
            
            result = response.json()
            transcribed_text = result.get("text", "")
            
            print(f"识别结果：{transcribed_text}")
            print(f"原始文本：我是智能AI医生")
            
            # 简单的准确性检查
            if "智能AI医生" in transcribed_text or "智能AI" in transcribed_text:
                print("✅ 语音识别成功！")
            else:
                print("⚠️ 识别结果可能不够准确")
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP错误：{e}")
        print(f"响应内容：{e.response.text}")
    except Exception as e:
        print(f"调用失败：{e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_stt())