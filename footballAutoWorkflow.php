<?php

/**
 * Football Auto Workflow
 * 
 * Quy trình tự động hoàn chỉnh:
 * 1. Thu thập tin tức bóng đá từ các nguồn Việt Nam
 * 2. Tóm tắt nội dung bằng Grok, ChatGPT/OpenAI hoặc Gemini AI
 * 3. Tạo bài đăng Facebook hấp dẫn với câu hỏi tương tác
 * 4. Tạo ảnh minh họa bằng Imagen AI (Gemini)
 * 5. Đăng lên Fanpage Facebook
 * 
 * AI Text  : ChatGPT/OpenAI → Grok (xai-...) → fallback Gemini nếu lỗi
 * AI Image : Gemini Imagen
 * 
 * @author Xiata
 * @version 1.0.0
 */

require_once __DIR__ . '/footballNewsScraper.php';
require_once __DIR__ . '/facebookAutoPoster.php';

class FootballAutoWorkflow {

    private $scraper;
    private $poster;
    private $ollama_base_url;
    private $hf_token;
    private $gemini_api_key;
    private $grok_api_key;
    private $openai_api_key;
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

            // Free AI - ưu tiên trước để tránh phát sinh chi phí
            'free_ai_only' => true,
            'ollama_base_url' => 'http://localhost:11434',
            'ollama_model' => 'gemma3',
            'hf_token' => '',
            'hf_model' => 'deepseek-ai/DeepSeek-R1:fastest',

            // Grok AI (xAI) - fallback khi người dùng bật không giới hạn miễn phí
            'grok_api_key' => '',
            'grok_model'   => 'grok-3-mini-fast',  // hoặc grok-3, grok-3-mini

            // ChatGPT / OpenAI - chỉ dùng nếu người dùng muốn
            'openai_api_key' => '',
            'openai_model'   => 'chat-latest',

            // Gemini AI - fallback text / image nếu người dùng muốn
            'gemini_api_key' => '',
            'gemini_model'   => 'gemini-2.5-flash-lite',

            // Scraper
            'max_articles' => 5,        // Số bài mỗi nguồn
            'date_filter' => 'both',    // today, yesterday, both
            'fetch_full_content' => false, // Lấy nội dung đầy đủ (chậm hơn)
            'article_links' => [],       // Link bài viết người dùng gửi
            'article_links_file' => '',  // File chứa link, mỗi dòng một URL
            'avoid_recent_duplicates' => true,
            'article_history_file' => './cache/article_history.json',
            'article_history_days' => 14,
            'max_total_articles' => 8,

            // Bài đăng
            'post_style' => 'tong_hop', // tong_hop = tổng hợp nhiều tin, don_le = 1 tin 1 bài
            'content_template' => 'tin_nong',
            'max_posts' => 3,           // Số bài đăng tối đa mỗi lần chạy
            'generate_image' => false,   // Có tạo ảnh AI không
            'no_logo_images' => true,
            'min_post_image_width' => 420,
            'min_post_image_height' => 220,

