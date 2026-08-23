/* 🏮 Trạm Điều Khiển — app.js
   Không dùng framework/build step — vanilla JS, phù hợp triết lý "tự host, tối giản"
   xuyên suốt cả dự án (Ollama local, STT/TTS local, ...). */

const REFRESH_MS = 10_000;
const TOKEN_KEY = "tdk_admin_token";

const PERSONA_LABELS = {
  ban_than: "🧑‍🤝‍🧑 Bạn thân",
  chuyen_gia: "🎓 Chuyên gia",
  hai_huoc: "😄 Dí dỏm",
  co_van: "🧭 Cố vấn",
};

const $ = (id) => document.getElementById(id);

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
function setToken(v) {
  localStorage.setItem(TOKEN_KEY, v);
}

async function apiFetch(path) {
  const headers = {};
  const token = getToken();
  if (token) headers["X-Admin-Token"] = token;
  const res = await fetch(path, { headers });
  if (res.status === 401) {
    const err = new Error("unauthorized");
    err.unauthorized = true;
    throw err;
  }
  if (!res.ok) throw new Error(`Lỗi API ${path}: ${res.status}`);
  return res.json();
}

// ── Cổng token ────────────────────────────────────────────────────────────
function showGate(message) {
  $("gate").hidden = false;
  $("app").hidden = true;
  $("gate-error").textContent = message || "";
}
function showApp() {
  $("gate").hidden = true;
  $("app").hidden = false;
}

$("gate-submit").addEventListener("click", async () => {
  const val = $("gate-input").value.trim();
  if (!val) return;
  setToken(val);
  try {
    await refreshAll();
    showApp();
  } catch (e) {
    showGate("Token không đúng — thử lại.");
  }
});
$("gate-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("gate-submit").click();
});

// ── Định dạng ────────────────────────────────────────────────────────────
function relativeTime(isoStr) {
  if (!isoStr) return "—";
  const then = new Date(isoStr).getTime();
  if (Number.isNaN(then)) return isoStr;
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return "vừa xong";
  const m = Math.floor(diffSec / 60);
  if (m < 60) return `${m} phút trước`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} giờ trước`;
  const d = Math.floor(h / 24);
  return `${d} ngày trước`;
}

function fmtPercent(v) {
  return v === null || v === undefined ? "—" : `${v.toFixed(0)}%`;
}

// ── Đồng hồ ──────────────────────────────────────────────────────────────
function tickClock() {
  $("clock").textContent = new Date().toLocaleTimeString("vi-VN", { hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

// ── Render: trạng thái + số liệu ────────────────────────────────────────
function renderStatus(status) {
  const seal = $("seal");
  const sealText = $("seal-text");
  if (status.ollama_alive) {
    seal.className = "seal seal--online";
    sealText.textContent = "Hoạt động";
  } else {
    seal.className = "seal seal--offline";
    sealText.textContent = "Mất kết nối Ollama";
  }

  $("stat-model").textContent = status.default_model || "—";

  $("stat-cpu").textContent = fmtPercent(status.cpu);
  $("stat-cpu-bar").style.width = `${status.cpu ?? 0}%`;
  $("stat-cpu-bar").className =
    "stat-card__bar-fill" + (status.cpu > 80 ? " stat-card__bar-fill--warn" : "");

  $("stat-ram").textContent = fmtPercent(status.ram_percent);
  $("stat-ram-bar").style.width = `${status.ram_percent ?? 0}%`;
  $("stat-ram-bar").className =
    "stat-card__bar-fill" + (status.ram_percent > 85 ? " stat-card__bar-fill--warn" : "");

  const kv = $("kv-list");
  kv.innerHTML = "";
  const rows = [
    ["Ollama", status.ollama_alive ? `✅ ${status.models.length} model đã cài` : "❌ không kết nối được"],
    ["Model mặc định", status.default_model],
    ["Uptime server", status.uptime_hours != null ? `${status.uptime_hours} giờ` : "— (thiếu psutil)"],
    ["Ổ đĩa đã dùng", fmtPercent(status.disk_percent)],
    ["Người dùng được phép", status.allowed_users_count == null ? "Mở cho tất cả" : status.allowed_users_count],
    ["Quản trị viên", status.admin_users_count],
  ];
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "kv-row";
    row.innerHTML = `<span class="kv-row__label">${label}</span><span class="kv-row__value">${value}</span>`;
    kv.appendChild(row);
  }

  $("server-time-footer").textContent = "Giờ máy chủ: " + new Date(status.server_time).toLocaleString("vi-VN");
}

function renderStats(stats) {
  $("stat-active").textContent = stats.ready ? stats.active_today : "—";
}

function renderLogs(data) {
  const feed = $("log-feed");
  if (!data.lines || data.lines.length === 0) {
    feed.innerHTML = '<div class="log-empty">Chưa có nhật ký nào.</div>';
    return;
  }
  const wasNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 40;
  feed.innerHTML = data.lines
    .map((l) => {
      const level = (l.level || "info").toLowerCase();
      const ts = (l.ts || "").split(" ")[1] || l.ts || "";
      return `<div class="log-line">
        <span class="log-line__ts">${escapeHtml(ts)}</span>
        <span class="log-line__level log-line__level--${level}">${escapeHtml((l.level || "").slice(0, 4))}</span>
        <span class="log-line__msg">${escapeHtml(l.msg || "")}</span>
      </div>`;
    })
    .join("");
  if (wasNearBottom) feed.scrollTop = feed.scrollHeight;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderUsers(data) {
  const tbody = $("users-tbody");
  if (!data.users || data.users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Chưa có người dùng nào trò chuyện.</td></tr>';
    return;
  }
  tbody.innerHTML = data.users
    .map((u) => {
      const roleBadge = u.is_admin
        ? '<span class="badge badge--red">Admin</span>'
        : '<span class="badge badge--muted">Thành viên</span>';
      const webBadge = u.auto_web
        ? '<span class="badge badge--jade">Auto-web</span>'
        : "";
      return `<tr>
        <td class="mono">${u.uid}</td>
        <td>${escapeHtml(u.nickname || "—")}</td>
        <td class="mono">${escapeHtml(u.model)}</td>
        <td>${PERSONA_LABELS[u.persona] || escapeHtml(u.persona)}</td>
        <td class="mono">${u.msg_count}</td>
        <td>${relativeTime(u.last_active)}</td>
        <td>${roleBadge} ${webBadge}</td>
      </tr>`;
    })
    .join("");
}

// ── Vòng lặp làm mới ─────────────────────────────────────────────────────
async function refreshAll() {
  const [status, stats, users, logs] = await Promise.all([
    apiFetch("/api/status"),
    apiFetch("/api/stats"),
    apiFetch("/api/users?limit=100"),
    apiFetch("/api/logs?limit=80"),
  ]);
  renderStatus(status);
  renderStats(stats);
  renderUsers(users);
  renderLogs(logs);
}

async function boot() {
  try {
    await refreshAll();
    showApp();
  } catch (e) {
    if (e.unauthorized) {
      showGate();
    } else {
      showApp();
      $("log-feed").innerHTML = `<div class="log-empty">⚠️ Không tải được dữ liệu: ${escapeHtml(e.message)}</div>`;
    }
  }
  setInterval(async () => {
    try {
      await refreshAll();
    } catch (e) {
      if (e.unauthorized) showGate("Token hết hạn hoặc bị đổi — nhập lại.");
    }
  }, REFRESH_MS);
}

boot();
