const TOKEN_KEY = "kriven_admin_token";
let token = localStorage.getItem(TOKEN_KEY) || "";
let currentFilter = "pending";

const loginScreen = document.getElementById("loginScreen");
const appScreen = document.getElementById("appScreen");
const loginError = document.getElementById("loginError");
const passwordInput = document.getElementById("passwordInput");
const statsEl = document.getElementById("stats");
const bookingsEl = document.getElementById("bookings");

function formatPrice(n) {
  if (n === 0) return "бесплатно";
  return n.toLocaleString("ru-RU") + " ₽";
}

function statusLabel(status) {
  if (status === "pending") return "⏳ Ждёт оплату";
  if (status === "confirmed") return "✅ Подтверждена";
  return "❌ Отменена";
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

function showLogin() {
  loginScreen.classList.remove("hidden");
  appScreen.classList.add("hidden");
}

function showApp() {
  loginScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    token = "";
    localStorage.removeItem(TOKEN_KEY);
    showLogin();
    throw new Error("Сессия истекла");
  }
  return { res, data };
}

async function login() {
  loginError.textContent = "";
  const password = passwordInput.value.trim();
  if (!password) {
    loginError.textContent = "Введи пароль";
    return;
  }

  const res = await fetch("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const data = await res.json();

  if (!data.ok) {
    loginError.textContent = data.error || "Ошибка входа";
    return;
  }

  token = data.token;
  localStorage.setItem(TOKEN_KEY, token);
  passwordInput.value = "";
  showApp();
  await loadDashboard();
}

async function loadDashboard() {
  bookingsEl.innerHTML = `<div class="empty">Загрузка...</div>`;
  const { data } = await api(`/api/admin/dashboard?filter=${currentFilter}`);
  if (!data.ok) {
    bookingsEl.innerHTML = `<div class="empty">${data.error || "Ошибка"}</div>`;
    return;
  }

  const s = data.stats;
  statsEl.innerHTML = `
    <div class="stat-card"><div class="stat-value">${s.pending}</div><div class="stat-label">Ждут оплату</div></div>
    <div class="stat-card"><div class="stat-value">${s.today_total}</div><div class="stat-label">Сегодня всего</div></div>
    <div class="stat-card"><div class="stat-value">${s.today_confirmed}</div><div class="stat-label">Сегодня подтв.</div></div>
    <div class="stat-card"><div class="stat-value">${s.upcoming_confirmed}</div><div class="stat-label">Предстоящие</div></div>
  `;

  if (!data.bookings.length) {
    bookingsEl.innerHTML = `<div class="empty">Записей нет</div>`;
    return;
  }

  bookingsEl.innerHTML = data.bookings.map((b) => {
    const username = b.username ? `@${b.username}` : "без username";
    const actions = b.status === "pending"
      ? `<div class="actions">
          <button type="button" class="btn-ok" data-action="confirm" data-id="${b.booking_id}">✅ Оплата получена</button>
          <button type="button" class="btn-no" data-action="cancel" data-id="${b.booking_id}">❌ Отменить</button>
        </div>`
      : "";

    return `
      <div class="card">
        <div class="card-top">
          <div>
            <div class="client">${b.full_name}</div>
            <div class="meta">${username}</div>
          </div>
          <span class="badge ${b.status}">${statusLabel(b.status)}</span>
        </div>
        <div class="meta">📅 ${b.date_label}, ${b.time}</div>
        <div class="services">✂️ ${b.haircut} · 🧔 ${b.beard}</div>
        <div class="money">Итого ${formatPrice(b.total)} · предоплата ${formatPrice(b.prepayment)} · в барбершопе ${formatPrice(b.rest)}</div>
        ${b.payment_code ? `<div class="code">🔑 ${b.payment_code}</div>` : ""}
        ${actions}
      </div>
    `;
  }).join("");
}

async function handleAction(action, bookingId) {
  const path = action === "confirm"
    ? `/api/admin/bookings/${bookingId}/confirm`
    : `/api/admin/bookings/${bookingId}/cancel`;

  const { data } = await api(path, { method: "POST", body: "{}" });
  if (!data.ok) {
    alert(data.error || "Не удалось");
    return;
  }
  await loadDashboard();
}

document.getElementById("loginBtn").onclick = login;
passwordInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") login();
});

document.getElementById("logoutBtn").onclick = () => {
  token = "";
  localStorage.removeItem(TOKEN_KEY);
  showLogin();
};

document.querySelectorAll(".filter").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".filter").forEach((el) => el.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    loadDashboard();
  };
});

bookingsEl.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  handleAction(btn.dataset.action, btn.dataset.id);
});

if (token) {
  showApp();
  loadDashboard().catch(showLogin);
} else {
  showLogin();
}
