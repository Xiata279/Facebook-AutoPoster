<?php

/**
 * Football News Scraper
 * 
 * Thu thập tin tức bóng đá từ các nguồn Việt Nam.
 * Hỗ trợ RSS feed và HTML scraping.
 * 
 * Nguồn hỗ trợ:
 * - VnExpress Bóng đá
 * - BongDa.com.vn
 * - 24h.com.vn Bóng đá
 * - TheThao247.vn
 * 
 * @author Xiata
 * @version 1.0.0
 */

class FootballNewsScraper {

    private $sources;
    private $log_file;
    private $cache_dir;
    private $max_articles_per_source;
    private $date_filter; // 'today', 'yesterday', 'both'

    /**
     * Khởi tạo
     * 
     * @param array $config Cấu hình
     */
    public function __construct($config = []) {
        $this->log_file = $config['log_file'] ?? './logs/scraper.log';
        $this->cache_dir = $config['cache_dir'] ?? './cache/';
        $this->max_articles_per_source = $config['max_articles'] ?? 5;
        $this->date_filter = $config['date_filter'] ?? 'both'; // today, yesterday, both

        // Tạo thư mục nếu chưa tồn tại
        if (!is_dir($this->cache_dir)) {
            mkdir($this->cache_dir, 0755, true);
        }
        if (!is_dir(dirname($this->log_file))) {
            mkdir(dirname($this->log_file), 0755, true);
        }

        // Cấu hình các nguồn tin
        $this->sources = [
            'vnexpress' => [
                'name' => 'VnExpress Bóng đá',
                'type' => 'rss',
                'url' => 'https://vnexpress.net/rss/bong-da.rss',
                'encoding' => 'UTF-8'
            ],
            '24h' => [
                'name' => '24h Bóng đá',
                'type' => 'rss',
                'url' => 'https://www.24h.com.vn/upload/rss/bongda.rss',
                'encoding' => 'UTF-8'
            ],
            'bongda' => [
                'name' => 'BongDa.com.vn',
                'type' => 'html',
                'url' => 'https://bongda.com.vn/',
                'encoding' => 'UTF-8'
            ],
            'thethao247' => [
                'name' => 'TheThao247',
                'type' => 'html',
                'url' => 'https://thethao247.vn/bong-da/',
                'encoding' => 'UTF-8'
            ]
        ];
    }

    /**
     * Thu thập tin tức từ tất cả các nguồn
     * 
     * @return array Danh sách bài viết
     */
    public function fetchAllNews() {
        $all_articles = [];

        foreach ($this->sources as $key => $source) {
            $this->log("Đang thu thập tin từ: {$source['name']}");

            try {
                if ($source['type'] === 'rss') {
                    $articles = $this->fetchRSS($source);
                } else {
                    $articles = $this->fetchHTML($key, $source);
                }

                // Lọc theo ngày
                $articles = $this->filterByDate($articles);

                // Giới hạn số bài
                $articles = array_slice($articles, 0, $this->max_articles_per_source);

                $this->log("Đã thu thập {$this->countArticles($articles)} tin từ {$source['name']}");
                $all_articles = array_merge($all_articles, $articles);

            } catch (Exception $e) {
                $this->log("Lỗi khi thu thập từ {$source['name']}: " . $e->getMessage());
            }
        }

        // Sắp xếp theo thời gian mới nhất
        usort($all_articles, function($a, $b) {
            return strtotime($b['published_at'] ?? '0') - strtotime($a['published_at'] ?? '0');
        });

        $this->log("Tổng cộng đã thu thập " . count($all_articles) . " tin tức");

        // Lưu cache
        $this->saveCache($all_articles);

        return $all_articles;
    }

