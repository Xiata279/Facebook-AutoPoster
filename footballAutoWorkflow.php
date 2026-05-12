<?php

/**
 * Football Auto Workflow
 * 
 * Quy trình tự động hoàn chỉnh:
 * 1. Thu thập tin tức bóng đá từ các nguồn Việt Nam
 * 2. Tóm tắt nội dung bằng Gemini AI
 * 3. Tạo bài đăng Facebook hấp dẫn với câu hỏi tương tác
 * 4. Tạo ảnh minh họa bằng Imagen AI
 * 5. Đăng lên Fanpage Facebook
 * 
 * @author Xiata
 * @version 1.0.0
 */

require_once __DIR__ . '/footballNewsScraper.php';
require_once __DIR__ . '/facebookAutoPoster.php';

class FootballAutoWorkflow {

    private $scraper;
    private $poster;
    private $gemini_api_key;
    private $config;
    private $log_file;

    /**
     * Khởi tạo
     * 
     * @param array $config Cấu hình
     */
    public function __construct($config = []) {
        $this->config = array_merge([
            // Facebook
            'page_id' => '',
            'page_access_token' => '',
            'facebook_api_version' => 'v20.0',

            // Gemini AI
            'gemini_api_key' => '',

            // Scraper
            'max_articles' => 5,        // Số bài mỗi nguồn
            'date_filter' => 'both',    // today, yesterday, both
            'fetch_full_content' => false, // Lấy nội dung đầy đủ (chậm hơn)

            // Bài đăng
            'post_style' => 'tong_hop', // tong_hop = tổng hợp nhiều tin, don_le = 1 tin 1 bài
            'max_posts' => 3,           // Số bài đăng tối đa mỗi lần chạy
            'generate_image' => true,   // Có tạo ảnh AI không

            // Thư mục
            'image_folder' => './images/',
            'log_file' => './logs/workflow.log',
            'cache_dir' => './cache/',
            'output_dir' => './output/', // Lưu bài đăng đã tạo
        ], $config);

        $this->gemini_api_key = $this->config['gemini_api_key'];
        $this->log_file = $this->config['log_file'];

        // Tạo thư mục
        foreach (['image_folder', 'cache_dir', 'output_dir'] as $dir) {
            if (!is_dir($this->config[$dir])) {
                mkdir($this->config[$dir], 0755, true);
            }
        }
        if (!is_dir(dirname($this->log_file))) {
            mkdir(dirname($this->log_file), 0755, true);
        }

        // Khởi tạo Scraper
        $this->scraper = new FootballNewsScraper([
            'log_file' => $this->log_file,
            'cache_dir' => $this->config['cache_dir'],
            'max_articles' => $this->config['max_articles'],
            'date_filter' => $this->config['date_filter'],
        ]);

        // Khởi tạo Poster
        $this->poster = new FacebookAutoPoster([
            'page_id' => $this->config['page_id'],
            'page_access_token' => $this->config['page_access_token'],
            'image_folder' => $this->config['image_folder'],
            'ai_use' => 1,
            'gemini_api_key' => $this->gemini_api_key,
            'log_file' => $this->log_file,
            'facebook_api_version' => $this->config['facebook_api_version'],
        ]);
    }

