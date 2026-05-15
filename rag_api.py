from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import numpy as np
import requests
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
import asyncio
from fastapi.responses import StreamingResponse

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 配置信息 ====================
EMBEDDING_CONFIG = {
    'api_url': 'https://api.agicto.cn/v1/embeddings',
    'api_key': 'sk-93FPv8WKJLZPPo5DujoHZeUfcY6wEXg1zkMec7PDVBrvPGl5',
    'model': 'text-embedding-v3'
}

DEEPSEEK_CONFIG = {
    'api_key': 'sk-653911d149e9484486110e4e8d826149',
    'model': 'deepseek-chat',
    'api_url': 'https://api.deepseek.com/v1/chat/completions'
}

# ==================== 请求模型 ====================
class ChatRequest(BaseModel):
    messages: list
    stream: Optional[bool] = True

# ==================== 文档加载 ====================
def load_documents_from_file(file_path):
    """从文本文件加载国防知识文档"""
    documents = []
    current_category = ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    current_category = line[1:].strip()
                else:
                    # 将类别信息作为文档前缀
                    documents.append(f"[{current_category}] {line}")
        return documents
    except Exception as e:
        print(f"加载文档失败: {str(e)}")
        return []

# ==================== 嵌入模型调用 ====================
def get_embedding(text):
    """调用第三方text-embedding-v3 API"""
    headers = {
        "Authorization": f"Bearer {EMBEDDING_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": text,
        "model": EMBEDDING_CONFIG['model'],
        "encoding_format": "float"
    }
    
    try:
        response = requests.post(
            EMBEDDING_CONFIG['api_url'],
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return np.array(response.json()['data'][0]['embedding'])
    except Exception as e:
        print(f"嵌入API调用失败: {str(e)}")
        return None

# ==================== 问答模型调用 ====================
def ask_deepseek_stream(prompt):
    """调用DeepSeek问答API（流式）"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_CONFIG['api_key']}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": DEEPSEEK_CONFIG['model'],
        "messages": prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": True
    }
    
    try:
        response = requests.post(
            DEEPSEEK_CONFIG['api_url'],
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )
        
        # 添加详细的错误日志
        if response.status_code != 200:
            error_detail = {
                "status_code": response.status_code,
                "response_text": response.text,
                "request_payload": payload
            }
            print(f"DeepSeek API错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            return None
            
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"DeepSeek API调用失败: {str(e)}")
        return None

# ==================== RAG 核心系统 ====================
class RAGSystem:
    def __init__(self, documents, embedding_cache="embeddings.npy"):
        """初始化RAG系统，支持向量缓存"""
        self.documents = documents
        self.document_embeddings = []
        
        # 尝试加载缓存的向量
        if os.path.exists(embedding_cache):
            try:
                self.document_embeddings = np.load(embedding_cache)
                print(f"从缓存加载了{len(self.document_embeddings)}个文档向量")
                if len(self.document_embeddings) == len(documents):
                    return
                print("文档数量变化，将重新计算向量")
            except:
                print("向量缓存加载失败，将重新计算")
        
        # 预计算所有文档的嵌入向量
        print("正在计算文档嵌入向量...")
        self.document_embeddings = []
        for i, doc in enumerate(documents):
            print(f"处理文档 {i+1}/{len(documents)}...", end='\r')
            emb = get_embedding(doc)
            if emb is not None:
                self.document_embeddings.append(emb)
            else:
                self.document_embeddings.append(np.zeros(1536))
        
        # 保存向量缓存
        np.save(embedding_cache, np.array(self.document_embeddings))
        print(f"\n已计算并缓存 {len(self.document_embeddings)}/{len(documents)} 个文档嵌入")

    def retrieve(self, query, top_k=3, similarity_threshold=0.7):
        """检索最相关的文档，增加相似度阈值"""
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return []
        
        similarities = cosine_similarity(
            [query_embedding],
            self.document_embeddings
        )[0]
        
        # 获取top_k结果并过滤低相似度文档
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [
            (self.documents[i], similarities[i]) 
            for i in top_indices 
            if similarities[i] > similarity_threshold
        ]

    def generate_prompt(self, query, context=None):
        """生成更专业的提示词模板"""
        system_prompt = """你是一名国防军事专家，负责回答用户关于国防、军事和国家安全的问题。请遵循以下要求：

1. 回答必须专业、准确、权威
2. 使用规范的军事术语和表达方式
3. 回答结构清晰，逻辑严谨
4. 如果提供了参考资料，必须基于参考资料回答
5. 避免使用Markdown或其他格式化符号
6. 回答格式：
   - 直接答案（简明扼要）
   - 详细解释（分点阐述）
   - 相关背景（如有必要）"""

        if context:
            user_prompt = f"""【参考资料】
{context}

【用户问题】
{query}

请根据以上资料，按照要求给出专业回答："""
        else:
            user_prompt = f"""【用户问题】
{query}

请根据你的专业知识，按照要求给出回答："""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

# 初始化RAG系统
KNOWLEDGE_FILE = "defense_knowledge.txt"
print(f"正在从 {KNOWLEDGE_FILE} 加载国防知识文档...")
documents = load_documents_from_file(KNOWLEDGE_FILE)
if not documents:
    print("警告: 未加载到任何文档，使用示例文档代替")
    documents = [
        "[军事历史] 南昌起义发生于1927年8月1日，是中国共产党独立领导武装斗争的开始",
        "[武器装备] 歼-20是中国自主研制的第五代隐形战斗机，2017年正式列装空军作战部队"
    ]

rag = RAGSystem(documents)

# ==================== API端点 ====================
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    # 获取用户最后一条消息
    user_message = None
    for msg in reversed(request.messages):
        if msg.get('role') == 'user':
            user_message = msg
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    question = user_message['content']
    
    try:
        # 检索相关文档
        relevant_docs = rag.retrieve(question)
        context = "\n".join([f"• {doc}" for doc, _ in relevant_docs]) if relevant_docs else None
        
        # 生成提示词
        messages = rag.generate_prompt(question, context)
        
        # 添加用户问题
        messages.append({"role": "user", "content": question})
        
        # 流式响应
        if request.stream:
            response = ask_deepseek_stream(messages)
            if not response:
                raise HTTPException(
                    status_code=502,
                    detail="无法连接到AI服务，请检查API密钥或稍后再试"
                )
            
            async def generate():
                try:
                    for chunk in response.iter_lines():
                        if chunk:
                            decoded_chunk = chunk.decode('utf-8')
                            if decoded_chunk.startswith('data: '):
                                yield decoded_chunk + "\n\n"
                except Exception as e:
                    print(f"流式响应生成错误: {str(e)}")
                    yield 'data: {"error": "流式响应中断"}\n\n'
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            raise HTTPException(status_code=400, detail="Only streaming is supported")
    except Exception as e:
        print(f"处理请求时出错: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)