    /**
     * Thu thập từ một nguồn cụ thể
     * 
     * @param string $source_key Tên nguồn (vnexpress, 24h, bongda, thethao247)
     * @return array
     */
    public function fetchFromSource($source_key) {
        if (!isset($this->sources[$source_key])) {
            $this->log("Nguồn không hợp lệ: $source_key");
            return [];
        }

        $source = $this->sources[$source_key];
        $this->log("Đang thu thập tin từ: {$source['name']}");

        try {
            if ($source['type'] === 'rss') {
                $articles = $this->fetchRSS($source);
            } else {
                $articles = $this->fetchHTML($source_key, $source);
            }

            $articles = $this->filterByDate($articles);
            $articles = array_slice($articles, 0, $this->max_articles_per_source);

            $this->log("Đã thu thập " . count($articles) . " tin từ {$source['name']}");
            return $articles;

        } catch (Exception $e) {
            $this->log("Lỗi: " . $e->getMessage());
            return [];
        }
    }

    /**
     * Thu thập tin từ RSS feed
     * 
     * @param array $source Thông tin nguồn
     * @return array
     */
    private function fetchRSS($source) {
        $articles = [];
        $xml_content = $this->httpGet($source['url']);

        if (empty($xml_content)) {
            throw new Exception("Không thể tải RSS từ {$source['url']}");
        }

        // Tắt báo lỗi XML
        libxml_use_internal_errors(true);
        $xml = simplexml_load_string($xml_content);

        if ($xml === false) {
            throw new Exception("Không thể phân tích RSS từ {$source['name']}");
        }

        $items = $xml->channel->item ?? [];

        foreach ($items as $item) {
            $title = trim((string)($item->title ?? ''));
            $link = trim((string)($item->link ?? ''));
            $description = trim(strip_tags((string)($item->description ?? '')));
            $pub_date = trim((string)($item->pubDate ?? ''));

            if (empty($title)) continue;

            // Lấy ảnh từ description nếu có
            $image = '';
            $desc_raw = (string)($item->description ?? '');
            if (preg_match('/<img[^>]+src=["\']([^"\']+)["\']/i', $desc_raw, $matches)) {
                $image = $matches[1];
            }

            $articles[] = [
                'title' => $title,
                'link' => $link,
                'description' => $description,
                'image' => $image,
                'published_at' => $pub_date ? date('Y-m-d H:i:s', strtotime($pub_date)) : date('Y-m-d H:i:s'),
                'source' => $source['name'],
                'full_content' => '' // Sẽ được lấy sau nếu cần
            ];
        }

        return $articles;
    }

    /**
     * Thu thập tin từ HTML (web scraping)
     * 
     * @param string $key Tên nguồn
     * @param array $source Thông tin nguồn
     * @return array
     */
    private function fetchHTML($key, $source) {
        $articles = [];
        $html = $this->httpGet($source['url']);

        if (empty($html)) {
            throw new Exception("Không thể tải trang từ {$source['url']}");
        }

        libxml_use_internal_errors(true);
        $doc = new DOMDocument();
        $doc->loadHTML('<?xml encoding="UTF-8">' . $html);
        $xpath = new DOMXPath($doc);

        switch ($key) {
            case 'bongda':
                $articles = $this->parseBongDa($xpath, $source);
                break;
            case 'thethao247':
                $articles = $this->parseTheThao247($xpath, $source);
                break;
        }

        return $articles;
    }