    /**
     * ═══════════════════════════════════════════════
     *  CHẠY TOÀN BỘ QUY TRÌNH TỰ ĐỘNG
     * ═══════════════════════════════════════════════
     * 
     * Bước 1: Thu thập tin tức
     * Bước 2: Tóm tắt & tạo bài đăng bằng AI
     * Bước 3: Tạo ảnh minh họa
     * Bước 4: Đăng lên Facebook
     * 
     * @return array Kết quả
     */
    public function run() {
        $this->log("════════════════════════════════════════");
        $this->log("BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG - " . date('d/m/Y H:i:s'));
        $this->log("════════════════════════════════════════");

        $results = [];

        try {
            // ─── BƯỚC 1: Thu thập tin tức ───
            $this->log("📰 BƯỚC 1: Thu thập tin tức bóng đá...");
            $articles = $this->scraper->fetchAllNews();

            if (empty($articles)) {
                $this->log("❌ Không tìm thấy tin tức nào!");
                return $this->formatResult('error', 'Không tìm thấy tin tức nào', []);
            }

            $this->log("✅ Đã thu thập " . count($articles) . " tin tức");

            // ─── BƯỚC 2: Tổng hợp nội dung ───
            $this->log("📝 BƯỚC 2: Tổng hợp nội dung tin tức...");
            $compiled_content = $this->scraper->compileNewsContent(
                $articles,
                $this->config['fetch_full_content']
            );

            // ─── BƯỚC 3: Tạo bài đăng bằng AI ───
            if ($this->config['post_style'] === 'tong_hop') {
                $results = $this->createSummaryPost($compiled_content, $articles);
            } else {
                $results = $this->createIndividualPosts($articles);
            }

            $this->log("════════════════════════════════════════");
            $this->log("HOÀN THÀNH - Đã xử lý " . count($results) . " bài đăng");
            $this->log("════════════════════════════════════════");

            return $this->formatResult('success', 'Quy trình hoàn thành', $results);

        } catch (Exception $e) {
            $this->log("❌ LỖI NGHIÊM TRỌNG: " . $e->getMessage());
            return $this->formatResult('error', $e->getMessage(), $results);
        }
    }

    /**
     * Tạo bài đăng tổng hợp (nhiều tin gộp thành 1 bài)
     */
    private function createSummaryPost($compiled_content, $articles) {
        $results = [];

        // ─── Tóm tắt bằng Gemini ───
        $this->log("🤖 Đang gửi nội dung cho Gemini AI tóm tắt...");

        $summary_prompt = $this->buildSummaryPrompt($compiled_content);
        $summary_result = $this->callGemini($summary_prompt);

        if (!$summary_result['success']) {
            $this->log("❌ Lỗi khi tóm tắt: " . $summary_result['message']);
            return $results;
        }

        $facebook_post = $summary_result['text'];
        $this->log("✅ Đã tạo bài đăng Facebook");

        // Lưu bài đăng ra file
        $this->saveOutput('summary_post', $facebook_post);

        // ─── Tạo ảnh minh họa ───
        $image_path = null;
        if ($this->config['generate_image']) {
            $this->log("🎨 Đang tạo ảnh minh họa bằng AI...");

            $image_prompt = $this->buildImagePrompt($articles);
            $image_result = $this->generateImage($image_prompt);

            if ($image_result['success']) {
                $image_path = $image_result['image_path'];
                $this->log("✅ Đã tạo ảnh: " . $image_result['filename']);
            } else {
                $this->log("⚠️ Không thể tạo ảnh: " . $image_result['message']);
            }
        }

        // ─── Đăng lên Facebook ───
        if (!empty($this->config['page_id']) && !empty($this->config['page_access_token'])) {
            $this->log("📤 Đang đăng lên Facebook...");
            $post_result = $this->publishToFacebook($facebook_post, $image_path);
            $results[] = $post_result;
        } else {
            $this->log("⚠️ Chưa cấu hình Facebook credentials - chỉ lưu bài đăng local");
            $results[] = [
                'status' => 'saved_locally',
                'message' => 'Bài đăng đã được lưu (chưa cấu hình Facebook)',
                'post_content' => $facebook_post,
                'image_path' => $image_path,
            ];
        }

        return $results;
    }

