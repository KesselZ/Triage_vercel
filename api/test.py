import json

def handler(request, response):
    """简单的测试函数"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'
    
    if request.method == 'OPTIONS':
        response.status_code = 200
        return ''
    
    return json.dumps({
        'message': 'Test function working!',
        'method': request.method,
        'body': request.body
    })

# Vercel也支持这种格式
def lambda_handler(event, context):
    """AWS Lambda兼容格式"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Lambda handler working!',
            'httpMethod': event.get('httpMethod'),
            'path': event.get('path')
        })
    }