    /**
     * Phân tích trang BongDa.com.vn
     */
    private function parseBongDa($xpath, $source) {
        $articles = [];

        // Tìm các bài viết chính
        $nodes = $xpath->query('//article | //div[contains(@class, "news-item")] | //div[contains(@class, "item-news")] | //h2/a | //h3/a');

        $seen_titles = [];
        foreach ($nodes as $node) {
            $title = '';
            $link = '';
            $description = '';
            $image = '';

            if ($node->tagName === 'a') {
                $title = trim($node->textContent);
                $link = $node->getAttribute('href');
            } else {
                // Tìm title trong article/div
                $title_node = $xpath->query('.//h2/a | .//h3/a | .//a[contains(@class, "title")]', $node);
                if ($title_node->length > 0) {
                    $title = trim($title_node->item(0)->textContent);
                    $link = $title_node->item(0)->getAttribute('href');
                }

                // Tìm description
                $desc_node = $xpath->query('.//p | .//div[contains(@class, "desc")] | .//span[contains(@class, "desc")]', $node);
                if ($desc_node->length > 0) {
                    $description = trim($desc_node->item(0)->textContent);
                }

                // Tìm ảnh
                $img_node = $xpath->query('.//img', $node);
                if ($img_node->length > 0) {
                    $image = $img_node->item(0)->getAttribute('src') ?: $img_node->item(0)->getAttribute('data-src');
                }
            }

            if (empty($title) || strlen($title) < 10) continue;
            if (isset($seen_titles[$title])) continue;
            $seen_titles[$title] = true;

            // Hoàn thiện link
            if ($link && !preg_match('/^https?:\/\//', $link)) {
                $link = 'https://bongda.com.vn' . $link;
            }

            $articles[] = [
                'title' => $title,
                'link' => $link,
                'description' => $description,
                'image' => $image,
                'published_at' => date('Y-m-d H:i:s'),
                'source' => $source['name'],
                'full_content' => ''
            ];
        }

        return $articles;
    }

    /**
     * Phân tích trang TheThao247.vn
     */
    private function parseTheThao247($xpath, $source) {
        $articles = [];

        $nodes = $xpath->query('//article | //div[contains(@class, "news")] | //div[contains(@class, "item")] | //div[contains(@class, "story")]');

        $seen_titles = [];
        foreach ($nodes as $node) {
            $title = '';
            $link = '';
            $description = '';
            $image = '';

            $title_node = $xpath->query('.//h2/a | .//h3/a | .//a[contains(@class, "title")] | .//a', $node);
            if ($title_node->length > 0) {
                $title = trim($title_node->item(0)->textContent);
                $link = $title_node->item(0)->getAttribute('href');
            }

            $desc_node = $xpath->query('.//p | .//div[contains(@class, "sapo")] | .//span[contains(@class, "desc")]', $node);
            if ($desc_node->length > 0) {
                $description = trim($desc_node->item(0)->textContent);
            }

            $img_node = $xpath->query('.//img', $node);
            if ($img_node->length > 0) {
                $image = $img_node->item(0)->getAttribute('src') ?: $img_node->item(0)->getAttribute('data-src');
            }

            if (empty($title) || strlen($title) < 10) continue;
            if (isset($seen_titles[$title])) continue;
            $seen_titles[$title] = true;

            if ($link && !preg_match('/^https?:\/\//', $link)) {
                $link = 'https://thethao247.vn' . $link;
            }

            $articles[] = [
                'title' => $title,
                'link' => $link,
                'description' => $description,
                'image' => $image,
                'published_at' => date('Y-m-d H:i:s'),
                'source' => $source['name'],
                'full_content' => ''
            ];
        }

        return $articles;
    }

    /**
     * Lấy nội dung đầy đủ của một bài viết từ link
     * 
     * @param string $url Link bài viết
     * @return string Nội dung bài viết
     */
    public function fetchArticleContent($url) {
        try {
            $html = $this->httpGet($url);
            if (empty($html)) return '';

            libxml_use_internal_errors(true);
            $doc = new DOMDocument();
            $doc->loadHTML('<?xml encoding="UTF-8">' . $html);
            $xpath = new DOMXPath($doc);

            // Tìm nội dung bài viết - thử nhiều selector phổ biến
            $selectors = [
                '//article//div[contains(@class, "content")]',
                '//div[contains(@class, "fck_detail")]',
                '//div[contains(@class, "article-body")]',
                '//div[contains(@class, "detail-content")]',
                '//div[contains(@class, "content-detail")]',
                '//div[contains(@class, "the_content")]',
                '//div[contains(@class, "post-content")]',
                '//div[@id="main-detail-body"]',
                '//article',
            ];

            foreach ($selectors as $selector) {
                $nodes = $xpath->query($selector);
                if ($nodes->length > 0) {
                    $content = '';
                    $paragraphs = $xpath->query('.//p', $nodes->item(0));
                    foreach ($paragraphs as $p) {
                        $text = trim($p->textContent);
                        if (!empty($text) && strlen($text) > 20) {
                            $content .= $text . "\n\n";
                        }
                    }
                    if (!empty($content)) {
                        return trim($content);
                    }
                }
            }

            return '';
        } catch (Exception $e) {
            $this->log("Lỗi khi lấy nội dung bài viết: " . $e->getMessage());
            return '';
        }
    }

