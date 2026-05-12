<?php
require_once 'facebookAutoPoster.php';


// EX1 - Phương pháp thủ công
$poster = new FacebookAutoPoster([
    'page_id' => 'PAGE_ID',
    'page_access_token' => 'PAGE_ACCESS_TOKEN',
    'ai_use' => 2, // 1 = AI, 2 = thủ công
    'image_folder' => '/images/',
    'caption_file' => '/captions.json'
]);

$result = $poster->post();

// Ghi log kết quả
file_put_contents('./logs/cron.log', 
    date('Y-m-d H:i:s') . ' - ' . json_encode($result) . PHP_EOL, 
    FILE_APPEND
);




// EX2 - Phương pháp AI
try {
    $ai_cron_poster = new FacebookAutoPoster([
        'page_id' => 'PAGE_ID',
        'page_access_token' => 'PAGE_ACCESS_TOKEN',
        'ai_use' => 1,
        'gemini_api_key' => 'GEMINI_KEY'
    ]);
    
    // câu lệnh
    $prompts = [
        'Cảnh sương mù buổi sáng thanh bình trên hồ',
        'Bữa sáng tươi mát và tốt cho sức khỏe với trái cây và sinh tố',
        'Nội thất văn phòng hiện đại với ánh sáng tự nhiên',
        'Góc đọc sách ấm cúng với nhiều sách và ánh sáng dịu nhẹ',
        'Khung cảnh tạo động lực tập luyện với các dụng cụ thể hình'
    ];
    
    // Chọn một câu lệnh ngẫu nhiên
    $random_prompt = $prompts[array_rand($prompts)];
    
    $result = $ai_cron_poster->post([
        'post_type' => 'image_caption',
        'prompt' => $random_prompt
    ]);
    
    if ($result['status'] == 'success') {
        echo "✅ Đăng bài thành công! ID Bài viết: " . $result['post_id'] . "\n";
    }
} catch (Exception $e) {
    echo "Lỗi: " . $e->getMessage() . "\n";
}

?>