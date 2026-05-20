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

function xiata_cli_options($argv) {
    $opts = ['mode' => 'run'];
    $mode_set = false;
    for ($i = 1; $i < count($argv); $i++) {
        $arg = $argv[$i];
        if (substr($arg, 0, 2) === '--') {
            $pair = substr($arg, 2);
            $eq = strpos($pair, '=');
            if ($eq !== false) {
                $key = substr($pair, 0, $eq);
                $value = substr($pair, $eq + 1);
            } else {
                $key = $pair;
                $value = true;
                if (isset($argv[$i + 1]) && substr($argv[$i + 1], 0, 2) !== '--') {
                    $value = $argv[++$i];
                }
            }
            $opts[str_replace('-', '_', trim($key))] = $value;
        } elseif (!$mode_set) {
            $opts['mode'] = $arg;
            $mode_set = true;
        }
    }
    return $opts;
}

function xiata_bool($value, $default = false) {
    if ($value === null || $value === '') return $default;
    if (is_bool($value)) return $value;
    $value = strtolower(trim((string)$value));
    return in_array($value, ['1', 'true', 'yes', 'on'], true);
}

function xiata_int($value, $default, $min, $max) {
    if ($value === null || $value === '' || !is_numeric($value)) return $default;
    return max($min, min($max, (int)$value));
}

$cli = xiata_cli_options($argv);
$post_style = $cli['post_style'] ?? ($env['POST_STYLE'] ?? 'tong_hop');
if (!in_array($post_style, ['tong_hop', 'don_le'], true)) {
    $post_style = 'tong_hop';
}
$content_template = $cli['content_template'] ?? ($env['CONTENT_TEMPLATE'] ?? 'tin_nong');
if (!in_array($content_template, ['tin_nong', 'nhan_dinh', 'tranh_luan', 'chuyen_nhuong', 'lich_thi_dau', 'sau_tran'], true)) {
    $content_template = 'tin_nong';
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
    'max_articles'       => xiata_int($cli['max_articles'] ?? ($env['MAX_ARTICLES'] ?? null), 5, 1, 30),
    'date_filter'        => 'both',
    'fetch_full_content' => xiata_bool($cli['full_content'] ?? ($env['FETCH_FULL_CONTENT'] ?? null), false),
    'article_links_file' => __DIR__ . '/input/article_links.txt',
    'avoid_recent_duplicates' => !isset($env['AVOID_RECENT_DUPLICATES']) || strtolower(trim((string)$env['AVOID_RECENT_DUPLICATES'])) !== 'false',
    'article_history_file' => __DIR__ . '/cache/article_history.json',
    'article_history_days' => (int)($env['ARTICLE_HISTORY_DAYS'] ?? 14),
    'max_total_articles' => xiata_int($cli['max_total_articles'] ?? ($env['MAX_TOTAL_ARTICLES'] ?? null), 8, 1, 30),

    // ─── Cấu hình Bài đăng ───
    'post_style'         => $post_style,
    'content_template'   => $content_template,
    'max_posts'          => xiata_int($cli['max_posts'] ?? ($env['MAX_POSTS'] ?? null), 1, 1, 8),
    'no_logo_images'     => xiata_bool($cli['no_logo_images'] ?? ($env['NO_LOGO_IMAGES'] ?? null), true),
    'min_post_image_width' => xiata_int($cli['min_post_image_width'] ?? ($env['MIN_POST_IMAGE_WIDTH'] ?? null), 420, 120, 4000),
    'min_post_image_height' => xiata_int($cli['min_post_image_height'] ?? ($env['MIN_POST_IMAGE_HEIGHT'] ?? null), 220, 120, 4000),
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

$mode = $cli['mode'] ?? 'run';
$workflow = new FootballAutoWorkflow($config);
$exit_code = 0;

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
        if (empty($preview['articles'])) {
            $exit_code = 1;
        }
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
        if (($preview['status'] ?? '') !== 'success') {
            $exit_code = 1;
        }

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
            $post_name = (($config['post_style'] ?? 'tong_hop') === 'don_le') ? 'single_post' : 'summary_post';
            $txt_file = $output_dir . "{$post_name}_{$ts}.txt";
            file_put_contents($txt_file, $preview['post_content']);

            $json_file = $output_dir . 'latest_post.json';
            file_put_contents($json_file, json_encode([
                'post_content' => $preview['post_content'],
                'timestamp'    => date('Y-m-d H:i:s'),
                'source_file'  => basename($txt_file),
                'ai_provider'  => $preview['ai_provider'] ?? 'unknown',
                'post_style'    => $config['post_style'] ?? 'tong_hop',
                'content_template' => $config['content_template'] ?? 'tin_nong',
                'image_path'    => $preview['image_path'] ?? null,
                'image_paths'   => $preview['image_paths'] ?? [],
            ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));

            echo "\n✅ Đã lưu bài vào: output/latest_post.json\n";
            if (!empty($preview['image_path'])) {
                echo "🖼️ Ảnh đính kèm: {$preview['image_path']}\n";
            }
        }
        echo $exit_code === 0 ? "\n💡 Bước tiếp theo: python chrome_poster.py\n" : "\n💡 Hãy thêm link mới hoặc xóa bộ nhớ trùng trước khi đăng.\n";
        break;

    // ─── Chạy đầy đủ (thu thập + tạo bài + tạo ảnh + đăng) ───
    case 'run':
    default:
        echo "🚀 Chế độ: CHẠY ĐẦY ĐỦ\n";
        echo "─────────────────────────────────\n\n";

        $result = $workflow->run();
        if (($result['status'] ?? '') !== 'success') {
            $exit_code = 1;
        }

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

echo $exit_code === 0 ? "\n✅ Hoàn thành!\n" : "\n❌ Có lỗi, vui lòng xem log phía trên.\n";

exit($exit_code);

?>
