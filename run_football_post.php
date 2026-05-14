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
// Đọc cấu hình từ file .env
$env_file = __DIR__ . '/.env';
$env = [];
if (file_exists($env_file)) {
    $env = parse_ini_file($env_file);
} else {
    echo "\u26a0️ Không tìm thấy file .env\n";
    echo "   Sao chép .env.example thành .env và điền thông tin vào\n\n";
}

$config = [
    // ─── Facebook Credentials ───
    'page_id'            => $env['FB_PAGE_ID'] ?? '',
    'page_access_token'  => $env['FB_ACCESS_TOKEN'] ?? '',
    'facebook_api_version' => 'v20.0',

    // ─── Free AI ───
    'free_ai_only'       => !isset($env['FREE_AI_ONLY']) || strtolower(trim((string)$env['FREE_AI_ONLY'])) !== 'false',
    'ollama_base_url'    => $env['OLLAMA_BASE_URL'] ?? 'http://localhost:11434',
    'ollama_model'       => $env['OLLAMA_MODEL'] ?? 'gemma3',
    'hf_token'           => $env['HF_TOKEN'] ?? '',
    'hf_model'           => $env['HF_MODEL'] ?? 'deepseek-ai/DeepSeek-R1:fastest',

    // ─── Grok AI (xAI) — AI chính để viết bài ───
    'grok_api_key'       => $env['GROK_API_KEY'] ?? '',
    'grok_model'         => $env['GROK_MODEL'] ?? 'grok-3-mini-fast',

    // ─── ChatGPT / OpenAI — fallback nội dung qua Responses API ───
    'openai_api_key'     => $env['OPENAI_API_KEY'] ?? '',
    'openai_model'       => $env['OPENAI_MODEL'] ?? 'chat-latest',

    // ─── Gemini AI — fallback text + tạo ảnh Imagen ───
    'gemini_api_key'     => $env['GEMINI_API_KEY'] ?? '',
    'gemini_model'       => $env['GEMINI_MODEL'] ?? 'gemini-2.5-flash-lite',

    // ─── Cấu hình Thu thập tin ───
    'max_articles'       => 5,
    'date_filter'        => 'both',
    'fetch_full_content' => false,
    'article_links_file' => __DIR__ . '/input/article_links.txt',
    'avoid_recent_duplicates' => !isset($env['AVOID_RECENT_DUPLICATES']) || strtolower(trim((string)$env['AVOID_RECENT_DUPLICATES'])) !== 'false',
    'article_history_file' => __DIR__ . '/cache/article_history.json',
    'article_history_days' => (int)($env['ARTICLE_HISTORY_DAYS'] ?? 14),
    'max_total_articles' => (int)($env['MAX_TOTAL_ARTICLES'] ?? 8),

    // ─── Cấu hình Bài đăng ───
    'post_style'         => 'tong_hop',
    'max_posts'          => 1,
    // Bật tạo ảnh nếu có Gemini key
    'generate_image'     => false,

    // ─── Thư mục ───
    'image_folder'       => __DIR__ . '/images/',
    'log_file'           => __DIR__ . '/logs/workflow.log',
    'cache_dir'          => __DIR__ . '/cache/',
    'output_dir'         => __DIR__ . '/output/',
];

// Tự động tạo thư mục cần thiết
foreach (['images', 'logs', 'cache', 'output', 'input'] as $dir) {
    $path = __DIR__ . '/' . $dir;
    if (!is_dir($path)) { mkdir($path, 0755, true); }
}

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

        // ✅ Lưu file để chrome_poster.py đọc ở bước tiếp theo
        if (!empty($preview['post_content']) && $preview['status'] === 'success') {
            $output_dir = $config['output_dir'];
            if (!is_dir($output_dir)) { mkdir($output_dir, 0755, true); }

            $ts = date('Ymd_His');
            $txt_file = $output_dir . "summary_post_{$ts}.txt";
            file_put_contents($txt_file, $preview['post_content']);

            $json_file = $output_dir . 'latest_post.json';
            file_put_contents($json_file, json_encode([
                'post_content' => $preview['post_content'],
                'timestamp'    => date('Y-m-d H:i:s'),
                'source_file'  => basename($txt_file),
                'ai_provider'  => $preview['ai_provider'] ?? 'unknown',
                'image_path'    => $preview['image_path'] ?? null,
                'image_paths'   => $preview['image_paths'] ?? [],
            ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));

            echo "\n✅ Đã lưu bài vào: output/latest_post.json\n";
            if (!empty($preview['image_path'])) {
                echo "🖼️ Ảnh đính kèm: {$preview['image_path']}\n";
            }
        }
        echo "\n💡 Bước tiếp theo: python chrome_poster.py\n";
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
