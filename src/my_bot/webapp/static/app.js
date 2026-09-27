const TOKEN_KEY = "my_bot_admin_token";
const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem(TOKEN_KEY) || "";

async function api(path) {
  const headers = {};
  if (token()) headers["X-Admin-Token"] = token();
  const response = await fetch(path, { headers });
  if (response.status === 401) {
    const value = prompt("Nhập WEBAPP_TOKEN:");
    if (!value) throw new Error("Thiếu token");
    localStorage.setItem(TOKEN_KEY, value);
    return api(path);
  }
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

const escapeHtml = (value) => String(value ?? "—")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

function renderUsers(data) {
  $("user-table").innerHTML = data.users?.length
    ? data.users.map((user) => `<tr>
      <td class="mono">${escapeHtml(user.uid)}</td><td>${escapeHtml(user.nickname || "—")}</td>
      <td class="mono">${escapeHtml(user.model)}</td><td>${escapeHtml(user.persona)}</td>
      <td>${user.auto_web ? "Bật" : "Tắt"}</td><td>${escapeHtml(user.msg_count)}</td>
      <td>${escapeHtml(user.last_active)}</td></tr>`).join("")
    : '<tr><td colspan="7">Chưa có dữ liệu hội thoại.</td></tr>';
}

async function refresh() {
  try {
    const [status, stats, users] = await Promise.all([
      api("/api/status"), api("/api/stats"), api("/api/users"),
    ]);
    $("connection").textContent = status.ollama_alive ? "● Ollama online" : "○ Ollama offline";
    $("connection").className = `status ${status.ollama_alive ? "online" : "offline"}`;
    $("model").textContent = status.default_model;
    $("ollama").textContent = `${status.models.length} model đã cài`;
    $("users").textContent = stats.total_users;
    $("active").textContent = `${stats.active_today} hoạt động hôm nay`;
    $("messages").textContent = stats.total_messages;
    $("allowlist").textContent = status.allowed_users_count ?? "Mở";
    $("admins").textContent = `${status.admin_users_count} admin`;
    renderUsers(users);
    $("updated").textContent = new Date().toLocaleString("vi-VN");
  } catch (error) {
    $("connection").textContent = error.message;
    $("connection").className = "status offline";
  }
}

$("refresh").addEventListener("click", refresh);
refresh();
setInterval(refresh, 10000);
