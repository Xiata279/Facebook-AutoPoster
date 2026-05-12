<?php

/**
 * Facebook Auto Poster - Ví dụ sử dụng
 */

// Nạp thư viện
require_once 'facebookAutoPoster.php';

// Cấu hình
$config = [
    'page_id' => 'PAGE_ID',
    'page_access_token' => 'PAGE_ACCESS_TOKEN',
    'image_folder' => './images/',
    'caption_file' => './captions.json',
    'ai_use' => 2, // 1 = AI, 2 = thủ công
    'gemini_api_key' => 'GEMINI_API_KEY', // Chỉ bắt buộc đối với chế độ AI
    'log_file' => './logs/facebook_poster.log',
    'facebook_api_version' => 'v20.0',
    'max_retries' => 3,
    'retry_delay' => 2 // giây
];

// ===== EX1: Phương pháp thủ công =====

// Lưu ý: Sau khi đăng thành công, tệp hình ảnh sẽ bị XÓA và chú thích sẽ tự động bị GỠ khỏi file JSON

$config['ai_use'] = 2;
$poster = new FacebookAutoPoster($config);
$result = $poster->post();
echo "Kết quả : " . json_encode($result, JSON_PRETTY_PRINT) . "\n\n";



// ===== EX2: Phương pháp AI =====

// QUAN TRỌNG: Chế độ AI hiện sử dụng MỘT câu lệnh (prompt) DUY NHẤT cho cả hình ảnh và chú thích
// AI sẽ tạo ra hình ảnh dựa trên câu lệnh của bạn, sau đó tạo chú thích phù hợp để mô tả bức ảnh được tạo ra

$config['ai_use'] = 1;
$ai_poster = new FacebookAutoPoster($config);



// Tạo hình ảnh và chú thích bằng AI (ĐƯỢC KHUYÊN DÙNG)
$result = $ai_poster->post([
    'post_type' => 'image_caption',
    'prompt' => 'Một hoàng hôn tuyệt đẹp trên núi với những sắc cam và tím rực rỡ'
]);
echo "Kết quả Ảnh+Chú thích AI: " . json_encode($result, JSON_PRETTY_PRINT) . "\n\n";



// Chỉ tạo chú thích bằng AI (không hình ảnh)
$result = $ai_poster->post([
    'post_type' => 'caption_only',
    'prompt' => 'Một câu nói truyền cảm hứng về thành công và sự kiên trì trong kinh doanh'
]);
echo "Kết quả Chỉ Chú thích AI: " . json_encode($result, JSON_PRETTY_PRINT) . "\n\n";



// Chỉ tạo hình ảnh bằng AI (không chú thích)
$result = $ai_poster->post([
    'post_type' => 'image_only',
    'prompt' => 'Nghệ thuật hình học trừu tượng với màu sắc tươi sáng và thiết kế hiện đại'
]);
echo "Kết quả Chỉ Ảnh AI: " . json_encode($result, JSON_PRETTY_PRINT) . "\n\n";







// ===== EX3: Kiểm tra Kết nối =====

$test_poster = new FacebookAutoPoster($config);

// Kiểm tra Token Facebook
$fb_test = $test_poster->testFacebookConnection();
echo "Kiểm tra Kết nối Facebook: " . json_encode($fb_test, JSON_PRETTY_PRINT) . "\n";

// Kiểm tra API KEY Gemini
if ($config['ai_use'] == 1) {
    $ai_test = $test_poster->testGeminiConnection();
    echo "Kiểm tra Kết nối AI Gemini: " . json_encode($ai_test, JSON_PRETTY_PRINT) . "\n";
}

// ===== EX4: Hàm tiện ích =====

// Lấy danh sách ảnh hiện có
$images = $test_poster->getAvailableImages();
echo "Hình ảnh hiện có: " . implode(', ', $images) . "\n";

// Lấy số lượng chú thích còn lại
$captions_count = $test_poster->getRemainingCaptionsCount();
echo "Chú thích còn lại: " . $captions_count . "\n";

// Lấy cấu hình hiện tại
$current_config = $test_poster->getConfig();
echo "Cấu hình hiện tại: " . json_encode($current_config, JSON_PRETTY_PRINT) . "\n";


?>