    /**
     * Tạo bài đăng riêng lẻ cho từng tin
     */
    private function createIndividualPosts($articles) {
        $results = [];
        $count = 0;

        foreach ($articles as $article) {
            if ($count >= $this->config['max_posts']) break;

            $this->log("📝 Đang xử lý tin: {$article['title']}");

            // Lấy nội dung đầy đủ nếu cần
            $content = !empty($article['description']) ? $article['description'] : $article['title'];
            if ($this->config['fetch_full_content'] && !empty($article['link'])) {
                $full = $this->scraper->fetchArticleContent($article['link']);
                if (!empty($full)) $content = $full;
            }

            // Tạo bài đăng
            $post_prompt = $this->buildSinglePostPrompt($article['title'], $content);
            $post_result = $this->callGemini($post_prompt);

            if (!$post_result['success']) {
                $this->log("❌ Lỗi tạo bài cho: {$article['title']}");
                continue;
            }

            $facebook_post = $post_result['text'];
            $this->saveOutput("post_{$count}", $facebook_post);

            // Tạo ảnh
            $image_path = null;
            if ($this->config['generate_image']) {
                $img_prompt = "A dynamic football news illustration: {$article['title']}. Professional sports photography style, vibrant stadium atmosphere, 4K quality, dramatic lighting";
                $image_result = $this->generateImage($img_prompt);
                if ($image_result['success']) {
                    $image_path = $image_result['image_path'];
                }
            }

            // Đăng lên Facebook
            if (!empty($this->config['page_id']) && !empty($this->config['page_access_token'])) {
                $result = $this->publishToFacebook($facebook_post, $image_path);
                $results[] = $result;

                // Đợi giữa các bài đăng (tránh rate limit)
                if ($count < $this->config['max_posts'] - 1) {
                    $this->log("⏳ Đợi 30 giây trước bài tiếp theo...");
                    sleep(30);
                }
            } else {
                $results[] = [
                    'status' => 'saved_locally',
                    'post_content' => $facebook_post,
                    'image_path' => $image_path,
                ];
            }

            $count++;
        }

        return $results;
    }

    /**
     * ═══════════════════════════════════════════════
     *  CÁC PROMPT AI
     * ═══════════════════════════════════════════════
     */

    /**
     * Prompt tóm tắt & tạo bài đăng tổng hợp
     */
    private function buildSummaryPrompt($compiled_content) {
        return "Bạn là một chuyên gia content bóng đá chuyên viết bài đăng Fanpage Facebook có khả năng tạo tương tác cao.

Dưới đây là nội dung tin tức bóng đá hôm nay:

--- NỘI DUNG ---
{$compiled_content}
--- HẾT NỘI DUNG ---

Hãy thực hiện:

1. **Tóm tắt** các tin tức quan trọng nhất (chọn 3-5 tin nổi bật nhất)
2. **Viết bài đăng Facebook** bằng tiếng Việt theo format sau:
   - Mở đầu bằng một câu hook gây chú ý (kèm emoji)
   - Tóm tắt từng tin ngắn gọn, hấp dẫn (mỗi tin 1-2 câu, có emoji)
   - Viết tự nhiên, gần gũi, có cảm xúc
   - **BẮT BUỘC** có câu hỏi mở ở cuối để khuyến khích bình luận
   - Thêm 3-5 hashtag phù hợp ở cuối
   - Tổng bài khoảng 150-250 từ

Yêu cầu quan trọng:
- Chỉ trả về BÀI ĐĂNG FACEBOOK sẵn sàng copy-paste, KHÔNG cần giải thích thêm
- Không đề cập nguồn tin
- Sử dụng emoji hợp lý, đẹp mắt
- Kết thúc bằng câu kêu gọi bình luận rõ ràng";
    }

    /**
     * Prompt tạo bài đăng cho một tin đơn lẻ
     */
    private function buildSinglePostPrompt($title, $content) {
        return "Bạn là chuyên gia content bóng đá. Viết bài đăng Facebook từ tin tức sau:

Tiêu đề: {$title}
Nội dung: {$content}

Yêu cầu:
- Viết bài đăng Facebook tiếng Việt, tự nhiên, có cảm xúc
- Dài khoảng 100-180 từ
- Sử dụng emoji hợp lý
- Mở đầu gây chú ý
- BẮT BUỘC có câu hỏi mở ở cuối để tăng tương tác
- Thêm 3-5 hashtag phù hợp
- Chỉ trả về bài đăng sẵn sàng copy-paste, KHÔNG giải thích";
    }

