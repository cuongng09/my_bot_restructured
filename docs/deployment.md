# Hướng Dẫn Triển Khai & Vận Hành `my_bot`

## 1. Cài Đặt Trong Môi Trường Python (Local / Server)

### Bước 1: Chuẩn bị môi trường
```bash
# Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Nâng cấp pip và cài đặt gói
pip install --upgrade pip
pip install -e ".[dev]"
```

### Bước 2: Cấu hình
```bash
cp .env.example .env
nano .env  # Điền TELEGRAM_TOKEN
```

### Bước 3: Khởi chạy
```bash
# Chạy Bot Telegram
python -m my_bot.main
# Hoặc dùng lệnh CLI đã được tạo qua pyproject.toml:
my-bot

# Chạy Trạm Điều Khiển Web (trên một terminal khác hoặc service riêng)
python -m my_bot.webapp.main
# Hoặc dùng lệnh CLI:
my-bot-web
```

---

## 2. Triển Khai Bằng Docker & Docker Compose

Kiểm tra Compose trước khi chạy:

```bash
docker compose version
```

Nếu lệnh trên báo `unknown shorthand flag`, máy đang thiếu Compose plugin.
Cài Docker Compose plugin theo tài liệu Docker hoặc dùng binary tương thích cũ:

```bash
docker-compose version
docker-compose up -d --build
docker-compose logs -f bot
```

Khi đã cài Compose plugin, dùng cú pháp hiện đại:

```bash
# Khởi chạy toàn bộ hệ sinh thái (Bot + Web Dashboard)
docker compose up -d --build

# Xem nhật ký hoạt động
docker compose logs -f bot
```

Trong Docker Compose, bot kết nối tới SearXNG bằng địa chỉ nội bộ
`http://searxng:8080`; không dùng `localhost:8081` từ bên trong container.
Port `8081` chỉ dành cho truy cập SearXNG từ máy host.

Nếu log vẫn báo lỗi kết nối SearXNG, kiểm tra container dịch vụ:

```bash
docker compose ps searxng
docker compose logs --tail=100 searxng
```

---

## 3. Chạy Dưới Dạng Dịch Vụ Hệ Thống (Linux Systemd)

```bash
# Copy file cấu hình service
sudo cp scripts/systemd/my_bot.service /etc/systemd/system/my_bot.service

# Chỉnh sửa đường dẫn thực tế trong file service nếu cần
sudo nano /etc/systemd/system/my_bot.service

# Kích hoạt và khởi động
sudo systemctl daemon-reload
sudo systemctl enable --now my_bot

# Kiểm tra trạng thái
sudo systemctl status my_bot
```

---

## 4. Chạy Dưới Dạng Windows Service (NSSM)

Mở PowerShell với quyền Administrator:
```powershell
# Cài đặt service
.\scripts\nssm\install_nssm_service.ps1

# Gỡ bỏ service khi không dùng
.\scripts\nssm\uninstall_nssm_service.ps1
```
