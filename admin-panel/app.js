const TOKEN_KEY = "kriven_admin_token";
let token = localStorage.getItem(TOKEN_KEY) || "";
let currentFilter = "pending";

const loginScreen = document.getElementById("loginScreen");
const adminLayout = document.getElementById("adminLayout");
const loginError = document.getElementById("loginError");
const passwordInput = document.getElementById("passwordInput");
const statsEl = document.getElementById("stats");
const bookingsEl = document.getElementById("bookings");
const tableFooter = document.getElementById("tableFooter");
const statusFilter = document.getElementById("statusFilter");
const notifyBadge = document.getElementById("notifyBadge");
const toastEl = document.getElementById("toast");

function formatPrice(n) {
  if (n === 0) return "бесплатно";
  return n.toLocaleString("ru-RU") + " ₽";
}

function statusLabel(status) {
  if (status === "pending") return "Ждёт оплату";
  if (status === "confirmed") return "Подтверждена";
  return "Отменена";
}

function showToast(msg) {
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  setTimeout(() => toastEl.classList.add("hidden"), 2800);
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

function showLogin() {
  loginScreen.classList.remove("hidden");
  adminLayout.classList.add("hidden");
}

function showApp() {
  loginScreen.classList.add("hidden");
  adminLayout.classList.remove("hidden");
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

function renderStats(s) {
  statsEl.innerHTML = `
    <div class="stat-card">
      <div class="stat-icon orange">📅</div>
      <div>
        <div class="stat-value">${s.pending}</div>
        <div class="stat-label">Ожидают подтверждения</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon blue">📆</div>
      <div>
        <div class="stat-value">${s.today_total}</div>
        <div class="stat-label">На сегодня</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon green">📋</div>
      <div>
        <div class="stat-value">${s.upcoming_confirmed}</div>
        <div class="stat-label">Ближайшие записи</div>
      </div>
    </div>
  `;
  if (notifyBadge) {
    notifyBadge.textContent = String(s.pending);
    notifyBadge.classList.toggle("hidden", s.pending === 0);
  }
}

function renderTable(bookings) {
  if (!bookings.length) {
    bookingsEl.innerHTML = `
      <tr class="empty-row"><td colspan="8">Записей нет</td></tr>
    `;
    tableFooter.innerHTML = `<span>Нет записей</span><div></div>`;
    return;
  }

  bookingsEl.innerHTML = bookings.map((b) => {
    const contact = b.username ? `@${b.username}` : "Telegram";
    const service = `${b.haircut} + ${b.beard}`;
    const datetime = `${b.date_label}, ${b.time}`;
    const actions = b.status === "pending"
      ? `<div class="action-cell">
          <button type="button" class="btn-confirm" data-action="confirm" data-id="${b.booking_id}">Подтвердить</button>
          <button type="button" class="btn-more" data-action="cancel" data-id="${b.booking_id}" title="Отменить">✕</button>
        </div>`
      : `<div class="action-cell"><button type="button" class="btn-confirm" disabled>—</button></div>`;

    return `
      <tr>
        <td>#${b.booking_id}</td>
        <td class="client-cell">
          <div class="name">${b.full_name}</div>
          ${b.payment_code ? `<div class="sub">${b.payment_code}</div>` : ""}
        </td>
        <td>${contact}</td>
        <td>${service}</td>
        <td>KRIVEN</td>
        <td>${datetime}</td>
        <td><span class="status-pill ${b.status}">${statusLabel(b.status)}</span></td>
        <td>${actions}</td>
      </tr>
    `;
  }).join("");

  const n = bookings.length;
  tableFooter.innerHTML = `
    <span>Показано 1 — ${n} из ${n}</span>
    <div class="pagination">
      <button type="button" class="page-btn" disabled>‹</button>
      <button type="button" class="page-btn active">1</button>
      <button type="button" class="page-btn" disabled>›</button>
    </div>
  `;
}

async function loadDashboard() {
  bookingsEl.innerHTML = `<tr class="empty-row"><td colspan="8">Загрузка...</td></tr>`;
  const { data } = await api(`/api/admin/dashboard?filter=${currentFilter}`);
  if (!data.ok) {
    bookingsEl.innerHTML = `<tr class="empty-row"><td colspan="8">${data.error || "Ошибка"}</td></tr>`;
    return;
  }

  renderStats(data.stats);
  renderTable(data.bookings);
}

async function handleAction(action, bookingId) {
  if (action === "cancel" && !window.confirm("Отменить эту запись?")) return;

  const path = action === "confirm"
    ? `/api/admin/bookings/${bookingId}/confirm`
    : `/api/admin/bookings/${bookingId}/cancel`;

  const { data } = await api(path, { method: "POST", body: "{}" });
  if (!data.ok) {
    showToast(data.error || "Не удалось");
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

document.getElementById("sidebarToggle")?.addEventListener("click", () => {
  document.getElementById("sidebar")?.classList.toggle("collapsed");
});

statusFilter?.addEventListener("change", () => {
  currentFilter = statusFilter.value;
  loadDashboard();
});

document.querySelectorAll(".nav-item[data-page]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const page = btn.dataset.page;
    if (page === "bookings") {
      document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("appScreen").classList.remove("hidden");
      loadDashboard();
      return;
    }
    showToast("Раздел в разработке");
  });
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
