<?php

/**
 * Cron Job cho hệ thống tự động đăng bài bóng đá
 * 
 * Ví dụ Cron Schedule:
 * 
 *   # Đăng 3 lần mỗi ngày (7h sáng, 12h trưa, 8h tối)
 *   0 7,12,20 * * * /usr/bin/php /path/to/cron_football.php
 * 
 *   # Đăng mỗi 4 tiếng
 *   0 */4 * * * /usr/bin/php /path/to/cron_football.php
 * 
 *   # Đăng 1 lần mỗi ngày lúc 8h sáng
 *   0 8 * * * /usr/bin/php /path/to/cron_football.php
 * 
 * @author Xiata
 */

require_once __DIR__ . '/footballAutoWorkflow.php';

// ═══ CẤU HÌNH ═══
$config = [
    'page_id'            => 'THAY_PAGE_ID_CUA_BAN',
    'page_access_token'  => 'THAY_ACCESS_TOKEN_CUA_BAN',
    'gemini_api_key'     => 'THAY_GEMINI_API_KEY_CUA_BAN',
    'max_articles'       => 5,
    'date_filter'        => 'both',
    'fetch_full_content' => false,
    'post_style'         => 'tong_hop',
    'generate_image'     => true,
    'image_folder'       => __DIR__ . '/images/',
    'log_file'           => __DIR__ . '/logs/workflow.log',
    'cache_dir'          => __DIR__ . '/cache/',
    'output_dir'         => __DIR__ . '/output/',
];

// ═══ CHẠY ═══
$workflow = new FootballAutoWorkflow($config);
$result = $workflow->run();

// Ghi log kết quả
$log_entry = date('Y-m-d H:i:s') . ' - Cron Result: ' . json_encode($result, JSON_UNESCAPED_UNICODE) . PHP_EOL;
file_put_contents(__DIR__ . '/logs/cron_football.log', $log_entry, FILE_APPEND);

?>
