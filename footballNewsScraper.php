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
            'vnexpress_thethao' => [
                'name' => 'VnExpress Thể thao',
                'type' => 'rss',
                'url' => 'https://vnexpress.net/rss/the-thao.rss',
                'encoding' => 'UTF-8'
            ],
            'vnexpress_quocte' => [
                'name' => 'VnExpress Bóng đá Quốc tế',
                'type' => 'rss',
                'url' => 'https://vnexpress.net/rss/bong-da-quoc-te.rss',
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

        $before_dedupe = count($all_articles);
        $all_articles = $this->deduplicateArticles($all_articles);
        $removed = $before_dedupe - count($all_articles);
        if ($removed > 0) {
            $this->log("Đã loại {$removed} tin trùng trong lần quét hiện tại");
        }

        $this->log("Tổng cộng đã thu thập " . count($all_articles) . " tin tức sau khi lọc trùng");

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
            $articles = $this->deduplicateArticles($articles);
            $articles = array_slice($articles, 0, $this->max_articles_per_source);

            $this->log("Đã thu thập " . count($articles) . " tin từ {$source['name']}");
            return $articles;

        } catch (Exception $e) {
            $this->log("Lỗi: " . $e->getMessage());
            return [];
        }
    }

    /**
     * Thu thập bài viết từ danh sách link người dùng gửi.
     *
     * @param array $links Danh sách URL bài viết
     * @return array
     */
    public function fetchFromLinks($links) {
        $articles = [];
        $seen = [];

        foreach ($links as $url) {
            $url = trim($url);
            if (!$this->isValidUrl($url) || isset($seen[$url])) {
                continue;
            }
            $seen[$url] = true;

            if ($this->isLikelyListingUrl($url)) {
                $listing_articles = $this->fetchArticlesFromListingUrl($url, 8);
                if (!empty($listing_articles)) {
                    $articles = array_merge($articles, $listing_articles);
                    $this->log("Đã lấy " . count($listing_articles) . " tin từ trang chuyên mục: {$url}");
                    usleep(350000);
                    continue;
                }
            }

            $this->log("Đang đọc bài viết từ link: {$url}");
            $article = $this->fetchArticleFromUrl($url);
            if (!empty($article['title']) || !empty($article['full_content'])) {
                $articles[] = $article;
            }

            usleep(350000);
        }

        $before_dedupe = count($articles);
        $articles = $this->deduplicateArticles($articles);
        $removed = $before_dedupe - count($articles);
        if ($removed > 0) {
            $this->log("Đã loại {$removed} link/bài thủ công bị trùng");
        }

        $this->log("Đã đọc " . count($articles) . " bài viết từ link thủ công");
        $this->saveCache($articles);
        return $articles;
    }

    /**
     * Đọc title, mô tả, ảnh đại diện và nội dung từ một URL bài viết.
     */
    private function isLikelyListingUrl($url) {
        $path = trim((string)(parse_url($url, PHP_URL_PATH) ?? ''), '/');
        if ($path === '') {
            return true;
        }
        if (preg_match('/(the-thao|bong-da|football|sport|sports|tin-tuc|category|chuyen-muc|\.epi)$/i', $path)) {
            return true;
        }
        return !preg_match('/(\d{4,}|\.html?|\/c\/\d+|\/p\/\d+)/i', $path);
    }

    private function fetchArticlesFromListingUrl($url, $limit = 8) {
        $html = $this->httpGet($url);
        if (empty($html)) {
            return [];
        }

        libxml_use_internal_errors(true);
        $doc = new DOMDocument();
        $doc->loadHTML('<?xml encoding="UTF-8">' . $html);
        $xpath = new DOMXPath($doc);
        $nodes = $xpath->query('//article//a[@href] | //h2/a[@href] | //h3/a[@href] | //h4/a[@href] | //a[contains(@class, "title")][@href] | //a[contains(@class, "story")][@href] | //a[contains(@class, "news")][@href]');

        $articles = [];
        $seen = [];
        foreach ($nodes as $node) {
            $title = trim(preg_replace('/\s+/u', ' ', $node->textContent));
            if (mb_strlen($title) < 18) {
                continue;
            }

            $link = $this->absoluteUrl($node->getAttribute('href'), $url);
            if (!$this->isValidUrl($link) || !$this->isLikelyArticleLink($link, $url)) {
                continue;
            }

            $key = $this->normalizeUrl($link);
            if ($key === '' || isset($seen[$key])) {
                continue;
            }
            $seen[$key] = true;

            $container = $this->nearestContentNode($node);
            $description = $container ? $this->listingDescription($xpath, $container) : '';
            $image = $container ? $this->listingImage($xpath, $container, $url) : '';

            $articles[] = [
                'title' => $title,
                'link' => $link,
                'description' => $description,
                'image' => $image,
                'published_at' => date('Y-m-d H:i:s'),
                'source' => parse_url($url, PHP_URL_HOST) ?: 'Link thủ công',
                'full_content' => ''
            ];

            if (count($articles) >= $limit) {
                break;
            }
        }

        return $articles;
    }

    private function isLikelyArticleLink($link, $base_url) {
        $path = parse_url($link, PHP_URL_PATH) ?? '';
        if ($path === '' || $path === '/') {
            return false;
        }
        if (preg_match('/(login|register|tag|search|author|video|photo|livescore|lich-thi-dau|bang-xep-hang)/i', $path)) {
            return false;
        }
        if (preg_match('/(\d{4,}|\.html?|\/c\/\d+|\/p\/\d+)/i', $path)) {
            return true;
        }

        $base_host = preg_replace('/^www\./i', '', parse_url($base_url, PHP_URL_HOST) ?: '');
        $host = preg_replace('/^www\./i', '', parse_url($link, PHP_URL_HOST) ?: '');
        return $base_host !== '' && $host === $base_host && substr_count(trim($path, '/'), '/') >= 1;
    }

    private function nearestContentNode($node) {
        $current = $node;
        for ($i = 0; $i < 4 && $current && $current->parentNode; $i++) {
            $current = $current->parentNode;
            if (in_array(strtolower($current->nodeName), ['article', 'li', 'div'], true)) {
                return $current;
            }
        }
        return $node->parentNode;
    }

    private function listingDescription($xpath, $node) {
        $desc_node = $xpath->query('.//p | .//*[contains(@class, "desc")] | .//*[contains(@class, "sapo")] | .//*[contains(@class, "summary")]', $node);
        if ($desc_node->length > 0) {
            $text = trim(preg_replace('/\s+/u', ' ', $desc_node->item(0)->textContent));
            return mb_substr($text, 0, 300);
        }
        return '';
    }

    private function listingImage($xpath, $node, $base_url) {
        $img_node = $xpath->query('.//img | .//source', $node);
        foreach ($img_node as $img) {
            $src = $img->getAttribute('src')
                ?: $img->getAttribute('data-src')
                ?: $img->getAttribute('data-original')
                ?: $img->getAttribute('data-lazy-src')
                ?: $img->getAttribute('srcset')
                ?: $img->getAttribute('data-srcset');
            $src = $this->firstSrcsetUrl($src);
            if ($src && !preg_match('/logo|avatar|icon|sprite/i', $src)) {
                return $this->absoluteUrl($src, $base_url);
            }
        }
        return '';
    }

    public function fetchArticleFromUrl($url) {
        $html = $this->httpGet($url);
        if (empty($html)) {
            return [
                'title' => $url,
                'link' => $url,
                'description' => '',
                'image' => '',
                'published_at' => date('Y-m-d H:i:s'),
                'source' => parse_url($url, PHP_URL_HOST) ?: 'Link thủ công',
                'full_content' => '',
            ];
        }

        libxml_use_internal_errors(true);
        $doc = new DOMDocument();
        $doc->loadHTML('<?xml encoding="UTF-8">' . $html);
        $xpath = new DOMXPath($doc);

        $title = $this->meta($xpath, 'property', 'og:title')
            ?: $this->meta($xpath, 'name', 'twitter:title')
            ?: $this->firstText($xpath, ['//h1', '//title'])
            ?: $url;

        $description = $this->meta($xpath, 'property', 'og:description')
            ?: $this->meta($xpath, 'name', 'description')
            ?: $this->meta($xpath, 'name', 'twitter:description')
            ?: '';

        $image = $this->meta($xpath, 'property', 'og:image')
            ?: $this->meta($xpath, 'name', 'twitter:image')
            ?: $this->firstImage($xpath);
        $image = $this->absoluteUrl($image, $url);

        $published = $this->meta($xpath, 'property', 'article:published_time')
            ?: $this->meta($xpath, 'name', 'pubdate')
            ?: $this->meta($xpath, 'name', 'publishdate')
            ?: date('Y-m-d H:i:s');

        $content = $this->extractArticleText($xpath);

        return [
            'title' => trim($title),
            'link' => $url,
            'description' => trim($description),
            'image' => $image,
            'published_at' => date('Y-m-d H:i:s', strtotime($published) ?: time()),
            'source' => parse_url($url, PHP_URL_HOST) ?: 'Link thủ công',
            'full_content' => $content,
        ];
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
            return $this->extractArticleText($xpath);
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
     * Loại tin trùng theo link, tiêu đề chuẩn hóa và độ giống tiêu đề.
     */
    public function deduplicateArticles($articles) {
        $unique = [];
        $seen_links = [];
        $seen_titles = [];

        foreach ($articles as $article) {
            if (!is_array($article)) {
                continue;
            }

            $title = trim((string)($article['title'] ?? ''));
            $link = trim((string)($article['link'] ?? ''));
            if ($title === '' && $link === '') {
                continue;
            }

            $link_key = $this->normalizeUrl($link);
            if ($link_key !== '' && isset($seen_links[$link_key])) {
                continue;
            }

            $title_key = $this->normalizeTitle($title);
            if ($title_key !== '') {
                if (isset($seen_titles[$title_key])) {
                    continue;
                }

                $similar = false;
                foreach ($seen_titles as $seen_title => $_) {
                    if ($this->isSimilarTitle($title_key, $seen_title)) {
                        $similar = true;
                        break;
                    }
                }
                if ($similar) {
                    continue;
                }
            }

            if ($link_key !== '') {
                $seen_links[$link_key] = true;
            }
            if ($title_key !== '') {
                $seen_titles[$title_key] = true;
            }
            $unique[] = $article;
        }

        return array_values($unique);
    }

    public function articleFingerprint($article) {
        $link_key = $this->normalizeUrl($article['link'] ?? '');
        $title_key = $this->normalizeTitle($article['title'] ?? '');
        return [
            'link_key' => $link_key,
            'title_key' => $title_key,
            'link_hash' => $link_key !== '' ? sha1($link_key) : '',
            'title_hash' => $title_key !== '' ? sha1($title_key) : '',
        ];
    }

    public function titlesAreSimilar($a, $b) {
        return $this->isSimilarTitle($this->normalizeTitle($a), $this->normalizeTitle($b));
    }

    private function normalizeTitle($title) {
        $title = html_entity_decode((string)$title, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        $title = $this->lower($title);
        $title = preg_replace('/\s+/u', ' ', $title);
        $title = preg_replace('/[^\p{L}\p{N}\s]+/u', ' ', $title);
        $title = preg_replace('/\b(video|clip|live|truc tiep|trực tiếp|mới nhất|cập nhật)\b/u', ' ', $title);
        $title = preg_replace('/\s+/u', ' ', $title);
        return trim($title);
    }

    private function normalizeUrl($url) {
        $url = trim((string)$url);
        if ($url === '') {
            return '';
        }

        $parts = parse_url($url);
        if (!$parts || empty($parts['host'])) {
            return rtrim($this->lower($url), '/');
        }

        $scheme = $this->lower($parts['scheme'] ?? 'https');
        $host = preg_replace('/^www\./i', '', $this->lower($parts['host']));
        $path = $parts['path'] ?? '';
        $query = [];

        if (!empty($parts['query'])) {
            parse_str($parts['query'], $query);
            foreach (array_keys($query) as $key) {
                if (preg_match('/^(utm_|fbclid|gclid|zarsrc|ref|source)/i', $key)) {
                    unset($query[$key]);
                }
            }
            ksort($query);
        }

        $normalized = "{$scheme}://{$host}" . rtrim($path, '/');
        if (!empty($query)) {
            $normalized .= '?' . http_build_query($query);
        }
        return $normalized;
    }

    private function isSimilarTitle($a, $b) {
        $a = trim((string)$a);
        $b = trim((string)$b);
        if ($a === '' || $b === '') {
            return false;
        }
        if ($a === $b) {
            return true;
        }
        if (strlen($a) < 18 || strlen($b) < 18) {
            return false;
        }

        similar_text($a, $b, $percent);
        return $percent >= 88;
    }

    private function lower($text) {
        return function_exists('mb_strtolower')
            ? mb_strtolower((string)$text, 'UTF-8')
            : strtolower((string)$text);
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

            if (!empty($article['full_content'])) {
                $content .= "Nội dung:\n{$article['full_content']}\n";
            }

            if (!empty($article['image'])) {
                $content .= "Ảnh đại diện: {$article['image']}\n";
            }

            if ($fetch_full_content && !empty($article['link'])) {
                $this->log("Đang lấy nội dung đầy đủ từ: {$article['link']}");
                $full = $this->fetchArticleContent($article['link']);
                if (!empty($full) && empty($article['full_content'])) {
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

    private function extractArticleText($xpath) {
        $selectors = [
            '//article//div[contains(@class, "content")]',
            '//div[contains(@class, "fck_detail")]',
            '//div[contains(@class, "article-body")]',
            '//div[contains(@class, "detail-content")]',
            '//div[contains(@class, "content-detail")]',
            '//div[contains(@class, "the_content")]',
            '//div[contains(@class, "post-content")]',
            '//div[contains(@class, "entry-content")]',
            '//div[contains(@class, "article-content")]',
            '//div[@id="main-detail-body"]',
            '//article',
            '//main',
        ];

        foreach ($selectors as $selector) {
            $nodes = $xpath->query($selector);
            if ($nodes->length > 0) {
                $content = $this->paragraphText($xpath, $nodes->item(0));
                if (!empty($content)) {
                    return mb_substr($content, 0, 5000);
                }
            }
        }

        return '';
    }

    private function paragraphText($xpath, $node) {
        $content = '';
        $paragraphs = $xpath->query('.//p', $node);
        foreach ($paragraphs as $p) {
            $text = trim(preg_replace('/\s+/', ' ', $p->textContent));
            if (!empty($text) && mb_strlen($text) > 20) {
                $content .= $text . "\n\n";
            }
        }
        return trim($content);
    }

    private function meta($xpath, $attr, $value) {
        $nodes = $xpath->query("//meta[translate(@{$attr}, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='" . strtolower($value) . "']/@content");
        if ($nodes->length > 0) {
            return trim($nodes->item(0)->nodeValue);
        }
        return '';
    }

    private function firstText($xpath, $selectors) {
        foreach ($selectors as $selector) {
            $nodes = $xpath->query($selector);
            if ($nodes->length > 0) {
                $text = trim(preg_replace('/\s+/', ' ', $nodes->item(0)->textContent));
                if ($text !== '') {
                    return $text;
                }
            }
        }
        return '';
    }

    private function firstImage($xpath) {
        $nodes = $xpath->query('//article//img | //article//source | //main//img | //main//source | //img | //source');
        foreach ($nodes as $node) {
            $src = $node->getAttribute('src')
                ?: $node->getAttribute('data-src')
                ?: $node->getAttribute('data-original')
                ?: $node->getAttribute('data-lazy-src')
                ?: $node->getAttribute('srcset')
                ?: $node->getAttribute('data-srcset');
            $src = $this->firstSrcsetUrl($src);
            if ($src && !preg_match('/logo|avatar|icon|sprite/i', $src)) {
                return $src;
            }
        }
        return '';
    }

    private function firstSrcsetUrl($value) {
        $value = trim((string)$value);
        if ($value === '') {
            return '';
        }
        $first = trim(explode(',', $value)[0]);
        return trim(explode(' ', $first)[0]);
    }

    private function absoluteUrl($url, $base_url) {
        $url = trim((string) $url);
        if ($url === '') {
            return '';
        }
        if (strpos($url, '//') === 0) {
            $scheme = parse_url($base_url, PHP_URL_SCHEME) ?: 'https';
            return $scheme . ':' . $url;
        }
        if (preg_match('/^https?:\/\//i', $url)) {
            return $url;
        }

        $scheme = parse_url($base_url, PHP_URL_SCHEME) ?: 'https';
        $host = parse_url($base_url, PHP_URL_HOST);
        if (!$host) {
            return $url;
        }
        if (strpos($url, '/') === 0) {
            return "{$scheme}://{$host}{$url}";
        }

        $path = parse_url($base_url, PHP_URL_PATH) ?: '/';
        $dir = rtrim(dirname($path), '/\\');
        return "{$scheme}://{$host}{$dir}/{$url}";
    }

    private function isValidUrl($url) {
        return filter_var($url, FILTER_VALIDATE_URL) && preg_match('/^https?:\/\//i', $url);
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
