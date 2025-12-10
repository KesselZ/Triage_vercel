import os
from typing import List, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("UNIAPI_API_KEY")
BASE_URL = os.getenv("UNIAPI_BASE_URL", "https://hk.uniapi.io/v1")

# 与 test.py 一致：使用 uniapi 的 OpenAI 兼容接口
client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# 模型配置：问诊阶段和诊断阶段使用不同模型
CHAT_MODEL_NAME = "gpt-5.1"  # 问诊阶段模型
DIAGNOSIS_MODEL_NAME = "grok-4-1-fast-reasoning"  # 诊断阶段模型

async def get_next_question(history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    根据对话历史，决定是继续提问还是停止。
    返回: {"status": "continue", "question": "问题内容", "options": ["选项1", "选项2"]} 
         或 {"status": "continue", "question": "问题内容"} (无选项)
         或 {"status": "stop"}
    """
    
    system_prompt = """你是一位温暖贴心的三甲医院分诊医生助手。你的任务是通过询问患者症状来收集信息，以便进行初步分诊。

请用关怀、温暖的语气与患者交流，就像一位真正关心患者健康的医生。

规则：
1. 每次只问**一个**最关键的补充问题。
2. 根据可能的相关多种疾病，解析症状，为病人提供可选择的症状列表进行确认。
3. 选择项应该简洁明了，4-6个选项为宜，包括常见相关症状。
4. 如果问题不适合提供选项（如需要详细描述），可以只返回问题文本。
5. 如果你认为当前收集的信息已经足够判断大概的疾病方向和挂号科室，请直接回复 "STOP_ASKING"。
6. 严禁在此时给出诊断结果，只负责提问。
7. 语气要求：
   - 用温暖关怀的语气，像医生关心患者一样交流
   - 多用理解和共情的表达，让患者感到被重视
   - 语言自然流畅，避免机械化和模板化
   - 可以适当使用一些温和的语气词，但不要过度

输出格式：
- 如果需要继续提问且提供选项：{"question": "问题内容", "options": ["选项1", "选项2", "选项3"]}
- 如果需要继续提问但不提供选项：{"question": "问题内容"}
- 如果信息足够：{"status": "stop"}

请严格按照JSON格式输出，不要包含任何markdown标记。"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        response = await client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        
        import json
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

async def generate_diagnosis(history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    根据完整对话历史生成分诊报告。
    """
    system_prompt = """你是一位专业的医生。根据以下的患病主诉和问诊记录，请生成一份结构化的分诊报告。
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
    ]
}

reasoning_steps说明：
- step: 步骤序号
- type: 步骤类型（symptom/analysis/conclusion）
- title: 步骤标题
- content: 该步骤的具体内容
- 通常3-5个步骤即可，按逻辑顺序排列
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        response = await client.chat.completions.create(
            model=DIAGNOSIS_MODEL_NAME,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        import json
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
