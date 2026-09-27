# Thiết kế WebApp — Trắng / Xanh Liquid Glass

Spec giao diện Trạm Điều Khiển (`src/my_bot/webapp`). Phong cách **white–blue liquid glass**: kính mờ, ánh sáng loang, chuyển động mượt. Không dùng ảnh raster; mọi hiệu ứng bằng CSS + (tuỳ chọn) SVG nhẹ.

Dashboard **read-only**. API không đổi: `/api/status`, `/api/stats`, `/api/users`, `/api/logs`. Auth: `WEBAPP_TOKEN` → header `X-Admin-Token`.

---

## 1. Cảm xúc sản phẩm

Màn hình quản trị như **tấm kính nổi trên mặt nước sáng**: nền trắng lạnh, accent xanh dương, panel trong suốt, viền sáng mỏng. Chuyển cảnh chậm, easing mềm — không bounce giật, không neon tối.

Từ khóa: sạch, lạnh, trong, yên.

Không: nền đen hiện tại, sơn mài đỏ vàng, ảnh banner, Voicebox, nút xuất file.

---

## 2. Design tokens

### Màu

| Token | Giá trị | Dùng |
|---|---|---|
| `--bg-0` | `#F4F8FF` | Nền trang |
| `--bg-1` | `#E8F1FC` | Vùng sâu hơn |
| `--blue-50` | `#E0F0FF` | Glow nhạt |
| `--blue-400` | `#5BA3E8` | Accent phụ |
| `--blue-500` | `#2F7DE1` | Accent chính, CTA |
| `--blue-700` | `#1B4F9C` | Chữ nhấn, heading |
| `--ink` | `#1A2744` | Chữ chính |
| `--ink-mute` | `#5B6B86` | Meta, caption |
| `--glass` | `rgba(255,255,255,0.52)` | Fill panel |
| `--glass-strong` | `rgba(255,255,255,0.78)` | Header, modal |
| `--stroke` | `rgba(255,255,255,0.72)` | Viền sáng |
| `--stroke-blue` | `rgba(47,125,225,0.22)` | Viền hover |
| `--ok` | `#1F9D6A` | Ollama online |
| `--bad` | `#D64545` | Offline / 401 |
| `--shadow` | `0 18px 50px rgba(47,125,225,0.12)` | Đổ bóng lạnh |

Gradient nền (cố định, không ảnh):

```css
background:
  radial-gradient(900px 500px at 12% -10%, rgba(91,163,232,0.28), transparent 55%),
  radial-gradient(700px 420px at 92% 8%, rgba(224,240,255,0.9), transparent 50%),
  radial-gradient(600px 400px at 70% 100%, rgba(47,125,225,0.10), transparent 45%),
  var(--bg-0);
```

Hai **orb** CSS (circle `blur(60px)`, `opacity: 0.45`) trôi chậm bằng `@keyframes drift` 28s / 36s, `transform: translate`. `pointer-events: none`.

### Typography

- UI: `"Plus Jakarta Sans"` hoặc `"Manrope"`, fallback `ui-sans-serif`
- Mono (UID, model): `"IBM Plex Mono"` / `ui-monospace`
- Load Google Fonts **hoặc** self-host woff2 — không phụ thuộc ảnh
- H1: 28–32px, weight 650, tracking `-0.03em`, màu `--blue-700`
- Kicker: 11px, uppercase, letter-spacing `0.16em`, `--ink-mute`
- Body: 14–15px, line-height 1.55

### Glass (bắt buộc mọi panel)

```css
.glass {
  background: var(--glass);
  border: 1px solid var(--stroke);
  border-radius: 22px;
  box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,0.85);
  backdrop-filter: blur(22px) saturate(1.35);
  -webkit-backdrop-filter: blur(22px) saturate(1.35);
}
```

Highlight: `::before` gradient trắng → trong suốt, `height: 40%`, `opacity: 0.55`, `pointer-events: none`, `border-radius` kế thừa.

`prefers-reduced-transparency`: bỏ blur, nền `--glass-strong` đặc.

---

## 3. Chuyển động

Nguyên tắc: **một nhịp** — `cubic-bezier(0.22, 1, 0.36, 1)` (smooth overshoot nhẹ). Thời gian 280–520ms. Không elastic mạnh.

| Hiện tượng | Motion |
|---|---|
| Lần đầu load | Stagger fade-up: header 0ms, metric cards 60ms/card, bảng 180ms, side 240ms. `opacity 0→1`, `translateY(14px)→0`, 480ms |
| Hover glass | `translateY(-3px)`, viền `--stroke-blue`, shadow sâu hơn, 280ms |
| Nút Làm mới | Scale 0.98 lúc `:active`; khi fetch: spinner 16px quay 0.8s linear |
| Badge Ollama | Online: pulse vòng 2s `box-shadow` xanh; offline: không pulse |
| Số liệu | Đếm lên 400ms khi giá trị đổi (JS `requestAnimationFrame`) |
| Bảng | Hàng hover `background: rgba(47,125,225,0.06)`; hàng mới (optional) highlight 1.2s rồi tắt |
| Modal token | Overlay fade 200ms; tấm kính `scale(0.96)→1` + fade 320ms |
| Poll 10s | Không reload DOM toàn trang; chỉ patch text/class. Nếu bảng cùng data: không re-render |
| Orb nền | `transform` only, 28–36s infinite alternate |

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Không dùng: marquee, confetti, parallax chuột nặng, blur animate (chỉ animate transform/opacity).

---

## 4. Bố cục

Max width `1200px`, padding `28px 24px 48px`. Desktop:

