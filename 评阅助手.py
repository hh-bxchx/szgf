from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from collections import deque

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key="sk-653911d149e9484486110e4e8d826149",
    base_url="https://api.deepseek.com"
)

# 定义记忆存储（简单实现）
class AgentMemory:
    def __init__(self, max_size=5):
        self.memory = deque(maxlen=max_size)
    
    def add(self, item: str):
        self.memory.append(item)
    
    def get_context(self) -> str:
        return "\n".join(self.memory) if self.memory else "无历史记录"

memory = AgentMemory()

# 定义请求模型
class WrongQuestionsRequest(BaseModel):
    wrong_questions: List[Dict[str, Any]]
    student_id: Optional[str] = None  # 可选学生ID，用于个性化

class OriginalQuestionRequest(BaseModel):
    original_question: Dict[str, Any]
    difficulty: Optional[str] = "中等"  # 可选难度调整

# 错题解析Agent
@app.post("/analyze_wrong_questions")
async def analyze_wrong_questions(request: WrongQuestionsRequest):
    """带记忆的错题分析Agent"""
    try:
        # 构建带记忆上下文的提示词
        context = f"学生{request.student_id}的" if request.student_id else ""
        memory_context = f"\n历史分析摘要:\n{memory.get_context()}" if memory.get_context() != "无历史记录" else ""
        
        prompt = f"""
        你是一个智能教学Agent，请分析{context}以下错题：
        1. 指出主要错误类型
        2. 给出3条具体建议
        3. 推荐重点复习内容
        {memory_context}
        请用中文回答，保持简洁专业。
        """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(request.wrong_questions, ensure_ascii=False)}
            ]
        )
        
        analysis = response.choices[0].message.content
        memory.add(f"分析摘要: {analysis[:100]}...")  # 存储简要记忆
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 错题重练Agent
@app.post("/generate_similar_question")
async def generate_similar_question(request: OriginalQuestionRequest):
    """带自适应能力的题目生成Agent"""
    try:
        # 自适应提示词
        prompt = f"""
        作为智能题目生成Agent，请基于以下要求生成题目：
        1. 知识点: 与原题相同
        2. 难度: {request.difficulty}
        3. 格式: 必须返回有效JSON
        4. 创新性: 改变题目情境但保持考察点
        
        示例格式:
        {{
            "text": "问题文本",
            "options": ["A...", "B...", "C...", "D..."],
            "correct": 0,
            "explanation": "解析说明",
            "difficulty": "{request.difficulty}"
        }}
        """
        
        # 自动重试机制
        for attempt in range(3):
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(request.original_question, ensure_ascii=False)}
                ]
            )
            
            content = response.choices[0].message.content
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                question = json.loads(content)
                # 验证必要字段
                if all(key in question for key in ["text", "options", "correct", "explanation"]):
                    return {"status": "success", "question": question}
            except:
                continue  # 自动重试
        
        raise ValueError("无法生成有效题目")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6000)