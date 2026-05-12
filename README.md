<h1 align="center">Facebook Auto Poster</h1>

<div align="center">

![PHP Version](https://img.shields.io/badge/PHP-7.4%2B-777BB4?style=for-the-badge&logo=php&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Facebook API](https://img.shields.io/badge/Facebook-API%20v20.0-1877F2?style=for-the-badge&logo=facebook&logoColor=white)
![AI Powered](https://img.shields.io/badge/AI-Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:hello@xiata.fun)[![GitHub](https://img.shields.io/badge/Xiata-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Xiata)

*Một thư viện PHP đơn giản nhưng mạnh mẽ để tự động hóa việc đăng bài trên Trang Facebook. Hỗ trợ đăng thủ công từ file JSON/hình ảnh cục bộ cũng như tạo nội dung bằng AI (Google Gemini). Được thiết kế cho các nhà phát triển muốn có một giải pháp rõ ràng, linh hoạt và thân thiện với cron cho tự động hóa Facebook.*

[Tính năng](#-tính-năng) • [Cài đặt](#-cài-đặt) • [Ví dụ Sử dụng](#-💡-ví-dụ-sử-dụng
) • [Khắc phục sự cố](#-khắc-phục-sự-cố) • [Đóng góp](#-đóng-góp) 

</div>

---

## 🚀 Tính năng

- 📝 Đăng bài thủ công (JSON + Hình ảnh)
- 🤖 Nội dung do AI tạo
- 🎨 Hình ảnh do AI tạo kèm chú thích
- 📸 Đăng bài Chỉ Hình ảnh
- ✍️ Đăng bài Chỉ Chú thích



---

## 📦 Yêu cầu

- PHP 7.4 trở lên
- Tiện ích mở rộng cURL
- Access Token Facebook
- Khóa (KEY) Gemini (dành cho các tính năng AI)

<center style="color:red;">Để sử dụng Gemini đăng bài AI, bạn phải bật thanh toán trên tài khoản Google Cloud của mình. Nếu không có thanh toán, khóa API của bạn sẽ không hoạt động!</center>

---

## 🎨 Cài đặt

Tôi sẽ không chỉ bạn cách cài đặt nó.  
Nếu bạn không thể tự tìm hiểu thì thôi đi🖕 Thư viện này dành cho những người biết họ đang làm gì😪

---

## 🔑 Lấy Thông tin Xác thực Facebook

### A. Lấy ID Trang (Page ID)
1. Đi tới Trang Facebook của bạn
2. Nhấp vào "Giới thiệu" (About)
3. Cuộn xuống để tìm "ID Trang" (Page ID)

### B. Lấy Access Token
1. Đi tới [Facebook Developers](https://developers.facebook.com/)
2. Tạo một ứng dụng (nếu bạn chưa có)
3. Thêm sản phẩm "Đăng nhập Facebook" (Facebook Login)
4. Đi tới Graph API Explorer
5. Chọn ứng dụng của bạn
6. Tạo token với các quyền sau:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
7. Nhấp "Tạo Access Token" (Generate Access Token)
8. Sao chép token

### C. Lấy Token Dài hạn (Khuyên dùng)

Token của bạn mặc định sẽ hết hạn trong 1 giờ. Vì vậy, hãy lấy token dài hạn:

```php
<?php
$app_id = 'APP_ID';
$app_secret = 'APP_SECRET';
$short_token = 'ACCESS_TOKEN';

$url = "https://graph.facebook.com/oauth/access_token?" .
       "grant_type=fb_exchange_token&" .
       "client_id={$app_id}&" .
       "client_secret={$app_secret}&" .
       "fb_exchange_token={$short_token}";

$response = file_get_contents($url);
$data = json_decode($response, true);
echo "Token dài hạn: " . $data['access_token'];
?>
```

---

## ⚙️ Cài đặt Cấu hình

```php
<?php

require_once 'facebookAutoPoster.php';

$config = [
    'page_id'            => 'PAGE_ID',
    'page_access_token'  => 'PAGE_ACCESS_TOKEN',
    'image_folder'       => './images/',
    'caption_file'       => './captions.json',
    'ai_use'             => 2, // 1 = Chế độ AI, 2 = Chế độ Thủ công
    'gemini_api_key'     => 'GEMINI_KEY',
    'log_file'           => './logs/facebook_poster.log',
    'facebook_api_version' => 'v20.0'
];

$poster = new FacebookAutoPoster($config);
$result = $poster->post();

echo json_encode($result, JSON_PRETTY_PRINT);
```

> **💡 Mẹo:** Đảm bảo các thư mục `images/` và `logs/` của bạn có quyền ghi!

---

## 💡 Ví dụ Sử dụng

### 1️⃣ **Đăng bài Thủ công**

```php
$config['ai_use'] = 2;
$poster = new FacebookAutoPoster($config);

$result = $poster->post();
print_r($result);
```

> **📌 Lưu ý:** Đặt hình ảnh của bạn vào ./images/ và chú thích vào captions.json

---

### 2️⃣ **Hình ảnh AI + Chú thích**

```php
$config['ai_use'] = 1;
$ai_poster = new FacebookAutoPoster($config);

$result = $ai_poster->post([
    'post_type' => 'image_caption',
    'prompt'    => 'Một buổi hoàng hôn tuyệt đẹp trên núi với những màu sắc rực rỡ'
]);
```

### 3️⃣ **Chỉ Chú thích AI**

```php
$result = $ai_poster->post([
    'post_type' => 'caption_only',
    'prompt'    => 'Câu nói truyền cảm hứng về thành công và sự kiên trì'
]);
```

### 4️⃣ **Chỉ Hình ảnh AI**

```php
$result = $ai_poster->post([
    'post_type' => 'image_only',
    'prompt'    => 'Nghệ thuật kỹ thuật số trừu tượng với các hình khối neon rực rỡ'
]);
```

---

## ⏰ Cài đặt Cron Job

**Tạo `cron.php`:**

```php
<?php
require_once 'facebookAutoPoster.php';

$poster = new FacebookAutoPoster([
    'page_id' => 'PAGE_ID',
    'page_access_token' => 'PAGE_ACCESS_TOKEN',
    'ai_use' => 2,
    'image_folder' => '/images/',
    'caption_file' => '/captions.json'
]);

$result = $poster->post();

file_put_contents('./logs/cron.log',
    date('Y-m-d H:i:s') . ' - ' . json_encode($result) . PHP_EOL,
    FILE_APPEND
);
```

**Ví dụ về Lịch trình Cron:**

```bash
# 🕐 Mỗi giờ
0 * * * * /usr/bin/php /fbauto/cron.php

# 🕒 3 lần một ngày (9 SA, 3 CH, 9 CH)
0 9,15,21 * * * /usr/bin/php /fbauto/cron.php

# 🌙 Một lần mỗi ngày vào lúc nửa đêm
0 0 * * * /usr/bin/php /fbauto/cron.php
```

---

## 🔧 Các Phương thức Tiện ích

```php
// Kiểm tra Token Facebook
$poster->testFacebookConnection();

// Kiểm tra Khóa Gemini
$poster->testGeminiConnection();

// Lấy danh sách hình ảnh hiện có
$images = $poster->getAvailableImages();

// Đếm số chú thích còn lại
$count = $poster->getRemainingCaptionsCount();

// Cấu hình hiện tại
$configs = $poster->getConfig();
```

---

## 📊 Định dạng Phản hồi

Mỗi phương thức đều trả về một phản hồi JSON theo chuẩn:

```json
{
  "status": "success",
  "message": "Đăng bài thành công!",
  "timestamp": "2025-10-03 12:00:00",
  "post_id": "123456789_987654321",
  "post_type": "image_caption"
}
```

---

## 🐛 Khắc phục sự cố

<details>
<summary><b>❌ Lỗi Token Không hợp lệ</b></summary>

**Vấn đề:** `Invalid OAuth access token`

**Giải pháp:** 
- Xác minh xem Access Token Trang của bạn có hợp lệ không
- Đảm bảo token có quyền `pages_manage_posts`
- Tạo lại token nếu đã hết hạn
</details>

<details>
<summary><b>🔒 Từ chối Quyền (Permission Denied)</b></summary>

**Vấn đề:** Không thể ghi vào tệp hoặc thư mục

**Giải pháp:**
```bash
chmod 755 images/
chmod 755 logs/
chmod 644 captions.json
```
</details>

<details>
<summary><b>⏱️ Vượt quá Giới hạn Tỷ lệ (Rate Limit)</b></summary>

**Vấn đề:** Quá nhiều yêu cầu tới API Facebook

**Giải pháp:**
- Thư viện sẽ tự động thử lại
- Giảm tần suất đăng bài trong cron
- Đợi vài phút trước khi thử lại
</details>

<details>
<summary><b>📝 Không có Chú thích</b></summary>

**Vấn đề:** `captions.json` trống hoặc không hợp lệ

**Giải pháp:**
- Xác minh định dạng JSON chính xác
- Thêm chú thích vào tệp
- Kiểm tra quyền truy cập tệp
</details>

---

## 🔐 Thực tiễn Tốt nhất

- Lưu trữ token trong các tệp `.env` (không bao giờ commit chúng!)
- Sử dụng biến môi trường cho dữ liệu nhạy cảm
- Đặt quyền truy cập tệp phù hợp (755 cho thư mục, 644 cho tệp)
- Kiểm tra trong môi trường phát triển (development) trước khi đưa lên môi trường thực tế (production)
- Thường xuyên kiểm tra nhật ký (logs)
- Xoay vòng khóa API theo định kỳ

---

## 📄 Giấy phép

Dự án này được cấp phép theo **Giấy phép MIT** - bạn được tự do sử dụng, sửa đổi và chia sẻ! 🎉

---

## 🤝 Đóng góp

Rất hoan nghênh những đóng góp! Đây là cách bạn có thể giúp đỡ:

1. Fork kho lưu trữ
2. Tạo nhánh tính năng của bạn (`git checkout -b feature/amazing-feature`)
3. Commit các thay đổi (`git commit -m 'Add amazing feature'`)
4. Đẩy (Push) lên nhánh đó (`git push origin feature/amazing-feature`)
5. Tạo một Yêu cầu Kéo (Pull Request) 🎯

Phát hiện lỗi? 🐛 [Mở một vấn đề (issue)](https://github.com/Xiata/facebook-auto-poster/issues)

---

<div align="center">

### 🌟 Hãy thả sao cho repo này nếu bạn thấy hữu ích!

Tạo ra với ❤️ và 💦 bởi <b>Xiata</b>

</div>