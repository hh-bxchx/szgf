<?php
/**
 * 战略决策游戏 - AI决策API
 * 调用讯飞星火AI接口为游戏提供AI决策
 */

// ==================== 配置部分 ====================

// 讯飞星火AI API配置
define('SPARK_API_KEY', 'Bearer tSGkgLMSJXNLYxDbRHnL:izrOmhTtutnVZbMzgcpV'); // 请替换为您的实际API密钥
define('SPARK_API_URL', 'https://spark-api-open.xf-yun.com/v2/chat/completions');

// API请求配置
define('API_TIMEOUT', 30); // API请求超时时间（秒）
define('API_MAX_TOKENS', 100); // 最大token数
define('API_TEMPERATURE', 0.7); // 温度参数，控制创造性

// 游戏配置
define('MAX_LOG_LENGTH', 1000); // 最大日志长度
define('ENABLE_DEBUG_LOG', true); // 是否启用调试日志

// 安全配置
define('ALLOWED_ORIGINS', [
    'http://localhost',
    'https://localhost',
    'http://127.0.0.1',
    'https://127.0.0.1'
    // 添加您的域名
]);

// 速率限制配置（可选实现）
define('RATE_LIMIT_REQUESTS', 60); // 每分钟最大请求数
define('RATE_LIMIT_WINDOW', 60); // 时间窗口（秒）

/**
 * 获取API密钥的函数
 * 支持从环境变量或配置文件读取
 */
function getApiKey() {
    // 优先从环境变量读取（更安全）
    $envKey = getenv('SPARK_API_KEY');
    if ($envKey !== false && !empty($envKey)) {
        return $envKey;
    }
    
    // 从配置常量读取
    return SPARK_API_KEY;
}

/**
 * 检查API密钥是否已配置
 */
function checkApiKeyConfigured() {
    $apiKey = getApiKey();
    return $apiKey !== 'Bearer YOUR_API_KEY_HERE' && !empty($apiKey);
}

/**
 * 记录调试日志
 */
function debugLog($message) {
    if (ENABLE_DEBUG_LOG) {
        $timestamp = date('Y-m-d H:i:s');
        error_log("[{$timestamp}] Strategy Game: {$message}");
    }
}

/**
 * 检查请求来源是否被允许
 */
function checkOrigin() {
    if (isset($_SERVER['HTTP_ORIGIN'])) {
        $origin = $_SERVER['HTTP_ORIGIN'];
        if (!in_array($origin, ALLOWED_ORIGINS)) {
            // 在生产环境中，您可能想要更严格的来源检查
            // 目前允许所有来源，便于本地开发
            // return false;
        }
    }
    return true;
}

/**
 * 应用环境检测
 */
function getEnvironment() {
    if (isset($_SERVER['HTTP_HOST'])) {
        $host = $_SERVER['HTTP_HOST'];
        if (strpos($host, 'localhost') !== false || strpos($host, '127.0.0.1') !== false) {
            return 'development';
        }
    }
    return 'production';
}

// 错误处理配置
if (getEnvironment() === 'development') {
    ini_set('display_errors', 1);
    ini_set('display_startup_errors', 1);
    error_reporting(E_ALL);
} else {
    ini_set('display_errors', 0);
    ini_set('display_startup_errors', 0);
    error_reporting(E_ERROR | E_WARNING | E_PARSE);
}

// ==================== API处理部分 ====================

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// 只接受POST请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => '只支持POST请求']);
    exit;
}

// 检查API密钥是否已配置
if (!checkApiKeyConfigured()) {
    http_response_code(500);
    echo json_encode([
        'error' => 'API密钥未配置，请在config.php中设置您的讯飞星火API密钥',
        'config_help' => '请将config.php中的YOUR_API_KEY_HERE替换为您的实际API密钥'
    ]);
    exit;
}

// 检查请求来源（可选）
if (!checkOrigin()) {
    http_response_code(403);
    echo json_encode(['error' => '不允许的请求来源']);
    exit;
}

/**
 * 调用讯飞星火AI API
 */