            // Thư mục
            'image_folder' => './images/',
            'log_file' => './logs/workflow.log',
            'cache_dir' => './cache/',
            'output_dir' => './output/', // Lưu bài đăng đã tạo
        ], $config);

        $this->gemini_api_key = $this->config['gemini_api_key'];
        $this->ollama_base_url = rtrim($this->config['ollama_base_url'] ?? '', '/');
        $this->hf_token = $this->config['hf_token'] ?? '';
        $this->grok_api_key   = $this->config['grok_api_key'];
        $this->openai_api_key = $this->config['openai_api_key'];
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
            $articles = $this->fetchInputArticles();

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

        // ─── Tóm tắt bằng AI ───
        $this->log("🤖 Đang gửi nội dung cho AI tóm tắt...");

        $summary_prompt = $this->hasManualLinks()
            ? $this->buildDailyLinksPrompt($compiled_content)
            : $this->buildSummaryPrompt($compiled_content);
        $summary_result = $this->callAI($summary_prompt);

        if (!$summary_result['success']) {
            $this->log("❌ Lỗi khi tóm tắt: " . $summary_result['message']);
            return $results;
        }

        $facebook_post = $summary_result['text'];
        $this->log("✅ Đã tạo bài đăng Facebook (via " . $summary_result['provider'] . ")");

        // ─── Lấy ảnh từ link bài viết; nếu không có mới tạo ảnh AI ───
        $image_paths = $this->downloadArticleImages($articles);
        $image_path = $image_paths[0] ?? null;
        if (!$image_path && $this->config['generate_image']) {
            $this->log("🎨 Đang tạo ảnh minh họa bằng AI...");

            $image_prompt = $this->buildImagePrompt($articles);
            $image_result = $this->generateImage($image_prompt);

            if ($image_result['success']) {
                $image_path = $image_result['image_path'];
                $image_paths = [$image_path];
                $this->log("✅ Đã tạo ảnh: " . $image_result['filename']);
            } else {
                $this->log("⚠️ Không thể tạo ảnh: " . $image_result['message']);
            }
        }

        // Lưu bài đăng ra file sau khi biết ảnh đính kèm
        $this->saveOutput('summary_post', $facebook_post, $image_path, $articles, $summary_result['provider'] ?? 'unknown', $image_paths);

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
            $post_result = $this->callAI($post_prompt);

            if (!$post_result['success']) {
                $this->log("❌ Lỗi tạo bài cho: {$article['title']}");
                continue;
            }

            $facebook_post = $post_result['text'];
            $image_paths = $this->downloadArticleImages([$article], 1);
            $image_path = $image_paths[0] ?? null;

            // Tạo ảnh
            if ($this->config['generate_image']) {
                $img_prompt = "A dynamic football news illustration: {$article['title']}. Professional sports photography style, vibrant stadium atmosphere, 4K quality, dramatic lighting, no logo, no watermark, no text overlay";
                $image_result = $this->generateImage($img_prompt);
                if ($image_result['success']) {
                    $image_path = $image_result['image_path'];
                    $image_paths = [$image_path];
                }
            }

            $this->saveOutput(
                "post_{$count}",
                $facebook_post,
                $image_path,
                [$article],
                $post_result['provider'] ?? 'unknown',
                $image_paths
            );

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

    private function fetchInputArticles() {
        $links = $this->getArticleLinks();
        $manual = !empty($links);
        if (!empty($links)) {
            $this->log("🔗 Dùng " . count($links) . " link bài viết người dùng gửi");
            $articles = $this->scraper->fetchFromLinks($links);
        } else {
            $articles = $this->scraper->fetchAllNews();
        }

        $articles = $this->scraper->deduplicateArticles($articles);

        if (!empty($this->config['avoid_recent_duplicates'])) {
            $articles = $this->filterRecentDuplicateArticles($articles, $manual);
        }

        $limit = (int)($this->config['max_total_articles'] ?? 8);
        if ($limit > 0 && count($articles) > $limit) {
            $articles = array_slice($articles, 0, $limit);
            $this->log("Giới hạn bản tin còn {$limit} tin mới nhất để bài đăng gọn hơn");
        }

        return array_values($articles);
    }

    private function getArticleLinks() {
        $links = [];

        if (!empty($this->config['article_links']) && is_array($this->config['article_links'])) {
            $links = array_merge($links, $this->config['article_links']);
        }

        $file = $this->config['article_links_file'] ?? '';
        if ($file && file_exists($file)) {
            $raw = file_get_contents($file);
            $lines = preg_split('/[\r\n,]+/', $raw);
            $links = array_merge($links, $lines ?: []);
        }

        $clean = [];
        foreach ($links as $link) {
            $link = trim((string) $link);
            if (filter_var($link, FILTER_VALIDATE_URL) && preg_match('/^https?:\/\//i', $link) && !in_array($link, $clean, true)) {
                $clean[] = $link;
            }
        }
        return $clean;
    }

    private function hasManualLinks() {
        return !empty($this->getArticleLinks());
    }

    private function filterRecentDuplicateArticles($articles, $manual = false) {
        $history = $this->loadArticleHistory();
        if (empty($history) || empty($articles)) {
            return $articles;
        }

        $fresh = [];
        $skipped = 0;
        foreach ($articles as $article) {
            if ($this->articleWasUsedRecently($article, $history)) {
                $skipped++;
                continue;
            }
            $fresh[] = $article;
        }

        if ($skipped > 0) {
            $scope = $manual ? 'link thủ công' : 'nguồn tự động';
            $this->log("Đã bỏ qua {$skipped} tin/link đã dùng gần đây ({$scope})");
        }

        return array_values($fresh);
    }

    private function articleWasUsedRecently($article, $history) {
        $fp = $this->scraper->articleFingerprint($article);
        $title = $article['title'] ?? '';

        foreach ($history as $record) {
            if (!is_array($record)) {
                continue;
            }
            if (!empty($fp['link_hash']) && !empty($record['link_hash']) && $fp['link_hash'] === $record['link_hash']) {
                return true;
            }
            if (!empty($fp['title_hash']) && !empty($record['title_hash']) && $fp['title_hash'] === $record['title_hash']) {
                return true;
            }
            $old_title = $record['title_key'] ?? ($record['title'] ?? '');
            if ($title && $old_title && $this->scraper->titlesAreSimilar($title, $old_title)) {
                return true;
            }
        }

        return false;
    }

    private function loadArticleHistory() {
        $file = $this->config['article_history_file'] ?? '';
        if (!$file || !file_exists($file)) {
            return [];
        }

        $data = json_decode(file_get_contents($file), true);
        if (!is_array($data)) {
            return [];
        }

        $days = max(1, (int)($this->config['article_history_days'] ?? 14));
        $cutoff = strtotime("-{$days} days");
        $fresh = [];

        foreach ($data as $record) {
            $used_at = strtotime($record['used_at'] ?? 'now');
            if ($used_at >= $cutoff) {
                $fresh[] = $record;
            }
        }

        return $fresh;
    }

    private function saveArticleHistory($history) {
        $file = $this->config['article_history_file'] ?? '';
        if (!$file) {
            return;
        }
        $dir = dirname($file);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        file_put_contents($file, json_encode(array_values($history), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    }

    private function rememberArticleHistory($articles) {
        if (empty($this->config['avoid_recent_duplicates']) || empty($articles)) {
            return;
        }

        $history = $this->loadArticleHistory();
        $index = [];
        foreach ($history as $record) {
            if (!empty($record['link_hash'])) {
                $index['l:' . $record['link_hash']] = true;
            }
            if (!empty($record['title_hash'])) {
                $index['t:' . $record['title_hash']] = true;
            }
        }

        $added = 0;
        foreach ($articles as $article) {
            $fp = $this->scraper->articleFingerprint($article);
            $dedupe_key = !empty($fp['link_hash']) ? 'l:' . $fp['link_hash'] : 't:' . $fp['title_hash'];
            if (!$dedupe_key || isset($index[$dedupe_key])) {
                continue;
            }

            $history[] = [
                'used_at' => date('Y-m-d H:i:s'),
                'title' => $article['title'] ?? '',
                'link' => $article['link'] ?? '',
                'source' => $article['source'] ?? '',
                'link_hash' => $fp['link_hash'],
                'title_hash' => $fp['title_hash'],
                'title_key' => $fp['title_key'],
            ];
            $index[$dedupe_key] = true;
            $added++;
        }

        if ($added > 0) {
            $this->saveArticleHistory(array_slice($history, -300));
            $this->log("Đã lưu {$added} dấu vết tin vào bộ chống trùng");
        }
    }

    private function downloadArticleImage($articles) {
        $paths = $this->downloadArticleImages($articles, 1);
        return $paths[0] ?? null;
    }

    private function downloadArticleImages($articles, $limit = 4) {
        $paths = [];
        $seen = [];
        $clean_only = !empty($this->config['no_logo_images']);

        foreach ($articles as $article) {
            $candidates = [];
            $image_url = trim($article['image'] ?? '');
            if ($image_url) {
                $candidates[] = $image_url;
            }
            if (($clean_only || !$image_url) && !empty($article['link'])) {
                $this->log("Đang bổ sung ảnh từ trang bài viết: {$article['link']}");
                $enriched = $this->scraper->fetchArticleFromUrl($article['link']);
                $enriched_image = trim($enriched['image'] ?? '');
                if ($enriched_image) {
                    $candidates[] = $enriched_image;
                }
            }

            foreach (array_values(array_unique($candidates)) as $image_url) {
                if (!$image_url || !preg_match('/^https?:\/\//i', $image_url)) {
                    continue;
                }
                if ($clean_only && $this->imageUrlLooksLogoLike($image_url)) {
                    $this->log("Bỏ qua ảnh nghi là logo/watermark: {$image_url}");
                    continue;
                }
                if (isset($seen[$image_url])) {
                    continue;
                }
                $seen[$image_url] = true;

                $this->log("🖼️ Đang lấy ảnh từ bài viết: {$image_url}");
                $path = $this->downloadImageFile($image_url, $article['link'] ?? '');
                if (!$path) {
                    continue;
                }
                if ($clean_only && !$this->imageFileLooksCleanForPost($path, $reason)) {
                    @unlink($path);
                    $this->log("Bỏ qua ảnh chưa đạt chuẩn không-logo ({$reason})");
                    continue;
                }

                $this->log("✅ Đã lưu ảnh bài viết: " . basename($path));
                $paths[] = $path;
                if (count($paths) >= $limit) {
                    break 2;
                }
            }
        }

        if (empty($paths)) {
            $this->log("ℹ️ Không tìm thấy ảnh hợp lệ trong các link bài viết");
        }
        return $paths;
    }

    private function downloadImageFile($url, $referer = '') {
        try {
            $ch = curl_init();
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_FOLLOWLOCATION => true,
                CURLOPT_TIMEOUT => 45,
                CURLOPT_CONNECTTIMEOUT => 10,
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                CURLOPT_HTTPHEADER => array_filter([
                    'Accept: image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    $referer ? 'Referer: ' . $referer : '',
                ]),
            ]);

            $data = curl_exec($ch);
            $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $content_type = curl_getinfo($ch, CURLINFO_CONTENT_TYPE) ?: '';
            $error = curl_error($ch);
            curl_close($ch);

            if ($error || $http_code >= 400 || empty($data) || strlen($data) < 1024) {
                $this->log("⚠️ Không tải được ảnh ({$http_code}): {$error}");
                return null;
            }

            $ext = $this->imageExtension($content_type, $url);
            $filename = 'article_image_' . date('Ymd_His') . '_' . uniqid() . '.' . $ext;
            $path = rtrim($this->config['output_dir'], '/\\') . DIRECTORY_SEPARATOR . $filename;
            file_put_contents($path, $data);
            return $path;
        } catch (Exception $e) {
            $this->log("⚠️ Lỗi tải ảnh bài viết: " . $e->getMessage());
            return null;
        }
    }

    private function imageUrlLooksLogoLike($url) {
        $url = strtolower((string)$url);
        return preg_match('/(logo|watermark|wm-|avatar|icon|sprite|favicon|badge|brand|placeholder|loading)/i', $url);
    }

    private function imageFileLooksCleanForPost($path, &$reason = '') {
        $reason = '';
        if (!file_exists($path)) {
            $reason = 'file khong ton tai';
            return false;
        }

        $size = @getimagesize($path);
        if (!$size || empty($size[0]) || empty($size[1])) {
            $reason = 'khong doc duoc kich thuoc anh';
            return false;
        }

        $width = (int)$size[0];
        $height = (int)$size[1];
        $min_width = max(120, (int)($this->config['min_post_image_width'] ?? 420));
        $min_height = max(120, (int)($this->config['min_post_image_height'] ?? 220));

        if ($width < $min_width || $height < $min_height) {
            $reason = "anh qua nho {$width}x{$height}";
            return false;
        }

        $ratio = $width / max(1, $height);
        if ($ratio > 3.4 || $ratio < 0.35) {
            $reason = "ti le anh bat thuong {$width}x{$height}";
            return false;
        }

        if (filesize($path) < 25 * 1024) {
            $reason = 'dung luong anh qua nho';
            return false;
        }

        return true;
    }

    private function imageExtension($content_type, $url) {
        $content_type = strtolower((string) $content_type);
        if (strpos($content_type, 'png') !== false) return 'png';
        if (strpos($content_type, 'webp') !== false) return 'webp';
        if (strpos($content_type, 'gif') !== false) return 'gif';
        if (preg_match('/\.(png|jpe?g|webp|gif)(\?|$)/i', $url, $m)) {
            return strtolower($m[1] === 'jpeg' ? 'jpg' : $m[1]);
        }
        return 'jpg';
    }

    /**
     * ═══════════════════════════════════════════════
     *  CÁC PROMPT AI
     * ═══════════════════════════════════════════════
     */

    /**
     * Prompt tóm tắt & tạo bài đăng tổng hợp
     */
    private function contentTemplateInstruction() {
        $template = $this->config['content_template'] ?? 'tin_nong';
        $map = [
            'tin_nong' => '- Phong cách: tin nóng, mở đầu mạnh, cập nhật nhanh, ưu tiên dữ kiện mới nhất.',
            'nhan_dinh' => '- Phong cách: nhận định, có góc nhìn chuyên môn, nêu bối cảnh và tác động.',
            'tranh_luan' => '- Phong cách: tranh luận, đặt câu hỏi mở, khơi ý kiến trái chiều nhưng không giật tít quá đà.',
            'chuyen_nhuong' => '- Phong cách: chuyển nhượng, nhấn khả năng xảy ra, tác động đội hình và kỳ vọng.',
            'lich_thi_dau' => '- Phong cách: lịch thi đấu, rõ thời gian, đối thủ, điểm đáng xem và lời mời dự đoán.',
            'sau_tran' => '- Phong cách: sau trận, tóm điểm nhấn, nhân vật nổi bật và cảm xúc sau trận.',
        ];
        return $map[$template] ?? $map['tin_nong'];
    }

    private function buildSummaryPrompt($compiled_content) {
        $style_instruction = $this->contentTemplateInstruction();
        return "Bạn là một chuyên gia content bóng đá chuyên viết bài đăng Fanpage Facebook có khả năng tạo tương tác cao.

Dưới đây là nội dung tin tức bóng đá hôm nay:

--- NỘI DUNG ---
{$compiled_content}
--- HẾT NỘI DUNG ---

Hãy thực hiện:

{$style_instruction}

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
     * Prompt cho bài cập nhật hằng ngày từ link người dùng gửi.
     */
    private function buildDailyLinksPrompt($compiled_content) {
        $style_instruction = $this->contentTemplateInstruction();
        return "Bạn là biên tập viên fanpage bóng đá. Người dùng đã gửi các link bài viết để tạo một bài cập nhật hằng ngày.

--- DỮ LIỆU TỪ LINK ---
{$compiled_content}
--- HẾT DỮ LIỆU ---

Hãy viết MỘT bài đăng Facebook tiếng Việt theo phong cách cập nhật trong ngày:
{$style_instruction}
- Mở đầu bằng hook ngắn, đúng trọng tâm, có ngày hôm nay nếu phù hợp
- Gom các tin thành 3-5 gạch đầu dòng rõ ràng, mỗi tin 1-2 câu
- Chỉ dùng thông tin có trong dữ liệu, không bịa thêm chi tiết
- Viết tự nhiên, dễ đọc, phù hợp fanpage bóng đá
- Có câu hỏi mở cuối bài để kéo bình luận
- Thêm 3-6 hashtag phù hợp
- Tổng bài khoảng 150-260 từ
- Không ghi phần giải thích, không ghi 'dưới đây là', chỉ trả về nội dung bài đăng sẵn sàng đăng

Lưu ý: app sẽ tự đính kèm ảnh lấy từ link bài viết, nên caption phải hợp với ảnh tin tức bóng đá.";
    }

    /**
     * Prompt tạo bài đăng cho một tin đơn lẻ
     */
    private function buildSinglePostPrompt($title, $content) {
        $style_instruction = $this->contentTemplateInstruction();
        return "Bạn là chuyên gia content bóng đá. Viết bài đăng Facebook từ tin tức sau:

Tiêu đề: {$title}
Nội dung: {$content}

Yêu cầu:
{$style_instruction}
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

        return "A stunning professional football news banner composition. Dynamic football action scene with dramatic stadium lighting, green pitch, football/soccer ball in motion, vibrant atmosphere with fans silhouettes in background. Modern sports media design with bold colors (green, blue, gold accents). Text-free clean design, no logo, no watermark, no brand mark, 4K ultra quality, cinematic sports photography style. Topic context: Vietnamese football news today.";
    }

    /**
     * ═══════════════════════════════════════════════
     *  GỌI API
     * ═══════════════════════════════════════════════
     */

    /**
     * Dispatcher AI: ưu tiên công cụ miễn phí trước.
     * Trả về ['success', 'text', 'provider']
     */
    private function callAI($prompt) {
        $free_only = !empty($this->config['free_ai_only']);

        // Ưu tiên Ollama local nếu có
        if (!empty($this->ollama_base_url)) {
            $result = $this->callOllama($prompt);
            if ($this->isUsableAIResult($result)) {
                return $result;
            }
            $this->log("⚠️ Ollama thất bại ({$result['message']}), thử Hugging Face...");
        }

        // Hugging Face free tier
        if (!empty($this->hf_token)) {
            $result = $this->callHuggingFace($prompt);
            if ($this->isUsableAIResult($result)) {
                return $result;
            }
            $this->log("⚠️ Hugging Face thất bại ({$result['message']}), thử Gemini...");
        }

        // Gemini fallback
        if (!empty($this->gemini_api_key)) {
            $result = $this->callGemini($prompt);
            if ($this->isUsableAIResult($result)) {
                return $result;
            }
            $this->log("⚠️ Gemini cũng thất bại: " . $result['message']);
            if ($free_only) {
                return $result;
            }
        }

        if ($free_only) {
            return ['success' => false, 'text' => '', 'provider' => 'none', 'message' => 'Chưa cấu hình Ollama, Hugging Face hoặc Gemini free-tier'];
        }

        // Fallback OpenAI / Grok nếu người dùng muốn dùng dịch vụ trả phí
        if (!empty($this->openai_api_key)) {
            $result = $this->callOpenAI($prompt);
            if ($this->isUsableAIResult($result)) {
                return $result;
            }
            $next_ai = !empty($this->grok_api_key) ? 'thử Grok...' : 'chưa có Grok key, thử Gemini...';
            $this->log("⚠️ ChatGPT thất bại ({$result['message']}), {$next_ai}");
        }

        if (!empty($this->grok_api_key)) {
            $result = $this->callGrok($prompt);
            if ($this->isUsableAIResult($result)) {
                return $result;
            }
            $this->log("⚠️ Grok thất bại ({$result['message']}), thử Gemini...");
        }

        return ['success' => false, 'text' => '', 'provider' => 'none', 'message' => 'Không có AI provider nào được cấu hình'];
    }

    /**
     * Ollama local API - miễn phí, chạy trên máy người dùng.
     */
    private function isUsableAIResult(&$result) {
        if (empty($result['success'])) {
            return false;
        }

        $text = trim((string)($result['text'] ?? ''));
        if (mb_strlen($text) < 280) {
            $result['success'] = false;
            $result['message'] = 'AI trả về caption quá ngắn hoặc bị cắt giữa chừng';
            $provider = strtoupper($result['provider'] ?? 'AI');
            $this->log("⚠️ {$provider} trả về caption quá ngắn, bỏ qua kết quả này");
            return false;
        }

        return true;
    }

    private function callOllama($prompt) {
        try {
            $model = $this->config['ollama_model'] ?? 'gemma3';
            $url = rtrim($this->ollama_base_url, '/') . '/api/chat';
            $data = [
                'model' => $model,
                'messages' => [
                    [
                        'role' => 'system',
                        'content' => 'Bạn là chuyên gia content bóng đá Việt Nam. Viết bài đăng Facebook hấp dẫn, tự nhiên, giàu cảm xúc bằng tiếng Việt.'
                    ],
                    [
                        'role' => 'user',
                        'content' => $prompt
                    ]
                ],
                'stream' => false
            ];

            $response = $this->makeRequest($url, $data);
            if (!$response['success']) {
                return ['success' => false, 'text' => '', 'provider' => 'ollama', 'message' => $response['message']];
            }

            $result = $response['data'];
            $text = $result['message']['content'] ?? '';
            if (!empty($text)) {
                $this->log("✅ Ollama ({$model}) tạo bài thành công");
                return ['success' => true, 'text' => trim($text), 'provider' => 'ollama'];
            }

            return ['success' => false, 'text' => '', 'provider' => 'ollama', 'message' => 'Ollama không trả về nội dung'];
        } catch (Exception $e) {
            return ['success' => false, 'text' => '', 'provider' => 'ollama', 'message' => $e->getMessage()];
        }
    }

    /**
     * Hugging Face free tier via router API.
     */
    private function callHuggingFace($prompt) {
        try {
            $model = $this->config['hf_model'] ?? 'deepseek-ai/DeepSeek-R1:fastest';
            $url = 'https://router.huggingface.co/v1/chat/completions';

            $data = [
                'model' => $model,
                'messages' => [
                    [
                        'role' => 'system',
                        'content' => 'Bạn là chuyên gia content bóng đá Việt Nam. Viết bài đăng Facebook hấp dẫn, tự nhiên, giàu cảm xúc bằng tiếng Việt.'
                    ],
                    [
                        'role' => 'user',
                        'content' => $prompt
                    ]
                ],
                'temperature' => 0.8,
                'max_tokens' => 1024,
            ];

            $ch = curl_init();
            $json_data = json_encode($data, JSON_UNESCAPED_UNICODE);
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $json_data,
                CURLOPT_TIMEOUT => 60,
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Authorization: Bearer ' . $this->hf_token,
                    'Content-Length: ' . strlen($json_data)
                ]
            ]);

            $result = curl_exec($ch);
            $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $error = curl_error($ch);
            curl_close($ch);

            if ($error) {
                return ['success' => false, 'text' => '', 'provider' => 'huggingface', 'message' => "cURL: $error"];
            }

            $decoded = json_decode($result, true);
            if ($http_code >= 200 && $http_code < 300 && isset($decoded['choices'][0]['message']['content'])) {
                $text = trim($decoded['choices'][0]['message']['content']);
                $this->log("✅ Hugging Face ({$model}) tạo bài thành công");
                return ['success' => true, 'text' => $text, 'provider' => 'huggingface'];
            }

            $err_msg = $decoded['error']['message'] ?? "HTTP $http_code";
            return ['success' => false, 'text' => '', 'provider' => 'huggingface', 'message' => $err_msg];
        } catch (Exception $e) {
            return ['success' => false, 'text' => '', 'provider' => 'huggingface', 'message' => $e->getMessage()];
        }
    }

    /**
     * Gọi ChatGPT / OpenAI Responses API để tạo text.
     */
    private function callOpenAI($prompt) {
        try {
            $url = 'https://api.openai.com/v1/responses';
            $model = $this->config['openai_model'] ?? 'chat-latest';

            $data = [
                'model' => $model,
                'instructions' => 'Bạn là chuyên gia content bóng đá Việt Nam. Viết bài đăng Facebook hấp dẫn, tự nhiên, giàu cảm xúc bằng tiếng Việt.',
                'input' => $prompt,
            ];

            $ch = curl_init();
            $json_data = json_encode($data, JSON_UNESCAPED_UNICODE);
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $json_data,
                CURLOPT_TIMEOUT => 60,
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Authorization: Bearer ' . $this->openai_api_key,
                    'Content-Length: ' . strlen($json_data)
                ]
            ]);

            $result = curl_exec($ch);
            $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $error = curl_error($ch);
            curl_close($ch);

            if ($error) {
                return ['success' => false, 'text' => '', 'provider' => 'openai', 'message' => "cURL: $error"];
            }

            $decoded = json_decode($result, true);
            $text = $this->extractOpenAIText($decoded);

            if ($http_code >= 200 && $http_code < 300 && !empty($text)) {
                $this->log("✅ ChatGPT/OpenAI ({$model}) tạo bài thành công");
                return ['success' => true, 'text' => $text, 'provider' => 'openai'];
            }

            $err_msg = $decoded['error']['message'] ?? "HTTP $http_code";
            return ['success' => false, 'text' => '', 'provider' => 'openai', 'message' => $err_msg];

        } catch (Exception $e) {
            return ['success' => false, 'text' => '', 'provider' => 'openai', 'message' => $e->getMessage()];
        }
    }

    private function extractOpenAIText($decoded) {
        if (!is_array($decoded)) {
            return '';
        }
        if (!empty($decoded['output_text']) && is_string($decoded['output_text'])) {
            return trim($decoded['output_text']);
        }
        foreach (($decoded['output'] ?? []) as $item) {
            foreach (($item['content'] ?? []) as $content) {
                if (!empty($content['text']) && in_array($content['type'] ?? '', ['output_text', 'text'], true)) {
                    return trim($content['text']);
                }
            }
        }
        return '';
    }

    /**
     * Gọi Grok API (xAI) — OpenAI-compatible
     */
    private function callGrok($prompt) {
        try {
            $url = 'https://api.x.ai/v1/chat/completions';
            $model = $this->config['grok_model'] ?? 'grok-3-mini-fast';

            $data = [
                'model' => $model,
                'messages' => [
                    [
                        'role' => 'system',
                        'content' => 'Bạn là chuyên gia content bóng đá Việt Nam. Viết bài đăng Facebook hấp dẫn, tự nhiên, giàu cảm xúc bằng tiếng Việt.'
                    ],
                    [
                        'role' => 'user',
                        'content' => $prompt
                    ]
                ],
                'temperature' => 0.8,
                'max_tokens' => 1024,
            ];

            $ch = curl_init();
            $json_data = json_encode($data);
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $json_data,
                CURLOPT_TIMEOUT => 60,
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Authorization: Bearer ' . $this->grok_api_key,
                    'Content-Length: ' . strlen($json_data)
                ]
            ]);

            $result = curl_exec($ch);
            $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $error = curl_error($ch);
            curl_close($ch);

            if ($error) {
                return ['success' => false, 'text' => '', 'provider' => 'grok', 'message' => "cURL: $error"];
            }

            $decoded = json_decode($result, true);

            if ($http_code >= 200 && $http_code < 300 && isset($decoded['choices'][0]['message']['content'])) {
                $text = trim($decoded['choices'][0]['message']['content']);
                $this->log("✅ Grok ({$model}) tạo bài thành công");
                return ['success' => true, 'text' => $text, 'provider' => 'grok'];
            }

            $err_msg = $decoded['error']['message'] ?? "HTTP $http_code";
            return ['success' => false, 'text' => '', 'provider' => 'grok', 'message' => $err_msg];

        } catch (Exception $e) {
            return ['success' => false, 'text' => '', 'provider' => 'grok', 'message' => $e->getMessage()];
        }
    }

    /**
     * Gọi Gemini API để tạo text (fallback)
     */
    private function callGemini($prompt) {
        try {
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

            $last_message = '';
            foreach ($this->geminiTextModels() as $model) {
                $url = "https://generativelanguage.googleapis.com/v1beta/models/{$model}:generateContent?key=" . $this->gemini_api_key;
                $response = $this->makeRequest($url, $data);

                if (!$response['success']) {
                    $last_message = $response['message'];
                    $this->log("⚠️ Gemini model {$model} thất bại: {$last_message}");
                    continue;
                }

                $result = $response['data'];

                if (isset($result['candidates'][0]['content']['parts'][0]['text'])) {
                    $text = trim($result['candidates'][0]['content']['parts'][0]['text']);
                    if (mb_strlen($text) < 280) {
                        $last_message = 'Gemini trả về caption quá ngắn hoặc bị cắt giữa chừng';
                        $this->log("⚠️ Gemini model {$model} trả về caption quá ngắn, thử model tiếp theo...");
                        continue;
                    }
                    $this->log("✅ Gemini ({$model}) tạo bài thành công");
                    return ['success' => true, 'text' => $text, 'provider' => 'gemini'];
                }

                $last_message = 'Gemini không trả về kết quả';
                $this->log("⚠️ Gemini model {$model} không trả về nội dung");
            }

            return ['success' => false, 'text' => '', 'provider' => 'gemini', 'message' => $last_message ?: 'Không có Gemini model khả dụng'];

        } catch (Exception $e) {
            return ['success' => false, 'text' => '', 'provider' => 'gemini', 'message' => $e->getMessage()];
        }
    }

    private function geminiTextModels() {
        $configured = $this->config['gemini_model'] ?? '';
        $models = [
            $configured,
            'gemini-2.5-flash-lite',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-flash-latest',
        ];

        $clean = [];
        foreach ($models as $model) {
            $model = trim(str_replace('models/', '', (string) $model));
            if ($model !== '' && !in_array($model, $clean, true)) {
                $clean[] = $model;
            }
        }
        return $clean;
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
     * Lưu output ra file txt + json (để Python chrome_poster.py đọc)
     */
    private function saveOutput($name, $content, $image_path = null, $articles = [], $ai_provider = 'unknown', $image_paths = []) {
        $timestamp = date('Ymd_His');

        // Lưu txt
        $txt_file = $this->config['output_dir'] . $name . '_' . $timestamp . '.txt';
        file_put_contents($txt_file, $content);

        // Lưu JSON (chrome_poster.py sẽ đọc file này)
        $json_file = $this->config['output_dir'] . 'latest_post.json';
        $json_data = json_encode([
            'post_content' => $content,
            'timestamp'    => date('Y-m-d H:i:s'),
            'source_file'  => basename($txt_file),
            'image_path'    => $image_path,
            'image_paths'   => array_values(array_filter($image_paths ?: [$image_path])),
            'ai_provider'   => $ai_provider,
            'article_links' => array_values(array_filter(array_map(function($article) {
                return $article['link'] ?? '';
            }, $articles))),
        ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
        file_put_contents($json_file, $json_data);
        $this->rememberArticleHistory($articles);

        $this->log("💾 Đã lưu output: $txt_file");
        $this->log("📋 JSON sẵn sàng cho Chrome poster: $json_file");
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
        $articles = $this->fetchInputArticles();
        if (empty($articles)) {
            return [
                'articles' => [],
                'compiled_content' => 'Không có tin mới sau khi lọc trùng.'
            ];
        }
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
        $articles = $this->fetchInputArticles();
        if (empty($articles)) {
            return [
                'articles_count' => 0,
                'post_content' => 'Không có tin mới sau khi lọc trùng. Hãy thêm link mới hoặc chờ nguồn tin mới cập nhật.',
                'status' => 'error',
                'ai_provider' => 'dedupe',
                'image_path' => null,
                'image_paths' => [],
            ];
        }
        $used_articles = $articles;
        if (($this->config['post_style'] ?? 'tong_hop') === 'don_le') {
            $article = $articles[0];
            $used_articles = [$article];
            $content = !empty($article['description']) ? $article['description'] : ($article['title'] ?? '');
            if (!empty($this->config['fetch_full_content']) && !empty($article['link'])) {
                $full = $this->scraper->fetchArticleContent($article['link']);
                if (!empty($full)) {
                    $content = $full;
                }
            }
            $prompt = $this->buildSinglePostPrompt($article['title'] ?? '', $content);
        } else {
            $compiled = $this->scraper->compileNewsContent($articles, $this->config['fetch_full_content']);
            $prompt = $this->hasManualLinks()
                ? $this->buildDailyLinksPrompt($compiled)
                : $this->buildSummaryPrompt($compiled);
        }

        $result = $this->callAI($prompt);
        $image_paths = $result['success'] ? $this->downloadArticleImages($used_articles) : [];
        $image_path = $image_paths[0] ?? null;

        if ($result['success']) {
            $name = (($this->config['post_style'] ?? 'tong_hop') === 'don_le') ? 'single_post' : 'summary_post';
            $this->saveOutput($name, $result['text'], $image_path, $used_articles, $result['provider'] ?? 'unknown', $image_paths);
        }

        return [
            'articles_count' => count($articles),
            'post_content' => $result['success'] ? $result['text'] : 'Lỗi: ' . $result['message'],
            'status' => $result['success'] ? 'success' : 'error',
            'ai_provider' => $result['provider'] ?? 'unknown',
            'image_path' => $image_path,
            'image_paths' => $image_paths,
        ];
    }
}

?>
