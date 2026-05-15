<?php
// 讯飞API PHP代理服务
// 文件名：xunfei_api_proxy.php

// 设置CORS跨域头
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
header("Content-Type: application/json; charset=utf-8");

// 处理OPTIONS预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// 只允许POST请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => '只允许POST请求']);
    exit;
}

// 配置讯飞API参数
$API_URL = 'https://spark-api-open.xf-yun.com/v1/chat/completions';
$API_KEY = 'RkkhELwFmBrjrfAgjZiZ:sUGtkqGyQUiSfSzaEQQJ'; // 请替换为您的真实API Key


// 获取前端发送的数据
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    http_response_code(400);
    echo json_encode(['error' => '无效的JSON数据']);
    exit;
}

// 构建请求参数
$requestData = [
    'model' => '4.0Ultra',
    'messages' => $data['messages'] ?? [],
    'stream' => true,
    'user' => 'user_id',
    'tools' => [
        [
            'type' => 'web_search',
            'web_search' => [
                'enable' => true
            ]
        ]
    ]
];

// 设置请求头
$headers = [
    'Content-Type: application/json',
    'Authorization: Bearer ' . $API_KEY
];

// 初始化cURL
$ch = curl_init();

curl_setopt_array($ch, [
    CURLOPT_URL => $API_URL,
    CURLOPT_RETURNTRANSFER => false,
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => json_encode($requestData),
    CURLOPT_HTTPHEADER => $headers,
    CURLOPT_WRITEFUNCTION => 'handleStreamData',
    CURLOPT_TIMEOUT => 60,
    CURLOPT_SSL_VERIFYPEER => false,
    CURLOPT_SSL_VERIFYHOST => false
]);

// 流式数据处理函数
function handleStreamData($ch, $data) {
    // 将数据直接输出到浏览器
    echo $data;
    
    // 强制刷新输出缓冲区
    if (ob_get_level()) {
        ob_flush();
    }
    flush();
    
    return strlen($data);
}

// 设置流式输出
if (ob_get_level()) {
    ob_end_clean();
}

// 执行请求
$response = curl_exec($ch);

// 检查错误
if ($response === false) {
    $error = curl_error($ch);
    curl_close($ch);
    
    http_response_code(500);
    echo json_encode(['error' => 'API请求失败: ' . $error]);
    exit;
}

// 获取HTTP状态码
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

// 如果状态码不是200，说明出错了
if ($httpCode !== 200) {
    http_response_code($httpCode);
    echo json_encode(['error' => 'API返回错误，状态码: ' . $httpCode]);
}
?>