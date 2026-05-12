<?php

/**
 * Facebook Auto Poster
 * 
 * A comprehensive PHP library for automated Facebook page posting
 * with AI integration using Gemini API for content generation.
 * 
 * Features:
 * - Only Image post
 * - Only Caption post
 * - Image with Caption post
 * - AI Image/Caption generation (Gemini)
 * - Gemini Daily Free Limit 100
 * - Manual Content from JSON files
 * - Easy configuration and usage
 * 
 * @author Xiata
 * @version 1.0.1
 */

class FacebookAutoPoster {
    
    private $page_id;
    private $page_access_token;
    private $image_folder;
    private $caption_file;
    private $ai_use;
    private $gemini_api_key;
    private $config;
    private $log_file;
    
    /**
     * Constructor
     * 
     * @param array $config Configuration array
     */
    public function __construct($config = []) {
        $this->config = array_merge([
            'page_id' => '',
            'page_access_token' => '',
            'image_folder' => './images/',
            'caption_file' => './captions.json',
            'ai_use' => 2, // 1 = use AI, 2 = manual
            'gemini_api_key' => '',
            'log_file' => './facebook_poster.log',
            'facebook_api_version' => 'v20.0',
            'max_retries' => 3,
            'retry_delay' => 2 // seconds
        ], $config);
        
        $this->page_id = $this->config['page_id'];
        $this->page_access_token = $this->config['page_access_token'];
        $this->image_folder = rtrim($this->config['image_folder'], '/') . '/';
        $this->caption_file = $this->config['caption_file'];
        $this->ai_use = $this->config['ai_use'];
        $this->gemini_api_key = $this->config['gemini_api_key'];
        $this->log_file = $this->config['log_file'];
        
        // Create directories if they don't exist
        if (!is_dir($this->image_folder)) {
            mkdir($this->image_folder, 0755, true);
        }
        
        if (!is_dir(dirname($this->caption_file))) {
            mkdir(dirname($this->caption_file), 0755, true);
        }
    }
    
    /**
     * Set configuration
     * 
     * @param string $key
     * @param mixed $value
     */
    public function setConfig($key, $value) {
        $this->config[$key] = $value;
        $this->$key = $value;
    }
    
    /**
     * Get configuration
     * 
     * @param string $key
     * @return mixed
     */
    public function getConfig($key = null) {
        return $key ? ($this->config[$key] ?? null) : $this->config;
    }
    
    /**
     * Create and post content
     * 
     * @param array $options Override options
     * @return array Response array
     */
    public function post($options = []) {
        try {
            $this->log('Bắt đầu quá trình đăng bài tự động trên Facebook');
            
            // Validate configuration
            $validation = $this->validateConfig();
            if (!$validation['valid']) {
                return $this->formatResponse('error', $validation['message']);
            }
            
            if ($this->ai_use == 1) {
                return $this->postWithAI($options);
            } else {
                return $this->postManually($options);
            }
            
        } catch (Exception $e) {
            $this->log('Error: ' . $e->getMessage());
            return $this->formatResponse('error', 'Đã xảy ra lỗi: ' . $e->getMessage());
        }
    }
    
    /**
     * Post with AI generated content
     * 
     * @param array $options
     * @return array
     */
    private function postWithAI($options = []) {
        $this->log('Sử dụng chế độ AI để tạo nội dung');
        
        if (empty($this->gemini_api_key)) {
            return $this->formatResponse('error', 'Yêu cầu khóa API Gemini cho chế độ AI');
        }
        
        // Determine post type
        $post_type = $options['post_type'] ?? 'image_caption'; // image_only, caption_only, image_caption
        
        switch ($post_type) {
            case 'image_only':
                return $this->postAIImageOnly($options);
            case 'caption_only':
                return $this->postAICaptionOnly($options);
            case 'image_caption':
            default:
                return $this->postAIImageCaption($options);
        }
    }
    
