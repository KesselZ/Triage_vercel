import os
import json
from typing import List, Dict, Any

import httpx


API_KEY = os.getenv("UNIAPI_API_KEY")
BASE_URL = os.getenv("UNIAPI_BASE_URL", "https://hk.uniapi.io/v1").rstrip("/")


async def _create_chat_completion(
    *,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float = 0.3,
    max_tokens: int | None = None,
    response_format: Dict[str, Any] | None = None,
) -> str:
    """调用 UniAPI(OpenAI 兼容) 的 /chat/completions 接口，返回 content 字符串。
    支持多模态输入（文本+图片）。
    """

    if not API_KEY:
        raise RuntimeError("UNIAPI_API_KEY is not set in environment variables")

    url = f"{BASE_URL}/chat/completions"

    # 处理消息，支持图片
    processed_messages = []
    for msg in messages:
        if "images" in msg and msg["images"]:
            # 构建多模态消息
            content_parts = []
            
            # 添加文本部分
            if msg.get("content"):
                content_parts.append({
                    "type": "text",
                    "text": msg["content"]
                })
            
            # 添加图片部分
            for img in msg["images"]:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['mime_type']};base64,{img['base64']}"
                    }
                })
            
            processed_messages.append({
                "role": msg["role"],
                "content": content_parts
            })
        else:
            # 普通文本消息
            processed_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    payload: Dict[str, Any] = {
        "model": model,
        "messages": processed_messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if response_format is not None:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:  # 增加超时时间以处理图片
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()

    data = resp.json()
    # 兼容 OpenAI 风格的返回结构
    return data["choices"][0]["message"]["content"].strip()

async def get_next_question(history: List[Dict[str, Any]], model: str = "grok-4-1-fast-non-reasoning") -> Dict[str, Any]:
    """
    根据对话历史，决定是继续提问还是停止。
    """
    system_prompt = """你是一位温暖贴心的三甲医院分诊医生助手。你的任务是通过询问患者症状来收集信息，以便进行初步分诊。

请用关怀、温暖的语气与患者交流，就像一位真正关心患者健康的医生。

患者是可以上传照片的，如果有，请根据图片内容进行分析。

规则：
1. 每次只问**一个**最关键的补充问题。
2. 根据可能的相关多种疾病，解析症状，为病人提供可选择的症状列表进行确认。
3. 选择项应该简洁明了，4-6个选项为宜，包括常见相关症状。
4. 如果问题不适合提供选项（如需要详细描述），可以只返回问题文本。
5. 如果你认为当前收集的信息已经足够判断大概的疾病方向和挂号科室，请直接回复 "STOP_ASKING"。
6. 严禁在此时给出诊断结果，只负责提问。
7. 语气要求：
   - 用温暖关怀的语气，像医生关心患者一样交流


输出格式：
- 如果需要继续提问且提供选项：{"question": "问题内容", "options": ["选项1", "选项2", "选项3"]}
- 如果需要继续提问但不提供选项：{"question": "问题内容"}
- 如果信息足够：{"status": "stop"}

请严格按照JSON格式输出，不要包含任何markdown标记。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # 打印调试信息
    print(f"📸 [AI Client] 处理历史消息，共 {len(history)} 条")
    for i, msg in enumerate(history):
        has_images = "images" in msg and msg.get("images")
        print(f"  消息 {i+1}: role={msg.get('role')}, 有图片={has_images}, 图片数量={len(msg.get('images', []))}")
        if has_images:
            for j, img in enumerate(msg.get("images", [])):
                print(f"    图片 {j+1}: mime_type={img.get('mime_type')}, base64长度={len(img.get('base64', ''))}")
    
    messages.extend(history)

    try:
        content = await _create_chat_completion(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        result = json.loads(content)
        
        if "status" in result and result["status"] == "stop":
            return {"status": "stop"}
        elif "question" in result:
            return {"status": "continue", **result}
        else:
            return {"status": "error", "message": "Invalid response format"}
            
    except Exception as e:
        print(f"Error calling AI: {e}")
        return {"status": "error", "message": str(e)}

async def generate_diagnosis(history: List[Dict[str, Any]], model: str = "grok-4-1-fast-non-reasoning") -> Dict[str, Any]:
    """
    根据完整对话历史生成分诊报告。
    """
    system_prompt = """你是一位专业的医生。根据以下的患病主诉和问诊记录（包括患者上传的图片），请生成一份结构化的分诊报告。
请严格按照以下 JSON 格式输出，不要包含 Markdown 格式标记（如 ```json）：
{
    "possible_conditions": ["疾病1", "疾病2"],
    "department": "建议挂号科室",
    "urgency": "紧急程度（普通/建议尽快/急诊）",
    "advice": "具体的医疗建议和注意事项",
    "reasoning_steps": [
        {
            "step": 1,
            "type": "symptom",
            "title": "症状分析",
            "content": "患者主要症状描述"
        },
        {
            "step": 2,
            "type": "analysis",
            "title": "初步分析",
            "content": "基于症状的可能疾病分析"
        },
        {
            "step": 3,
            "type": "conclusion",
            "title": "诊断结论",
            "content": "最终判断和建议科室"
        }
    ],
    "sankey_data": {
        "nodes": [
            {"id": "symptom_1", "name": "症状名称", "layer": 0, "category": "症状", "color": "#ec4899"},
            {"id": "symptom_2", "name": "症状名称", "layer": 0, "category": "症状", "color": "#ec4899"},
            {"id": "symptom_3", "name": "症状名称", "layer": 0, "category": "症状", "color": "#ec4899"},
            {"id": "analysis_1", "name": "症状模式", "layer": 1, "category": "分析", "color": "#ec4899"},
            {"id": "analysis_2", "name": "症状模式", "layer": 1, "category": "分析", "color": "#ec4899"},
            {"id": "analysis_3", "name": "症状模式", "layer": 1, "category": "分析", "color": "#ec4899"},
            {"id": "condition_1", "name": "疾病1", "layer": 2, "category": "疑似患病", "color": "#10b981"},
            {"id": "condition_2", "name": "疾病2", "layer": 2, "category": "疑似患病", "color": "#10b981"}
        ],
        "links": [
            {"source": "symptom_1", "target": "analysis_1", "value": 0.8},
            {"source": "symptom_1", "target": "analysis_2", "value": 0.7},
            {"source": "symptom_2", "target": "analysis_2", "value": 0.9},
            {"source": "symptom_3", "target": "analysis_3", "value": 0.9},
            {"source": "analysis_1", "target": "condition_1", "value": 0.8},
            {"source": "analysis_2", "target": "condition_1", "value": 0.7},
            {"source": "analysis_2", "target": "condition_2", "value": 0.6},
            {"source": "analysis_3", "target": "condition_2", "value": 0.5}
        ]
    }
}

reasoning_steps说明：
- step: 步骤序号
- type: 步骤类型（symptom/analysis/conclusion）
- title: 步骤标题
- content: 该步骤的具体内容
- 通常3-5个步骤即可，按逻辑顺序排列

sankey_data说明：
- nodes: 桑基图节点，包含以下字段：
  * id: 唯一标识符
  * name: 节点显示名称
  * layer: 层级（0=主诉症状，1=分析层，2=疑似患病）
  * category: 节点分类（症状/发病时间/部位/分析/时间分析/部位分析/疑似患病）
  * color: 节点颜色（症状用#ec4899粉色，发病时间用#3b82f6蓝色，部位用#f59e0b橙色，分析层继承对应症状颜色，疑似患病用#10b981绿色）
- links: 节点间的连接，value表示关联强度（0-1之间）
- 确保每个节点的id在nodes中唯一，links中的source和target引用nodes中的id
- 症状应该按类型分类：具体症状描述、发病时间、部位等
- 分析层应该对症状进行提炼和归纳，形成医学术语
- 一个症状可以连接到多个分析结果，一个分析结果可以连接多个疑似疾病
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        content = await _create_chat_completion(
            model=model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        return json.loads(content)
    except Exception as e:
        print(f"Error generating diagnosis: {e}")
        return {
            "possible_conditions": ["生成失败"],
            "department": "未知",
            "urgency": "未知",
            "advice": "系统繁忙，请稍后再试或直接咨询医生。",
            "reasoning": str(e)
        }