function callSparkAI($prompt) {
    $headers = [
        'Authorization: ' . getApiKey(),
        'Content-Type: application/json'
    ];
    
    $data = [
        'model' => 'x1',
        'user' => 'strategy_game_user',
        'messages' => [
            [
                'role' => 'user',
                'content' => $prompt
            ]
        ],
        'stream' => false, // 设为false，使用非流式响应，便于处理
        'temperature' => API_TEMPERATURE,
        'max_tokens' => API_MAX_TOKENS
    ];
    
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => SPARK_API_URL,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($data),
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_TIMEOUT => API_TIMEOUT,
        CURLOPT_SSL_VERIFYPEER => false, // 生产环境建议设为true
        CURLOPT_FOLLOWLOCATION => true
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);
    
    if ($curlError) {
        throw new Exception("CURL错误: " . $curlError);
    }
    
    if ($httpCode !== 200) {
        throw new Exception("API请求失败，HTTP状态码: " . $httpCode . "，响应: " . $response);
    }
    
    $responseData = json_decode($response, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new Exception("响应JSON解析失败: " . json_last_error_msg());
    }
    
    if (!isset($responseData['choices'][0]['message']['content'])) {
        throw new Exception("API响应格式异常: " . json_encode($responseData));
    }
    
    return $responseData['choices'][0]['message']['content'];
}

/**
 * 流式调用讯飞星火AI API（备用方案）
 */
function callSparkAIStream($prompt) {
    $headers = [
        'Authorization: ' . getApiKey(),
        'Content-Type: application/json'
    ];
    
    $data = [
        'model' => 'x1',
        'user' => 'strategy_game_user',
        'messages' => [
            [
                'role' => 'user',
                'content' => $prompt
            ]
        ],
        'stream' => true,
        'temperature' => API_TEMPERATURE,
        'max_tokens' => API_MAX_TOKENS
    ];
    
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => SPARK_API_URL,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($data),
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_TIMEOUT => API_TIMEOUT,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_FOLLOWLOCATION => true
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);
    
    if ($curlError) {
        throw new Exception("CURL错误: " . $curlError);
    }
    
    if ($httpCode !== 200) {
        throw new Exception("API请求失败，HTTP状态码: " . $httpCode);
    }
    
    // 处理流式响应
    $lines = explode("\n", $response);
    $content = '';
    
    foreach ($lines as $line) {
        $line = trim($line);
        if (strpos($line, 'data: ') === 0 && $line !== 'data: [DONE]') {
            $jsonData = substr($line, 6); // 移除 "data: " 前缀
            $data = json_decode($jsonData, true);
            
            if (isset($data['choices'][0]['delta']['content'])) {
                $content .= $data['choices'][0]['delta']['content'];
            }
        }
    }
    
    return $content;
}

// 主处理逻辑
try {
    // 获取请求数据
    $input = file_get_contents('php://input');
    if (empty($input)) {
        throw new Exception('请求数据为空');
    }
    
    $requestData = json_decode($input, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new Exception('请求JSON格式错误: ' . json_last_error_msg());
    }
    
    if (!isset($requestData['prompt']) || empty(trim($requestData['prompt']))) {
        throw new Exception('prompt参数为空或缺失');
    }
    
    $prompt = trim($requestData['prompt']);
    
    // 记录请求日志
    debugLog("收到AI决策请求: " . substr($prompt, 0, 100) . "...");
    
    // 调用AI API
    $startTime = microtime(true);
    $aiResponse = callSparkAI($prompt);
    $endTime = microtime(true);
    $duration = round(($endTime - $startTime) * 1000, 2); // 毫秒
    
    // 清理响应内容
    $aiResponse = trim($aiResponse);
    
    // 记录响应日志
    debugLog("AI响应 (耗时{$duration}ms): " . $aiResponse);
    
    // 返回结果
    echo json_encode([
        'success' => true,
        'content' => $aiResponse,
        'duration_ms' => $duration,
        'timestamp' => date('Y-m-d H:i:s')
    ], JSON_UNESCAPED_UNICODE);
    
} catch (Exception $e) {
    // 错误处理
    debugLog("错误: " . $e->getMessage());
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage(),
        'timestamp' => date('Y-m-d H:i:s')
    ], JSON_UNESCAPED_UNICODE);
}
?>