    /**
     * Prompt tạo ảnh minh họa
     */
    private function buildImagePrompt($articles) {
        // Lấy chủ đề chính từ các tiêu đề
        $titles = array_column(array_slice($articles, 0, 3), 'title');
        $topic = implode(', ', $titles);

        return "A stunning professional football news banner composition. Dynamic football action scene with dramatic stadium lighting, green pitch, football/soccer ball in motion, vibrant atmosphere with fans silhouettes in background. Modern sports media design with bold colors (green, blue, gold accents). Text-free clean design, 4K ultra quality, cinematic sports photography style. Topic context: Vietnamese football news today.";
    }

    /**
     * ═══════════════════════════════════════════════
     *  GỌI API
     * ═══════════════════════════════════════════════
     */

    /**
     * Gọi Gemini API để tạo text
     */
    private function callGemini($prompt) {
        try {
            $url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=' . $this->gemini_api_key;

            $data = [
                'contents' => [
                    [
                        'parts' => [
                            ['text' => $prompt]
                        ]
                    ]
                ],
                'generationConfig' => [
                    'temperature' => 0.8,
                    'topK' => 40,
                    'topP' => 0.95,
                    'maxOutputTokens' => 1024
                ]
            ];

            $response = $this->makeRequest($url, $data);

            if (!$response['success']) {
                return ['success' => false, 'message' => $response['message']];
            }

            $result = $response['data'];

            if (isset($result['candidates'][0]['content']['parts'][0]['text'])) {
                $text = trim($result['candidates'][0]['content']['parts'][0]['text']);
                return ['success' => true, 'text' => $text];
            }

            return ['success' => false, 'message' => 'Gemini không trả về kết quả'];

        } catch (Exception $e) {
            return ['success' => false, 'message' => $e->getMessage()];
        }
    }

    /**
     * Tạo ảnh bằng Imagen API
     */
    private function generateImage($prompt) {
        try {
            $url = 'https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=' . $this->gemini_api_key;

            $data = [
                'instances' => [
                    ['prompt' => $prompt]
                ],
                'parameters' => [
                    'sampleCount' => 1,
                    'aspectRatio' => '16:9',
                    'safetyFilterLevel' => 'block_some',
                    'personGeneration' => 'allow_adult'
                ]
            ];

            $response = $this->makeRequest($url, $data);

            if (!$response['success']) {
                return ['success' => false, 'message' => $response['message']];
            }

            $result = $response['data'];

            if (isset($result['predictions'][0]['bytesBase64Encoded'])) {
                $image_data = base64_decode($result['predictions'][0]['bytesBase64Encoded']);
                $filename = 'football_news_' . date('Ymd_His') . '_' . uniqid() . '.png';
                $image_path = $this->config['image_folder'] . $filename;

                if (file_put_contents($image_path, $image_data)) {
                    return ['success' => true, 'image_path' => $image_path, 'filename' => $filename];
                }
            }

            return ['success' => false, 'message' => 'Không nhận được dữ liệu ảnh'];

        } catch (Exception $e) {
            return ['success' => false, 'message' => $e->getMessage()];
        }
    }

    /**
     * Đăng lên Facebook
     */
    private function publishToFacebook($caption, $image_path = null) {
        try {
            $page_token = $this->getPageToken();
            if (!$page_token) {
                return ['status' => 'error', 'message' => 'Không thể lấy token trang'];
            }

            $api_version = $this->config['facebook_api_version'];
            $page_id = $this->config['page_id'];

            if ($image_path && file_exists($image_path)) {
                $url = "https://graph.facebook.com/{$api_version}/{$page_id}/photos";
                $post_fields = [
                    'caption' => $caption,
                    'access_token' => $page_token,
                    'source' => new CURLFile($image_path)
                ];
            } else {
                $url = "https://graph.facebook.com/{$api_version}/{$page_id}/feed";
                $post_fields = [
                    'message' => $caption,
                    'access_token' => $page_token
                ];
            }

            $ch = curl_init();
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $post_fields,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_TIMEOUT => 30,
                CURLOPT_SSL_VERIFYPEER => false,
            ]);

