# Hướng dẫn cài đặt Docker trên Linux (Ubuntu/Debian)

## 1. Kiểm tra Docker đã cài chưa

```bash
docker --version
systemctl status docker
```

## 2. Cài đặt Docker (nếu chưa có)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
```

## 3. Cho phép user hiện tại chạy Docker không cần `sudo`

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 4. Kiểm tra daemon đang chạy

```bash
sudo systemctl start docker
sudo systemctl status docker
```

Nếu lỗi, xem log chi tiết:

```bash
sudo journalctl -u docker -n 50 --no-pager
```

## 5. Cài Docker Compose (thường đi kèm sẵn với bản cài mới)

```bash
docker compose version
```

---

## Triển khai SearXNG bằng Docker Compose

### Cấu trúc thư mục

```
searxng/
├── docker-compose.yml
├── .env
└── core-config/
    └── settings.yml   (tự tạo khi container chạy lần đầu)
```

### File `.env` (chỉ chứa biến mà `docker-compose.yml` cần)

```env
SEARXNG_VERSION=latest
SEARXNG_PORT=8081
#SEARXNG_HOST=[::]
```

> ⚠️ Không dùng file `.env` của project khác (chứa `DB_HOST`, `JWT_SECRET`...) — sẽ không có tác dụng và gây nhầm lẫn.

### Khởi động

```bash
cd searxng
docker compose up -d
docker ps
```

Cột `PORTS` phải hiện `0.0.0.0:8081->8081/tcp`.

### Bật JSON output (bắt buộc nếu code gọi API dạng JSON)

Sửa `core-config/settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Sau đó restart:

```bash
docker compose restart core
```

### Test

```bash
curl -I http://localhost:8081
curl "http://localhost:8081/search?q=test&format=json"
```

---

## Xử lý sự cố thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `failed to connect to the docker API at unix:///var/run/docker.sock` | Docker daemon chưa chạy | `sudo systemctl start docker` |
| `address already in use` (bind port) | Port đã bị chiếm bởi container/app khác | `sudo lsof -i :<port>` để tìm tiến trình, đổi `SEARXNG_PORT` trong `.env` hoặc `docker rm -f <container_cũ>` |
| Đổi `.env` nhưng port cũ vẫn báo lỗi | Container cũ chưa được recreate | `docker compose down && docker compose up -d` |
| `Temporary failure in name resolution` trong log container | Container không có DNS ra ngoài | Thêm vào `docker-compose.yml`:<br>`dns:`<br>`  - 8.8.8.8`<br>`  - 1.1.1.1` |
| `curl` từ host không connect được dù container "Started" | Port mapping chưa áp dụng đúng, hoặc container đã start nhưng chưa listen kịp | Kiểm tra `docker ps` cột `PORTS`, xem log `docker compose logs core` |

## Lệnh hữu ích khác

```bash
docker compose logs core --tail 30      # xem log gần nhất
docker compose down                     # dừng và xóa container
docker exec -it searxng-core sh         # vào bên trong container
docker port searxng-core                # xem port mapping thực tế
```