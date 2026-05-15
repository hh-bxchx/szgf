import time
import requests
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
import hashlib
import base64
import hmac
from urllib.parse import urlencode
import json
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

# 讯飞embedding API配置
XUNFEI_CONFIG = {
    'APPID': '223211d3',  # 请替换为您的APPID
    'APISecret': 'OTk4YzgzMDljNmM1ZjA5Yzk2YjZiNGE4',  # 请替换为您的APISecret
    'APIKEY': '1add55ee4caebfff2bbeba14ba7d582f'  # 请替换为您的APIKEY
}

class AssembleHeaderException(Exception):
    def __init__(self, msg):
        self.message = msg

class Url:
    def __init__(self, host, path, schema):
        self.host = host
        self.path = path
        self.schema = schema

def sha256base64(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    digest = base64.b64encode(sha256.digest()).decode(encoding='utf-8')
    return digest

def parse_url(requset_url):
    stidx = requset_url.index("://")
    host = requset_url[stidx + 3:]
    schema = requset_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException("invalid request url:" + requset_url)
    path = host[edidx:]
    host = host[:edidx]
    u = Url(host, path, schema)
    return u

def assemble_ws_auth_url(requset_url, method="GET", api_key="", api_secret=""):
    u = parse_url(requset_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return requset_url + "?" + urlencode(values)

def get_Body(appid, text, style):
    body = {
        "header": {
            "app_id": appid,
            "uid": "39769795890",
            "status": 3
        },
        "parameter": {
            "emb": {
                "domain": style,
                "feature": {
                    "encoding": "utf8"
                }
            }
        },
        "payload": {
            "messages": {
                "text": base64.b64encode(json.dumps(text).encode('utf-8')).decode()
            }
        }
    }
    return body

def get_xunfei_embedding(text, style="para"):
    """获取讯飞embedding向量"""
    host = 'https://emb-cn-huabei-1.xf-yun.com/'
    url = assemble_ws_auth_url(host, method='POST', 
                              api_key=XUNFEI_CONFIG['APIKEY'], 
                              api_secret=XUNFEI_CONFIG['APISecret'])
    
    # 构造请求数据
    text_data = {"messages": [{"content": text, "role": "user"}]}
    content = get_Body(XUNFEI_CONFIG['APPID'], text_data, style)
    
    try:
        response = requests.post(url, json=content, headers={'content-type': "application/json"})
        result = parser_Message(response.text)
        return result
    except Exception as e:
        print(f"获取embedding失败: {e}")
        return None

def parser_Message(message):
    """解析讯飞API返回的embedding结果"""
    try:
        data = json.loads(message)
        code = data['header']['code']
        if code != 0:
            print(f'请求错误: {code}, {data}')
            return None
        else:
            text_base = data["payload"]["feature"]["text"]
            text_data = base64.b64decode(text_base)
            dt = np.dtype(np.float32)
            dt = dt.newbyteorder("<")
            text = np.frombuffer(text_data, dtype=dt)
            return text
    except Exception as e:
        print(f"解析embedding结果失败: {e}")
        return None

# 完整资源数据
resource_data = [
    # 四渡赤水视频
    {
        "id": 1, "title": "沙盘推演：四渡赤水（上）史上最详细拆解长征最秀一役", "type": "video",
        "url": "https://www.bilibili.com/video/BV18A411e7Qj/", "thumbnail": "",
        "tags": ["四渡赤水", "红军", "长征", "战略分析", "毛泽东"],
        "description": "通过沙盘推演详细解析四渡赤水战役，展示红军灵活机动的战略战术",
        "text": "沙盘推演：四渡赤水（上）史上最详细拆解长征最秀一役 四渡赤水 红军 长征 战略分析 毛泽东"
    },
    {
        "id": 2, "title": "沙盘推演：四渡赤水（下）史上最详细拆解长征最秀一役", "type": "video",
        "url": "https://www.bilibili.com/video/BV1SD4y1S7PE/", "thumbnail": "",
        "tags": ["四渡赤水", "红军", "长征", "战役复盘", "军事指挥"],
        "description": "继续深入分析四渡赤水战役的决策过程和战术执行，展现红军高超的作战艺术",
        "text": "沙盘推演：四渡赤水（下）史上最详细拆解长征最秀一役 四渡赤水 红军 长征 战役复盘 军事指挥"
    },
    # 抗美援朝视频
    {
        "id": 3, "title": "上甘岭", "type": "video",
        "url": "https://www.bilibili.com/bangumi/play/ep313063?theme=movie&spm_id_from=333.337.0.0", "thumbnail": "",
        "tags": ["抗美援朝", "上甘岭战役", "战争电影", "历史重现"],
        "description": "经典抗美援朝战争电影，展现志愿军战士的英勇顽强",
        "text": "上甘岭 抗美援朝 上甘岭战役 战争电影 历史重现"
    },
    {
        "id": 4, "title": "抗美援朝究竟是怎么打的？全景式回顾立国之战！", "type": "video",
        "url": "https://www.bilibili.com/video/BV16v411k7Sx/", "thumbnail": "",
        "tags": ["抗美援朝", "全景回顾", "战争史", "志愿军", "立国之战"],
        "description": "全面回顾抗美援朝战争全过程，分析战争背景、重要战役和历史意义",
        "text": "抗美援朝究竟是怎么打的？全景式回顾立国之战！ 抗美援朝 全景回顾 战争史 志愿军 立国之战"
    },
    # 抗日战争视频
    {
        "id": 5, "title": "20分钟全方位回顾抗日战争", "type": "video",
        "url": "https://www.bilibili.com/video/BV1Fx411b7NR/", "thumbnail": "",
        "tags": ["抗日战争", "全面抗战", "历史回顾", "中华民族", "战争史"],
        "description": "浓缩抗日战争重要事件，展现中华民族不屈不挠的抗战精神",
        "text": "20分钟全方位回顾抗日战争 抗日战争 全面抗战 历史回顾 中华民族 战争史"
    },
    {
        "id": 6, "title": "一个日本人如何参加抗战？", "type": "video",
        "url": "https://www.bilibili.com/video/BV1634y1s7GC/", "thumbnail": "",
        "tags": ["抗日战争", "国际友人", "历史故事", "中日关系"],
        "description": "讲述日本友人参与中国抗战的感人故事，展现人道主义精神",
        "text": "一个日本人如何参加抗战？ 抗日战争 国际友人 历史故事 中日关系"
    },
    # 四渡赤水文档
    {
        "id": 7, "title": "红军四渡赤水路线图", "type": "doc",
        "url": "docs/sdcs-analysis.jpg", "thumbnail": "",
        "tags": ["四渡赤水", "路线图", "军事地图", "红军", "长征"],
        "description": "详细标注红军四渡赤水的行军路线和重要战役地点的高清地图",
        "text": "红军四渡赤水路线图 四渡赤水 路线图 军事地图 红军 长征"
    },
    {
        "id": 8, "title": "毛泽东在四渡赤水战役指挥中的关键作用", "type": "doc",
        "url": "docs/毛泽东在四渡赤水战役指挥中的关键作用.pdf", "thumbnail": "",
        "tags": ["毛泽东", "四渡赤水", "军事指挥", "战略思想", "红军"],
        "description": "分析毛泽东在四渡赤水战役中的指挥艺术和战略决策，探讨其军事思想",
        "text": "毛泽东在四渡赤水战役指挥中的关键作用 毛泽东 四渡赤水 军事指挥 战略思想 红军"
    },
    # 抗美援朝文档
    {
        "id": 9, "title": "抗美援朝战争中志愿军的坑道战研究", "type": "doc",
        "url": "docs/抗美援朝战争中志愿军的坑道战研究.pdf", "thumbnail": "",
        "tags": ["抗美援朝", "坑道战", "战术研究", "志愿军", "战争史"],
        "description": "深入分析志愿军在抗美援朝战争中创造的坑道战术及其实战效果",
        "text": "抗美援朝战争中志愿军的坑道战研究 抗美援朝 坑道战 战术研究 志愿军 战争史"
    },
    # 抗日战争文档
    {
        "id": 10, "title": "《不能忘却的记忆--32位抗战老兵口述史》", "type": "doc",
        "url": "docs/《不能忘却的记忆--32位抗战老兵口述史》.pdf", "thumbnail": "",
        "tags": ["抗日战争", "口述历史", "老兵回忆", "历史资料"],
        "description": "收录32位抗战老兵的口述历史，真实还原抗战时期的艰苦岁月",
        "text": "《不能忘却的记忆--32位抗战老兵口述史》 抗日战争 口述历史 老兵回忆 历史资料"
    },
    # 更多文档资源
    {
        "id": 11, "title": "抗日战争中的游击战术研究", "type": "doc",
        "url": "docs/抗日战争中的游击战术研究.pdf", "thumbnail": "",
        "tags": ["抗日战争", "游击战术", "军事策略", "敌后作战"],
        "description": "深入分析抗日战争期间使用的游击战术及其战略意义",
        "text": "抗日战争中的游击战术研究 抗日战争 游击战术 军事策略 敌后作战"
    },
    {
        "id": 12, "title": "抗美援朝战争中的后勤保障体系", "type": "doc",
        "url": "docs/抗美援朝战争中的后勤保障体系.pdf", "thumbnail": "",
        "tags": ["抗美援朝", "后勤保障", "战争史", "军事后勤"],
        "description": "研究抗美援朝战争中志愿军的后勤保障体系及其运作机制",
        "text": "抗美援朝战争中的后勤保障体系 抗美援朝 后勤保障 战争史 军事后勤"
    }
]

# 全局变量存储预计算的嵌入向量
resource_embeddings = []
embedding_initialized = False

def initialize_embeddings():
    """预计算所有资源的嵌入向量"""
    global resource_embeddings, embedding_initialized
    
    if embedding_initialized:
        return True
        
    print("正在使用讯飞embedding API预计算资源嵌入向量...")
    
    try:
        resource_embeddings = []
        for i, resource in enumerate(resource_data):
            print(f"正在处理资源 {i+1}/{len(resource_data)}: {resource['title']}")
            embedding = get_xunfei_embedding(resource["text"], style="para")
            
            if embedding is not None:
                resource_embeddings.append(embedding)
                print(f"成功获取嵌入向量，维度: {len(embedding)}")
            else:
                print(f"获取嵌入向量失败，跳过资源: {resource['title']}")
                # 创建一个零向量作为占位符
                resource_embeddings.append(np.zeros(1024))  # 假设嵌入维度为1024
            
            # 添加延迟避免API限流
            time.sleep(0.1)
        
        embedding_initialized = True
        print(f"成功预计算了{len(resource_embeddings)}个资源的嵌入向量")
        return True
        
    except Exception as e:
        print(f"初始化嵌入向量失败: {e}")
        return False

@app.route('/recommend', methods=['POST'])
def recommend():
    global embedding_initialized
    
    # 确保嵌入向量已初始化
    if not embedding_initialized:
        if not initialize_embeddings():
            return jsonify({"error": "嵌入服务初始化失败"}), 500
    
    data = request.json
    query = data['query']
    
    # 获取查询文本的嵌入向量
    print(f"正在处理查询: {query}")
    query_embedding = get_xunfei_embedding(query, style="query")
    
    if query_embedding is None:
        return jsonify({"error": "查询嵌入获取失败"}), 500
    
    # 计算查询与所有资源的余弦相似度
    similarities = []
    for i, resource_embedding in enumerate(resource_embeddings):
        try:
            # 确保两个向量都是有效的
            if resource_embedding is not None and len(resource_embedding) > 0:
                sim = cosine_similarity([query_embedding], [resource_embedding])[0][0]
                similarities.append((i, sim))
            else:
                similarities.append((i, 0.0))
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            similarities.append((i, 0.0))
    
    # 按相似度排序并获取前10个结果
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_results = similarities[:10]
    
    # 归一化处理（使最高分为1.0）
    max_score = top_results[0][1] if top_results and top_results[0][1] > 0 else 1
    normalized_results = []
    for idx, score in top_results:
        normalized_score = score / max_score if max_score > 0 else 0
        normalized_results.append((idx, normalized_score))
    
    # 构建响应数据
    results = []
    for idx, score in normalized_results:
        resource = resource_data[idx]
        results.append({
            "id": resource["id"],
            "title": resource["title"],
            "type": resource["type"],
            "matchScore": float(score),
            "description": resource["description"],
            "tags": resource["tags"],
            "url": resource["url"],
            "thumbnail": resource.get("thumbnail", "")
        })
    
    return jsonify(results)

@app.route('/status', methods=['GET'])
def status():
    global embedding_initialized
    
    # 如果还未初始化，尝试初始化
    if not embedding_initialized:
        initialize_embeddings()
    
    return jsonify({
        "status": "active" if embedding_initialized else "initializing",
        "model": "讯飞embedding模型",
        "resources": len(resource_data),
        "embeddings_ready": embedding_initialized,
        "message": "讯飞embedding推荐系统已就绪" if embedding_initialized else "正在初始化embedding向量..."
    })

@app.route('/init_embeddings', methods=['POST'])
def init_embeddings():
    """手动触发嵌入向量初始化"""
    success = initialize_embeddings()
    return jsonify({
        "success": success,
        "message": "嵌入向量初始化成功" if success else "嵌入向量初始化失败"
    })

if __name__ == '__main__':
    print("启动讯飞embedding推荐服务...")
    print("注意：请确保已正确配置讯飞API密钥")
    
    # 启动时不立即初始化嵌入向量，而是在第一次请求时初始化
    app.run(host='0.0.0.0', port=5000, debug=True)