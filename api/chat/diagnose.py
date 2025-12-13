import json
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.utils.ai_client import generate_diagnosis

def handler(request, response):
    """
    Vercel serverless function for diagnosis
    """
    print("⚡ [Serverless-diagnose.py] /api/chat/diagnose 被调用")
    # 设置CORS头
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
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
        history = body.get('history', [])
        
        # 调用AI生成诊断（包装异步调用）
        result = asyncio.run(generate_diagnosis(history))
        
        response.status_code = 200
        return json.dumps(result)
        
    except Exception as e:
        print(f"Error in diagnose.py: {e}")
        response.status_code = 500
        return json.dumps({'error': str(e)})
