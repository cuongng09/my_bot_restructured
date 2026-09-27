/* ==========================================================================
   my_bot · Text Console (Liquid Glass)
   Read-only dashboard for self-hosted Telegram assistant.
   ========================================================================== */

const TOKEN_KEY = "my_bot_admin_token";
const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem(TOKEN_KEY) || "";

/* --------------------------------------------------------------------------
   Token modal (replaces window.prompt)
   -------------------------------------------------------------------------- */
let pendingTokenPromise = null;
let resolveToken = null;

function requestToken() {
  if (pendingTokenPromise) return pendingTokenPromise;

  pendingTokenPromise = new Promise((resolve) => { resolveToken = resolve; });

  const modal = $("token-modal");
  const input = $("token-input");
  input.value = "";
  $("token-error").textContent = "";
  modal.hidden = false;
  // next frame so the transition kicks in
  requestAnimationFrame(() => modal.classList.add("open"));
  setTimeout(() => input.focus(), 80);

  return pendingTokenPromise;
}

function closeTokenModal() {
  const modal = $("token-modal");
  modal.classList.remove("open");
  setTimeout(() => { modal.hidden = true; }, 320);
}

function showTokenError(message) {
  $("token-error").textContent = message;
  const card = document.querySelector(".modal-card");
  card.classList.remove("shake");
  // force reflow to restart animation
  void card.offsetWidth;
  card.classList.add("shake");
}

function bindTokenForm() {
  $("token-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const value = $("token-input").value.trim();
    if (!value) {
      showTokenError("Token không được để trống");
      return;
    }
    const resolver = resolveToken;
    resolveToken = null;
    pendingTokenPromise = null;
    closeTokenModal();
    resolver?.(value);
  });
}

/* --------------------------------------------------------------------------
   API helper
   -------------------------------------------------------------------------- */
async function api(path) {
  const headers = {};
  if (token()) headers["X-Admin-Token"] = token();

  const response = await fetch(path, { headers });

  if (response.status === 401) {
    const value = await requestToken();
    if (!value) throw new Error("Thiếu token");
    localStorage.setItem(TOKEN_KEY, value);
    return api(path);
  }
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

/* --------------------------------------------------------------------------
   Utils
   -------------------------------------------------------------------------- */
const escapeHtml = (value) => String(value ?? "—")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;");

function setText(id, value) {
  const el = $(id);
  if (!el) return;
  el.classList.remove("skel");
  el.textContent = value;
}

/* Animated counter for metric values (requestAnimationFrame, 400ms) */
function animateCount(id, target) {
  const el = $(id);
  if (!el) return;
  el.classList.remove("skel");

  const to = Number(target);
  if (!Number.isFinite(to)) { el.textContent = String(target); return; }

  const from = Number(el.dataset.value ?? 0);
  if (from === to) { el.textContent = to.toLocaleString("vi-VN"); return; }
  el.dataset.value = String(to);

  const start = performance.now();
  const duration = 400;
  const ease = (p) => 1 - Math.pow(1 - p, 3);

  function tick(now) {
    const p = Math.min(1, (now - start) / duration);
    const value = Math.round(from + (to - from) * ease(p));
    el.textContent = value.toLocaleString("vi-VN");
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* --------------------------------------------------------------------------
   Banner (network / fetch errors)
   -------------------------------------------------------------------------- */
function showBanner(message) {
  const el = $("banner");
  el.textContent = message;
  el.hidden = false;
}
function hideBanner() {
  $("banner").hidden = true;
}

/* --------------------------------------------------------------------------
   Users table
   -------------------------------------------------------------------------- */
let usersSignature = null;

function renderUsers(data) {
  const users = Array.isArray(data?.users) ? data.users : [];
  const signature = JSON.stringify(users);
  if (signature === usersSignature) return; // no flicker on identical payload
  usersSignature = signature;

  const tbody = $("user-table");

  if (!users.length) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="empty">Chưa có dữ liệu hội thoại.</td></tr>';
    return;
  }

  tbody.innerHTML = users.map((user) => {
    const admin = user.is_admin
      ? '<span class="admin-dot" title="Admin"></span>'
      : "";
    const webChip = user.auto_web
      ? '<span class="chip on">Bật</span>'
      : '<span class="chip off">Tắt</span>';

    return `<tr>
      <td class="mono">${admin}${escapeHtml(user.uid)}</td>
      <td>${escapeHtml(user.nickname || "—")}</td>
      <td class="mono">${escapeHtml(user.model)}</td>
      <td>${escapeHtml(user.persona)}</td>
      <td>${webChip}</td>
      <td>${escapeHtml(user.msg_count)}</td>
      <td>${escapeHtml(user.last_active)}</td>
    </tr>`;
  }).join("");
}

/* --------------------------------------------------------------------------
   Logs
   -------------------------------------------------------------------------- */
function renderLogs(data) {
  const el = $("logs");
  const lines = Array.isArray(data?.lines) ? data.lines : [];

  if (!lines.length) {
    el.innerHTML = '<p class="muted">Chưa có log hiển thị.</p>';
    return;
  }

  el.innerHTML = lines.slice(0, 12).map((line) => {
    const text = String(line);
    let cls = "log-info";
    if (/\bERROR\b/i.test(text)) cls = "log-error";
    else if (/\bWARN(ING)?\b/i.test(text)) cls = "log-warn";
    return `<div class="log-line ${cls}">${escapeHtml(text)}</div>`;
  }).join("");
}

/* --------------------------------------------------------------------------
   Refresh
   -------------------------------------------------------------------------- */
async function refresh() {
  const button = $("refresh");
  button.setAttribute("aria-busy", "true");
  button.classList.add("busy");

  try {
    const [status, stats, users, logs] = await Promise.all([
      api("/api/status"),
      api("/api/stats"),
      api("/api/users"),
      api("/api/logs").catch(() => ({ lines: [] })),
    ]);

    hideBanner();

    // Status pill
    const conn = $("connection");
    const online = Boolean(status.ollama_alive);
    conn.className = `status ${online ? "online" : "offline"}`;
    $("connection-text").textContent = online
      ? "Ollama online"
      : "Ollama offline";

    // Metrics
    setText("model", status.default_model ?? "—");
    setText("ollama", `${status.models?.length ?? 0} model đã cài`);
    animateCount("users", stats.total_users ?? 0);
    setText("active", `${stats.active_today ?? 0} hoạt động hôm nay`);
    animateCount("messages", stats.total_messages ?? 0);
    setText(
      "allowlist",
      status.allowed_users_count == null ? "Mở" : status.allowed_users_count
    );
    setText("admins", `${status.admin_users_count ?? 0} admin`);

    // Data
    renderUsers(users);
    renderLogs(logs);

    $("updated").textContent = new Date().toLocaleString("vi-VN");
  } catch (error) {
    showBanner(`Không kết nối được: ${error.message}`);
    const conn = $("connection");
    conn.className = "status offline";
    $("connection-text").textContent = "Lỗi kết nối";
  } finally {
    button.removeAttribute("aria-busy");
    button.classList.remove("busy");
  }
}

/* --------------------------------------------------------------------------
   Bootstrap
   -------------------------------------------------------------------------- */
function init() {
  bindTokenForm();

  // Entrance animation
  requestAnimationFrame(() => document.body.classList.add("loaded"));

  $("refresh").addEventListener("click", refresh);

  // First load + poll every 10s
  refresh();
  setInterval(refresh, 10000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}