    /**
     * Post manually using JSON file
     * 
     * @param array $options
     * @return array
     */
    private function postManually($options = []) {
        $this->log('Sử dụng chế độ thủ công cho nội dung');
        
        // Load captions from JSON file
        $captions_data = $this->loadCaptionsFile();
        if (!$captions_data) {
            return $this->formatResponse('error', 'Không thể tải tệp chú thích');
        }
        
        if (empty($captions_data['captions'])) {
            return $this->formatResponse('error', 'Không có chú thích nào trong tệp');
        }
        
        
        $caption_data = array_shift($captions_data['captions']);
        
        $caption = $caption_data['caption'] ?? '';
        $image_file = $caption_data['file'] ?? '';
        $image_path = !empty($image_file) ? $this->image_folder . $image_file : null;
        

        if (!empty($image_file) && !empty($caption)) {
            $post_type = 'image_caption';
        } elseif (!empty($image_file)) {
            $post_type = 'image_only';
            $caption = $caption_data['caption'] ?? '';
        } elseif (!empty($caption)) {
            $post_type = 'caption_only';
        } else {
            return $this->formatResponse('error', 'Không tìm thấy nội dung hợp lệ');
        }
        
        // Publish to Facebook
        $result = $this->publishToFacebook($caption, $image_path, $post_type);
        
        // If post was successful, delete the image file and update JSON
        if ($result['status'] == 'success') {
            
            if (!empty($image_file) && file_exists($image_path)) {
                if (unlink($image_path)) {
                    $this->log('Đã xóa tệp hình ảnh: ' . $image_file);
                } else {
                    $this->log('Cảnh báo: Không thể xóa tệp hình ảnh: ' . $image_file);
                }
            }
            
            // Update caption file
            if ($this->saveCaptionsFile(['captions' => $captions_data['captions']])) {
                $this->log('Đã xóa chú thích khỏi tệp JSON');
            } else {
                $this->log('Cảnh báo: Không thể cập nhật tệp chú thích');
            }
        }
        
        return $result;
    }
    
    /**
     * Post AI generated image only
     * 
     * @param array $options
     * @return array
     */
    private function postAIImageOnly($options = []) {
        $prompt = $options['image_prompt'] ?? 'Tạo một hình ảnh sáng tạo và thu hút';
        
        $image_result = $this->generateImageWithGemini($prompt);
        if (!$image_result['success']) {
            return $this->formatResponse('error', 'Không thể tạo hình ảnh: ' . $image_result['message']);
        }
        
        return $this->publishToFacebook('', $image_result['image_path'], 'image_only');
    }
    
    /**
     * Post AI generated caption only
     * 
     * @param array $options
     * @return array
     */
    private function postAICaptionOnly($options = []) {
        $prompt = $options['caption_prompt'] ?? 'Tạo một chú thích mạng xã hội thu hút';
        
        $caption_result = $this->generateCaptionWithGemini($prompt);
        if (!$caption_result['success']) {
            return $this->formatResponse('error', 'Không thể tạo chú thích: ' . $caption_result['message']);
        }
        
        return $this->publishToFacebook($caption_result['caption'], null, 'caption_only');
    }
    
    /**
     * Post AI generated image with caption
     * 
     * @param array $options
     * @return array
     */
    private function postAIImageCaption($options = []) {
        $image_prompt = $options['image_prompt'] ?? 'Tạo một hình ảnh sáng tạo và thu hút';
        
        // Generate image first
        $image_result = $this->generateImageWithGemini($image_prompt);
        if (!$image_result['success']) {
            return $this->formatResponse('error', 'Không thể tạo hình ảnh: ' . $image_result['message']);
        }
        
        // Generate caption based on the image
        $caption_prompt = $options['caption_prompt'] ?? 'Tạo một chú thích mạng xã hội thu hút cho hình ảnh này';
        $caption_result = $this->generateCaptionForImage($image_result['image_path'], $caption_prompt);
        
        if (!$caption_result['success']) {
            return $this->formatResponse('error', 'Không thể tạo chú thích: ' . $caption_result['message']);
        }
        
        return $this->publishToFacebook($caption_result['caption'], $image_result['image_path'], 'image_caption');
    }
    
