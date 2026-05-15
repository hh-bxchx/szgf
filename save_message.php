<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 获取POST数据
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if ($data) {
        // 格式化留言内容
        $message = "姓名: " . $data['姓名'] . "\n";
        $message .= "邮箱: " . $data['邮箱'] . "\n";
        $message .= "留言内容: " . $data['留言内容'] . "\n";
        $message .= "提交时间: " . $data['提交时间'] . "\n";
        $message .= "----------------------------------------\n\n";
        
        // 写入txt文件
        $filename = 'tila_messages.txt';
        $result = file_put_contents($filename, $message, FILE_APPEND | LOCK_EX);
        
        if ($result !== false) {
            echo json_encode(['success' => true, 'message' => '留言保存成功']);
        } else {
            http_response_code(500);
            echo json_encode(['success' => false, 'message' => '文件写入失败']);
        }
    } else {
        http_response_code(400);
        echo json_encode(['success' => false, 'message' => '数据格式错误']);
    }
} else {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => '不支持的请求方法']);
}
?>