    /**
     * Lọc bài viết theo ngày
     */
    private function filterByDate($articles) {
        $today = date('Y-m-d');
        $yesterday = date('Y-m-d', strtotime('-1 day'));

        return array_filter($articles, function($article) use ($today, $yesterday) {
            $article_date = date('Y-m-d', strtotime($article['published_at'] ?? 'now'));

            switch ($this->date_filter) {
                case 'today':
                    return $article_date === $today;
                case 'yesterday':
                    return $article_date === $yesterday;
                case 'both':
                default:
                    return $article_date === $today || $article_date === $yesterday;
            }
        });
    }

    /**
     * Tổng hợp nội dung tin tức thành một văn bản
     * 
     * @param array $articles Danh sách bài viết
     * @param bool $fetch_full_content Có lấy nội dung đầy đủ không
     * @return string
     */
    public function compileNewsContent($articles, $fetch_full_content = false) {
        $content = "=== TIN TỨC BÓNG ĐÁ HÔM NAY (" . date('d/m/Y') . ") ===\n\n";

        foreach ($articles as $index => $article) {
            $num = $index + 1;
            $content .= "--- TIN {$num} ---\n";
            $content .= "Tiêu đề: {$article['title']}\n";
            $content .= "Nguồn: {$article['source']}\n";
            $content .= "Thời gian: {$article['published_at']}\n";

            if (!empty($article['description'])) {
                $content .= "Mô tả: {$article['description']}\n";
            }

            if ($fetch_full_content && !empty($article['link'])) {
                $this->log("Đang lấy nội dung đầy đủ từ: {$article['link']}");
                $full = $this->fetchArticleContent($article['link']);
                if (!empty($full)) {
                    $content .= "Nội dung:\n{$full}\n";
                }
                // Tránh bị chặn bởi rate limit
                usleep(500000); // 0.5 giây
            }

            $content .= "Link: {$article['link']}\n";
            $content .= "---\n\n";
        }

        return $content;
    }

    /**
     * Lưu cache tin tức
     */
    private function saveCache($articles) {
        $cache_file = $this->cache_dir . 'news_' . date('Y-m-d') . '.json';
        file_put_contents($cache_file, json_encode($articles, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        $this->log("Đã lưu cache: $cache_file");
    }

    /**
     * Tải cache tin tức
     * 
     * @return array|null
     */
    public function loadCache() {
        $cache_file = $this->cache_dir . 'news_' . date('Y-m-d') . '.json';
        if (file_exists($cache_file)) {
            $data = json_decode(file_get_contents($cache_file), true);
            if (json_last_error() === JSON_ERROR_NONE) {
                $this->log("Đã tải cache: $cache_file");
                return $data;
            }
        }
        return null;
    }

    /**
     * HTTP GET request
     */
    private function httpGet($url) {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_CONNECTTIMEOUT => 10,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            CURLOPT_HTTPHEADER => [
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: vi-VN,vi;q=0.9,en;q=0.8',
            ]
        ]);

        $result = curl_exec($ch);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            $this->log("Lỗi HTTP: $error (URL: $url)");
            return '';
        }

        return $result;
    }

    /**
     * Đếm số bài viết
     */
    private function countArticles($articles) {
        return is_array($articles) ? count($articles) : 0;
    }

    /**
     * Ghi log
     */
    private function log($message) {
        $log_entry = date('Y-m-d H:i:s') . " [Scraper] " . $message . PHP_EOL;
        file_put_contents($this->log_file, $log_entry, FILE_APPEND | LOCK_EX);
    }

    /**
     * Lấy danh sách các nguồn tin
     * 
     * @return array
     */
    public function getSources() {
        return $this->sources;
    }
}

?>