            $result = curl_exec($ch);
            $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);

            $decoded = json_decode($result, true);

            if ($http_code == 200 && isset($decoded['id'])) {
                $this->log("✅ Đăng Facebook thành công! Post ID: " . $decoded['id']);
                return [
                    'status' => 'success',
                    'message' => 'Đăng bài thành công',
                    'post_id' => $decoded['id'],
                    'timestamp' => date('Y-m-d H:i:s')
                ];
            } else {
                $error_msg = $decoded['error']['message'] ?? 'Lỗi không xác định';
                $this->log("❌ Đăng Facebook thất bại: " . $error_msg);
                return ['status' => 'error', 'message' => $error_msg, 'http_code' => $http_code];
            }

        } catch (Exception $e) {
            return ['status' => 'error', 'message' => $e->getMessage()];
        }
    }

    /**
     * Lấy Page Access Token
     */
    private function getPageToken() {
        $url = "https://graph.facebook.com/{$this->config['facebook_api_version']}/{$this->config['page_id']}?fields=access_token&access_token={$this->config['page_access_token']}";

        $response = $this->makeRequest($url, null, 'GET');

        if ($response['success'] && isset($response['data']['access_token'])) {
            return $response['data']['access_token'];
        }

        return null;
    }

    /**
     * HTTP Request
     */
    private function makeRequest($url, $data = null, $method = 'POST') {
        $ch = curl_init();

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 60,
            CURLOPT_CONNECTTIMEOUT => 10,
            CURLOPT_SSL_VERIFYPEER => false,
        ]);

        if ($method === 'POST' && $data) {
            curl_setopt($ch, CURLOPT_POST, true);
            $json_data = json_encode($data);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $json_data);
            curl_setopt($ch, CURLOPT_HTTPHEADER, [
                'Content-Type: application/json',
                'Content-Length: ' . strlen($json_data)
            ]);
        }

        $result = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            return ['success' => false, 'message' => "Lỗi cURL: $error"];
        }

        $decoded = json_decode($result, true);

        if ($http_code >= 200 && $http_code < 300) {
            return ['success' => true, 'data' => $decoded];
        } else {
            return [
                'success' => false,
                'message' => $decoded['error']['message'] ?? "Lỗi HTTP: $http_code",
                'data' => $decoded
            ];
        }
    }

    /**
     * ═══════════════════════════════════════════════
     *  TIỆN ÍCH
     * ═══════════════════════════════════════════════
     */

    /**
     * Lưu output ra file
     */
    private function saveOutput($name, $content) {
        $filename = $this->config['output_dir'] . $name . '_' . date('Ymd_His') . '.txt';
        file_put_contents($filename, $content);
        $this->log("💾 Đã lưu output: $filename");
    }

    /**
     * Format kết quả
     */
    private function formatResult($status, $message, $posts = []) {
        return [
            'status' => $status,
            'message' => $message,
            'total_posts' => count($posts),
            'posts' => $posts,
            'timestamp' => date('Y-m-d H:i:s')
        ];
    }

    /**
     * Ghi log
     */
    private function log($message) {
        $log_entry = date('Y-m-d H:i:s') . " [Workflow] " . $message . PHP_EOL;
        file_put_contents($this->log_file, $log_entry, FILE_APPEND | LOCK_EX);
        // Cũng in ra console
        echo $message . "\n";
    }

    /**
     * Chỉ thu thập tin (không đăng bài)
     * Hữu ích để xem trước nội dung
     */
    public function previewNews() {
        $articles = $this->scraper->fetchAllNews();
        $compiled = $this->scraper->compileNewsContent($articles);
        return [
            'articles' => $articles,
            'compiled_content' => $compiled
        ];
    }

    /**
     * Chỉ tạo bài đăng (không đăng lên Facebook)
     * Hữu ích để xem trước bài đăng
     */
    public function previewPost() {
        $articles = $this->scraper->fetchAllNews();
        $compiled = $this->scraper->compileNewsContent($articles, $this->config['fetch_full_content']);
        $prompt = $this->buildSummaryPrompt($compiled);
        $result = $this->callGemini($prompt);

        return [
            'articles_count' => count($articles),
            'post_content' => $result['success'] ? $result['text'] : 'Lỗi: ' . $result['message'],
            'status' => $result['success'] ? 'success' : 'error'
        ];
    }
}

?>