    /**
     * Generate image using Gemini AI
     * 
     * @param string $prompt
     * @return array
     */
    private function generateImageWithGemini($prompt) {
        try {
            $this->log('Đang tạo hình ảnh bằng Imagen API');
            
            
            $url = 'https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=' . $this->gemini_api_key;
            
            // Payload
            $data = [
                'instances' => [
                    [
                        'prompt' => $prompt
                    ]
                ],
                'parameters' => [
                    'sampleCount' => 1,
                    'aspectRatio' => '1:1', 
                    'safetyFilterLevel' => 'block_some',
                    'personGeneration' => 'allow_adult'
                ]
            ];
            
            $response = $this->makeAPIRequest($url, $data, 'POST');
            
            if (!$response['success']) {
                $error_msg = $response['message'];
                // Log
                if (isset($response['data'])) {
                    $this->log('Chi tiết Lỗi Imagen API: ' . json_encode($response['data']));
                }
                return ['success' => false, 'message' => $error_msg];
            }
            
            $result = $response['data'];
            
            
            if (isset($result['predictions'][0]['bytesBase64Encoded'])) {
                $image_data = base64_decode($result['predictions'][0]['bytesBase64Encoded']);
                $filename = 'ai_generated_' . time() . '_' . uniqid() . '.png';
                $image_path = $this->image_folder . $filename;
                
                if (file_put_contents($image_path, $image_data)) {
                    $this->log('Tạo hình ảnh thành công: ' . $filename);
                    return ['success' => true, 'image_path' => $image_path, 'filename' => $filename];
                } else {
                    return ['success' => false, 'message' => 'Không thể lưu hình ảnh đã tạo'];
                }
            } elseif (isset($result['predictions'][0]['mimeType']) && isset($result['predictions'][0]['image'])) {
                
                $image_data = base64_decode($result['predictions'][0]['image']);
                $filename = 'ai_generated_' . time() . '_' . uniqid() . '.png';
                $image_path = $this->image_folder . $filename;
                
                if (file_put_contents($image_path, $image_data)) {
                    $this->log('Tạo hình ảnh thành công: ' . $filename);
                    return ['success' => true, 'image_path' => $image_path, 'filename' => $filename];
                } else {
                    return ['success' => false, 'message' => 'Không thể lưu hình ảnh đã tạo'];
                }
            } else {
                $this->log('Phản hồi API không mong muốn: ' . json_encode($result));
                return ['success' => false, 'message' => 'Không nhận được dữ liệu hình ảnh từ Imagen API. Phản hồi: ' . json_encode($result)];
            }
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => 'Lỗi tạo hình ảnh: ' . $e->getMessage()];
        }
    }
    
    /**
     * Generate caption using Gemini AI
     * 
     * @param string $prompt
     * @return array
     */
    private function generateCaptionWithGemini($prompt) {
        try {
            $this->log('Đang tạo chú thích bằng Gemini AI');
            
            
            $url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=' . $this->gemini_api_key;
            
            $data = [
                'contents' => [
                    [
                        'parts' => [
                            [
                                'text' => $prompt . ' Hãy giữ cho nó thu hút, súc tích và phù hợp với mạng xã hội. Bao gồm các hashtag có liên quan.'
                            ]
                        ]
                    ]
                ],
                'generationConfig' => [
                    'temperature' => 0.7,
                    'topK' => 40,
                    'topP' => 0.95,
                    'maxOutputTokens' => 200
                ]
            ];
            
            $response = $this->makeAPIRequest($url, $data, 'POST');
            
            if (!$response['success']) {
                return ['success' => false, 'message' => $response['message']];
            }
            
            $result = $response['data'];
            
            if (isset($result['candidates'][0]['content']['parts'][0]['text'])) {
                $caption = trim($result['candidates'][0]['content']['parts'][0]['text']);
                $this->log('Tạo chú thích thành công');
                return ['success' => true, 'caption' => $caption];
            } else {
                $this->log('Phản hồi chú thích không mong muốn: ' . json_encode($result));
                return ['success' => false, 'message' => 'Không có chú thích nào được tạo bởi Gemini'];
            }
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => 'Lỗi tạo chú thích: ' . $e->getMessage()];
        }
    }
    
    /**
     * Generate caption for existing image using Gemini AI
     * 
     * @param string $image_path
     * @param string $prompt
     * @return array
     */
    private function generateCaptionForImage($image_path, $prompt) {
        try {
            if (!file_exists($image_path)) {
                return ['success' => false, 'message' => 'Không tìm thấy tệp hình ảnh'];
            }
            
            $this->log('Đang tạo chú thích cho hình ảnh bằng Gemini AI');
            
            $url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';
            
            $image_data = base64_encode(file_get_contents($image_path));
            $mime_type = mime_content_type($image_path);
            
            $data = [
                'contents' => [
                    [
                        'parts' => [
                            [
                                'text' => $prompt . ' Dựa trên hình ảnh này, hãy tạo một chú thích mạng xã hội thu hút với các hashtag có liên quan.'
                            ],
                            [
                                'inline_data' => [
                                    'mime_type' => $mime_type,
                                    'data' => $image_data
                                ]
                            ]
                        ]
                    ]
                ],
                'generationConfig' => [
                    'temperature' => 0.7,
                    'topK' => 40,
                    'topP' => 0.95,
                    'maxOutputTokens' => 200
                ]
            ];
            
            $response = $this->makeAPIRequest($url . '?key=' . $this->gemini_api_key, $data, 'POST');
            
            if (!$response['success']) {
                return ['success' => false, 'message' => $response['message']];
            }
            
            $result = $response['data'];
            
            if (isset($result['candidates'][0]['content']['parts'][0]['text'])) {
                $caption = trim($result['candidates'][0]['content']['parts'][0]['text']);
                $this->log('Tạo chú thích thành công for image');
                return ['success' => true, 'caption' => $caption];
            } else {
                return ['success' => false, 'message' => 'Không có chú thích nào được tạo bởi Gemini for image'];
            }
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => 'Lỗi tạo chú thích cho hình ảnh: ' . $e->getMessage()];
        }
    }
    
    /**
     * Publish content to Facebook
     * 
     * @param string $caption
     * @param string|null $image_path
     * @param string $post_type
     * @return array
     */
    private function publishToFacebook($caption, $image_path, $post_type) {
        try {
            $this->log("Đang đăng lên Facebook - Loại: $post_type");
            

            $page_token = $this->getPageAccessToken();
            if (!$page_token) {
                return $this->formatResponse('error', 'Không thể lấy token truy cập trang');
            }
            
            $result = $this->postToFacebook($page_token, $caption, $image_path);
            
            if ($result['status'] == 'success') {
                $this->log('Đăng bài thành công. ID Bài viết: ' . $result['post_id']);
                return $this->formatResponse('success', 'Đăng bài thành công', [
                    'post_id' => $result['post_id'],
                    'post_type' => $post_type,
                    'caption' => $caption,
                    'image_used' => !empty($image_path),
                    'timestamp' => date('Y-m-d H:i:s')
                ]);
            } else {
                return $this->formatResponse('error', $result['message'], $result);
            }
            
        } catch (Exception $e) {
            return $this->formatResponse('error', 'Lỗi khi đăng: ' . $e->getMessage());
        }
    }
    
    /**
     * Get page access token
     * 
     * @return string|null
     */
    private function getPageAccessToken() {
        $url = "https://graph.facebook.com/{$this->config['facebook_api_version']}/{$this->page_id}?fields=access_token&access_token={$this->page_access_token}";
        
        $response = $this->makeAPIRequest($url, null, 'GET');
        
        if ($response['success'] && isset($response['data']['access_token'])) {
            return $response['data']['access_token'];
        }
        
        return null;
    }
    
    /**
     * Post to Facebook page
     * 
     * @param string $page_token
     * @param string $caption
     * @param string|null $image_path
     * @return array
     */
    private function postToFacebook($page_token, $caption, $image_path = null) {
        $retries = 0;
        
        while ($retries < $this->config['max_retries']) {
            try {
                $url = $image_path && file_exists($image_path)
                    ? "https://graph.facebook.com/{$this->config['facebook_api_version']}/{$this->page_id}/photos"
                    : "https://graph.facebook.com/{$this->config['facebook_api_version']}/{$this->page_id}/feed";

                $post_fields = $image_path && file_exists($image_path)
                    ? ['caption' => $caption, 'access_token' => $page_token, 'source' => new CURLFile($image_path)]
                    : ['message' => $caption, 'access_token' => $page_token];

                $ch = curl_init();
                curl_setopt($ch, CURLOPT_URL, $url);
                curl_setopt($ch, CURLOPT_POST, true);
                curl_setopt($ch, CURLOPT_POSTFIELDS, $post_fields);
                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                curl_setopt($ch, CURLOPT_TIMEOUT, 30);
                curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
                curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
                
                $result = curl_exec($ch);
                $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
                $error = curl_error($ch);
                curl_close($ch);

                if ($error) {
                    throw new Exception("Lỗi cURL: $error");
                }
                
                $decoded = json_decode($result, true);
                
                if ($http_code == 200 && isset($decoded['id'])) {
                    return [
                        'status' => 'success', 
                        'message' => 'Đăng bài thành công.', 
                        'post_id' => $decoded['id']
                    ];
                } else {
                    // Handle rate limiting
                    if ($http_code == 429 || (isset($decoded['error']['code']) && $decoded['error']['code'] == 4)) {
                        $retries++;
                        if ($retries < $this->config['max_retries']) {
                            $this->log("Giới hạn tỷ lệ. Thử lại sau {$this->config['retry_delay']} giây... (Lần thử $retries)");
                            sleep($this->config['retry_delay']);
                            continue;
                        }
                    }
                    
                    return [
                        'status' => 'error', 
                        'message' => 'Đăng bài thất bại: ' . ($decoded['error']['message'] ?? 'Lỗi không xác định'),
                        'response' => $decoded,
                        'http_code' => $http_code
                    ];
                }
                
            } catch (Exception $e) {
                $retries++;
                if ($retries < $this->config['max_retries']) {
                    $this->log("Đã xảy ra lỗi. Đang thử lại... (Lần thử $retries): " . $e->getMessage());
                    sleep($this->config['retry_delay']);
                } else {
                    return ['status' => 'error', 'message' => $e->getMessage()];
                }
            }
        }
        
        return ['status' => 'error', 'message' => 'Đã vượt quá số lần thử lại tối đa'];
    }
    
    /**
     * Load captions from JSON file
     * 
     * @return array|false
     */
    private function loadCaptionsFile() {
        if (!file_exists($this->caption_file)) {
            // Create sample file
            $sample_data = [
                'captions' => [
                    [
                        'file' => 'sample1.jpg',
                        'caption' => 'Chú thích mẫu cho bài đăng đầu tiên của bạn!'
                    ],
                    [
                        'file' => 'sample2.jpg',
                        'caption' => 'Một chú thích bài đăng tuyệt vời khác ở đây!'
                    ]
                ]
            ];
            file_put_contents($this->caption_file, json_encode($sample_data, JSON_PRETTY_PRINT));
        }
        
        $json_content = file_get_contents($this->caption_file);
        $data = json_decode($json_content, true);
        
        if (json_last_error() !== JSON_ERROR_NONE) {
            $this->log('Lỗi giải mã JSON: ' . json_last_error_msg());
            return false;
        }
        
        return $data;
    }
    
    /**
     * Save captions to JSON file
     * 
     * @param array $data
     * @return bool
     */
    private function saveCaptionsFile($data) {
        $json_content = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
        return file_put_contents($this->caption_file, $json_content) !== false;
    }
    
    /**
     * Make API request
     * 
     * @param string $url
     * @param array|null $data
     * @param string $method
     * @return array
     */
    private function makeAPIRequest($url, $data = null, $method = 'GET') {
        $ch = curl_init();
        
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        if ($method == 'POST' && $data) {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            curl_setopt($ch, CURLOPT_HTTPHEADER, [
                'Content-Type: application/json',
                'Content-Length: ' . strlen(json_encode($data))
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
     * Validate configuration
     * 
     * @return array
     */
    private function validateConfig() {
        if (empty($this->page_id)) {
            return ['valid' => false, 'message' => 'Yêu cầu ID Trang'];
        }
        
        if (empty($this->page_access_token)) {
            return ['valid' => false, 'message' => 'Yêu cầu Token truy cập trang'];
        }
        
        if ($this->ai_use == 1 && empty($this->gemini_api_key)) {
            return ['valid' => false, 'message' => 'Yêu cầu khóa API Gemini cho chế độ AI'];
        }
        
        if (!is_writable(dirname($this->image_folder))) {
            return ['valid' => false, 'message' => 'Thư mục hình ảnh không có quyền ghi'];
        }
        
        return ['valid' => true, 'message' => 'Cấu hình hợp lệ'];
    }
    
    /**
     * Format response array
     * 
     * @param string $status
     * @param string $message
     * @param array $additional_data
     * @return array
     */
    private function formatResponse($status, $message, $additional_data = []) {
        return array_merge([
            'status' => $status,
            'message' => $message,
            'timestamp' => date('Y-m-d H:i:s')
        ], $additional_data);
    }
    
    /**
     * Log messages
     * 
     * @param string $message
     */
    private function log($message) {
        $log_entry = date('Y-m-d H:i:s') . " - " . $message . PHP_EOL;
        file_put_contents($this->log_file, $log_entry, FILE_APPEND | LOCK_EX);
    }
    
    /**
     * Get available images in the images folder
     * 
     * @return array
     */
    public function getAvailableImages() {
        $images = [];
        $allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
        
        if (is_dir($this->image_folder)) {
            $files = scandir($this->image_folder);
            foreach ($files as $file) {
                if ($file != '.' && $file != '..') {
                    $extension = strtolower(pathinfo($file, PATHINFO_EXTENSION));
                    if (in_array($extension, $allowed_extensions)) {
                        $images[] = $file;
                    }
                }
            }
        }
        
        return $images;
    }
    
    /**
     * Get remaining captions count
     * 
     * @return int
     */
    public function getRemainingCaptionsCount() {
        $captions_data = $this->loadCaptionsFile();
        return $captions_data ? count($captions_data['captions']) : 0;
    }
    
    /**
     * Test Facebook connection
     * 
     * @return array
     */
    public function testFacebookConnection() {
        try {
            $page_token = $this->getPageAccessToken();
            if ($page_token) {
                return $this->formatResponse('success', 'Kết nối Facebook thành công');
            } else {
                return $this->formatResponse('error', 'Không thể kết nối với Facebook');
            }
        } catch (Exception $e) {
            return $this->formatResponse('error', 'Kiểm tra kết nối thất bại: ' . $e->getMessage());
        }
    }
    
    /**
     * Test Gemini AI connection
     * 
     * @return array
     */
    public function testGeminiConnection() {
        try {
            if (empty($this->gemini_api_key)) {
                return $this->formatResponse('error', 'Không cung cấp khóa API Gemini');
            }
            
            $result = $this->generateCaptionWithGemini('Kiểm tra kết nối');
            if ($result['success']) {
                return $this->formatResponse('success', 'Kết nối AI Gemini thành công');
            } else {
                return $this->formatResponse('error', 'Kết nối AI Gemini thất bại: ' . $result['message']);
            }
        } catch (Exception $e) {
            return $this->formatResponse('error', 'Kiểm tra kết nối Gemini thất bại: ' . $e->getMessage());
        }
    }
}

?>