```
┌─────────────────────────────────────────────┐
│  kicker + title              [badge status] │
├──────┬──────┬──────┬────────────────────────┤
│ Ollama│ Users│ Msgs │ Quyền                 │
├──────────────────────────────┬──────────────┤
│ Bảng người dùng              │ Scope + logs │
│ (rộng 2/3)                   │ (1/3)        │
├─────────────────────────────────────────────┤
│ footer poll time                            │
└─────────────────────────────────────────────┘
```

Mobile `< 840px`: một cột; topbar xếp dọc; bảng scroll ngang trong `.table-wrap` bo góc kính.

### Topbar

Trái: kicker `SELF-HOSTED · TEXT CONSOLE`, H1 `my_bot` + span nhẹ `liquid glass`.

Phải: pill kính — chấm tròn 8px + `Ollama online/offline`. Không icon ảnh.

### Metric cards (4)

Mỗi card: label uppercase nhỏ, số lớn `--blue-700`, caption mute.

| Card | Nguồn |
|---|---|
| Ollama | `default_model` + `models.length` |
| Người dùng | `total_users` + `active_today` |
| Tin nhắn | `total_messages` |
| Quyền | `allowed_users_count` (`Mở` nếu null) + `admin_users_count` |

### Bảng users

Cột: UID (mono), Nickname, Model, Persona, Web (chip Bật/Tắt), Tin nhắn, Hoạt động.

Chip Web bật: nền `rgba(47,125,225,0.12)`, chữ `--blue-700`. Tắt: xám nhạt.

Hàng `is_admin`: chấm nhỏ xanh trước UID, tooltip “Admin”.

Empty: một dòng giữa bảng, chữ mute “Chưa có dữ liệu hội thoại.”

Nút **Làm mới**: pill xanh `--blue-500`, chữ trắng, hover sáng hơn 6%.

### Cột phải

1. **Phạm vi** — list text, dấu chấm xanh (không emoji lòe). Mục đã loại bỏ: chữ mute, gạch nhẹ.
2. **Nhật ký** — nếu `/api/logs` trả `lines`: 8–12 dòng mono, level INFO/WARN/ERROR màu ink / amber / `--bad`. Hiện API đang trả rỗng: placeholder “Chưa có log hiển thị.”

Footer: `Read-only · làm mới mỗi 10 giây · {updated}` căn giữa, 12px mute.

---

## 5. Màn hình token (401)

Không dùng `prompt()` trình duyệt.

Overlay `rgba(27,79,156,0.18)` + blur 8px. Card kính giữa viewport, max 400px.

- Tiêu đề: “Truy cập bảng điều khiển”
- Mô tả một dòng: nhập `WEBAPP_TOKEN`
- Input password, viền kính, focus ring xanh 2px
- Nút “Vào” full width
- Lỗi sai token: shake ngang 240ms (6px), text `--bad`
- Lưu `localStorage` key hiện tại `my_bot_admin_token`
- Enter submit; Escape không đóng nếu token bắt buộc

---

## 6. HTML / CSS / JS

Giữ 3 file static. Không framework.

**index.html**

- `lang="vi"`, title `my_bot · Console`
- Orbs: 2 `div.orb` trong `body` trước `main`
- Semantic: `header`, `section.metrics`, `section.grid`, `table`, `dialog` hoặc `div[role="dialog"]` cho token
- Không `<img>`

**style.css**

- Tokens `:root`
- Glass, layout, table, chips, motion
- `@media` 840px + reduced-motion + reduced-transparency

**app.js**

- Giữ `api()`, escape HTML, poll 10s
- Thay `prompt` bằng modal
- `classList` stagger lần đầu (`data-animate`)
- So sánh JSON users trước khi `innerHTML`
- Nút refresh: `aria-busy` khi đang fetch

---

## 7. Trạng thái

| State | UI |
|---|---|
| Loading lần đầu | Skeleton glass (shimmer 1.2s linear gradient), không “Đang tải…” thô |
| OK | Số + bảng |
| Ollama down | Badge đỏ, card model vẫn hiện tên config |
| DB chưa ready | Metrics 0, empty table |
| 401 | Modal token |
| Mạng lỗi | Banner kính mỏng trên topbar, chữ `--bad`, tự ẩn khi poll ok |

---

## 8. A11y

- Contrast chữ `--ink` trên kính ≥ 4.5:1 (nếu kính quá trong, tăng `--glass-strong` trên text)
- Focus visible: outline 2px `--blue-500` offset 2px
- Nút có `:focus-visible`
- `prefers-reduced-motion` / `prefers-reduced-transparency`
- Bảng: `th` scope; status dùng text không chỉ màu

---

## 9. Không làm

- Ảnh PNG/JPEG banner, illustration stock
- Dark theme mặc định (có thể thêm later, không trong spec này)
- Chart library nặng
- Particle WebGL
- Thay đổi contract API

---

## 10. Checklist implement

- [ ] Tokens + nền gradient + 2 orb drift
- [ ] `.glass` trên topbar, 4 metrics, 2 panel, footer
- [ ] Stagger load + hover lift
- [ ] Modal token thay `prompt`
- [ ] Chip auto_web, badge Ollama pulse
- [ ] Skeleton + empty + error
- [ ] Reduced motion / transparency
- [ ] Mobile 1 cột, bảng scroll
- [ ] Poll 10s không nhấp nháy bảng

Khi xong, dashboard hiện tại (nền `#0b1018`) được thay bằng bản trắng–xanh kính lỏng; logic fetch giữ nguyên.
