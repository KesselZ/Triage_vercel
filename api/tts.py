import json
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.utils.voice_services import text_to_speech

def handler(request, response):
    """
    Vercel serverless function for text-to-speech
    """
    # 设置CORS头
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Content-Type'] = 'application/json'
    
    # 处理OPTIONS请求（CORS预检）
    if request.method == 'OPTIONS':
        response.status_code = 200
        return ''
    
    if request.method != 'POST':
        response.status_code = 405
        return json.dumps({'error': 'Method not allowed'})
    
    try:
        # 解析请求体
        body = json.loads(request.body)
        text = body.get('text', '')
        
        if not text.strip():
            response.status_code = 400
            return json.dumps({'error': 'No text provided'})
        
        # 调用共享的TTS服务
        result = asyncio.run(text_to_speech(text))
        
        response.status_code = 200
        return json.dumps(result)
        
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        response.status_code = 500
        return json.dumps({"error": str(e)})
