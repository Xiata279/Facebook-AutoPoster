<?php

/**
 * ═══════════════════════════════════════════════════════
 *  CHẠY QUY TRÌNH TỰ ĐỘNG ĐĂNG BÀI BÓNG ĐÁ
 * ═══════════════════════════════════════════════════════
 * 
 * Sử dụng:
 *   php run_football_post.php              → Chạy đầy đủ (thu thập + đăng bài)
 *   php run_football_post.php preview      → Chỉ xem trước tin tức
 *   php run_football_post.php preview-post → Xem trước bài đăng (không đăng)
 * 
 * @author Xiata
 */

require_once __DIR__ . '/footballAutoWorkflow.php';

// ═══════════════════════════════════════════════════════
//  CẤU HÌNH - THAY ĐỔI THÔNG TIN CỦA BẠN TẠI ĐÂY
// ═══════════════════════════════════════════════════════

$config = [
    // ─── Facebook Credentials ───
    'page_id'            => 'THAY_PAGE_ID_CUA_BAN',
    'page_access_token'  => 'THAY_ACCESS_TOKEN_CUA_BAN',
    'facebook_api_version' => 'v20.0',

    // ─── Grok AI (xAI) — AI chính để viết bài ───
    'grok_api_key'       => 'THAY_GROK_API_KEY_CUA_BAN',  // xai-...
    'grok_model'         => 'grok-3-mini-fast',            // grok-3 | grok-3-mini | grok-3-mini-fast

    // ─── Gemini AI — fallback text + tạo ảnh Imagen ───
    'gemini_api_key'     => 'THAY_GEMINI_API_KEY_CUA_BAN',
    'gemini_model'       => 'gemini-2.5-flash-lite',       // model Gemini để tạo text (fallback)

    // ─── Cấu hình Thu thập tin ───
    'max_articles'       => 5,
    'date_filter'        => 'both',
    'fetch_full_content' => false,

    // ─── Cấu hình Bài đăng ───
    'post_style'         => 'tong_hop',
    'max_posts'          => 3,
    'generate_image'     => true,

    // ─── Thư mục ───
    'image_folder'       => './images/',
    'log_file'           => './logs/workflow.log',
    'cache_dir'          => './cache/',
    'output_dir'         => './output/',
];

// ═══════════════════════════════════════════════════════
//  CHẠY
// ═══════════════════════════════════════════════════════

$mode = $argv[1] ?? 'run';
$workflow = new FootballAutoWorkflow($config);

echo "\n";
echo "╔══════════════════════════════════════════════════╗\n";
echo "║   ⚽ HỆ THỐNG TỰ ĐỘNG ĐĂNG BÀI BÓNG ĐÁ ⚽    ║\n";
echo "║                  by Xiata                        ║\n";
echo "╚══════════════════════════════════════════════════╝\n";
echo "\n";

switch ($mode) {
    // ─── Xem trước tin tức (không tạo bài, không đăng) ───
    case 'preview':
        echo "📰 Chế độ: XEM TRƯỚC TIN TỨC\n";
        echo "─────────────────────────────────\n\n";

        $preview = $workflow->previewNews();
        echo "Tổng số tin: " . count($preview['articles']) . "\n\n";

        foreach ($preview['articles'] as $i => $article) {
            $num = $i + 1;
            echo "  {$num}. [{$article['source']}] {$article['title']}\n";
            echo "     📅 {$article['published_at']}\n";
            if (!empty($article['description'])) {
                echo "     📝 " . mb_substr($article['description'], 0, 100) . "...\n";
            }
            echo "\n";
        }

        echo "\n─────────────────────────────────\n";
        echo "💡 Để tạo bài đăng, chạy: php run_football_post.php preview-post\n";
        echo "💡 Để đăng bài, chạy: php run_football_post.php\n";
        break;

    // ─── Xem trước bài đăng (tạo bài nhưng không đăng Facebook) ───
    case 'preview-post':
        echo "📝 Chế độ: XEM TRƯỚC BÀI ĐĂNG\n";
        echo "─────────────────────────────────\n\n";

        $preview = $workflow->previewPost();

        echo "📰 Số tin đã thu thập: {$preview['articles_count']}\n";
        echo "Trạng thái: {$preview['status']}\n";
        echo "AI dùng: " . strtoupper($preview['ai_provider'] ?? '?') . "\n\n";
        echo "═══ BÀI ĐĂNG FACEBOOK ═══\n\n";
        echo $preview['post_content'];
        echo "\n\n═══════════════════════════\n";
        echo "\n💡 Để đăng bài lên Facebook, chạy: php run_football_post.php\n";
        break;

    // ─── Chạy đầy đủ (thu thập + tạo bài + tạo ảnh + đăng) ───
    case 'run':
    default:
        echo "🚀 Chế độ: CHẠY ĐẦY ĐỦ\n";
        echo "─────────────────────────────────\n\n";

        $result = $workflow->run();

        echo "\n═══ KẾT QUẢ ═══\n";
        echo "Trạng thái: " . strtoupper($result['status']) . "\n";
        echo "Thông báo: {$result['message']}\n";
        echo "Tổng bài đăng: {$result['total_posts']}\n";
        echo "Thời gian: {$result['timestamp']}\n";

        if (!empty($result['posts'])) {
            foreach ($result['posts'] as $i => $post) {
                $num = $i + 1;
                echo "\n  Bài #{$num}: {$post['status']}";
                if (isset($post['post_id'])) {
                    echo " (ID: {$post['post_id']})";
                }
                echo "\n";
            }
        }
        break;
}

echo "\n✅ Hoàn thành!\n";

?>
