const TOKEN_KEY = "kriven_admin_token";
let token = localStorage.getItem(TOKEN_KEY) || "";
let currentPage = "bookings";
let currentFilter = "pending";

const PAGES = {
  dashboard: { title: "Панель управления", crumb: "Главная" },
  bookings: { title: "Бронирования", crumb: "Главная / Бронирования" },
  clients: { title: "Клиенты", crumb: "Главная / Клиенты" },
  services: { title: "Услуги", crumb: "Главная / Услуги" },
  barbers: { title: "Барберы", crumb: "Главная / Барберы" },
  reviews: { title: "Отзывы", crumb: "Главная / Отзывы" },
  gallery: { title: "Галерея", crumb: "Главная / Галерея" },
  settings: { title: "Настройки", crumb: "Главная / Настройки" },
  users: { title: "Пользователи", crumb: "Главная / Пользователи" },
  logs: { title: "Логи", crumb: "Главная / Логи" },
};

const loginScreen = document.getElementById("loginScreen");
const adminLayout = document.getElementById("adminLayout");
const loginError = document.getElementById("loginError");
const passwordInput = document.getElementById("passwordInput");
const appScreen = document.getElementById("appScreen");
const notifyBadge = document.getElementById("notifyBadge");
const toastEl = document.getElementById("toast");

function formatPrice(n) {
  if (n === 0) return "бесплатно";
  return Number(n).toLocaleString("ru-RU") + " ₽";
}

function statusLabel(status) {
  if (status === "pending") return "Ждёт оплату";
  if (status === "confirmed") return "Подтверждена";
  return "Отменена";
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 16).replace("T", " ");
  return d.toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function showToast(msg) {
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  setTimeout(() => toastEl.classList.add("hidden"), 2800);
}

function authHeaders() {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
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

function pageHead(title, crumb) {
  return `
    <div class="page-head">
      <h1 class="page-title">${title}</h1>
      <div class="breadcrumb">${crumb}</div>
    </div>
  `;
}

function renderStatsRow(s) {
  return `
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon orange">📅</div>
        <div><div class="stat-value">${s.pending}</div><div class="stat-label">Ожидают подтверждения</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon blue">📆</div>
        <div><div class="stat-value">${s.today_total}</div><div class="stat-label">На сегодня</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green">📋</div>
        <div><div class="stat-value">${s.upcoming_confirmed}</div><div class="stat-label">Ближайшие записи</div></div>
      </div>
    </div>
  `;
}

function updateNotifyBadge(pending) {
  if (!notifyBadge) return;
  notifyBadge.textContent = String(pending ?? 0);
  notifyBadge.classList.toggle("hidden", !pending);
}

function bookingRow(b, withActions = true) {
  const contact = b.username ? `@${b.username}` : "Telegram";
  const service = `${b.haircut} + ${b.beard}`;
  const actions = withActions && b.status === "pending"
    ? `<div class="action-cell">
        <button type="button" class="btn-confirm" data-action="confirm" data-id="${b.booking_id}">Подтвердить</button>
        <button type="button" class="btn-more" data-action="cancel" data-id="${b.booking_id}" title="Отменить">✕</button>
      </div>`
    : withActions ? `<div class="action-cell"><button type="button" class="btn-confirm" disabled>—</button></div>` : "";

  return `
    <tr>
      <td>#${b.booking_id}</td>
      <td class="client-cell"><div class="name">${b.full_name}</div>${b.payment_code ? `<div class="sub">${b.payment_code}</div>` : ""}</td>
      <td>${contact}</td>
      <td>${service}</td>
      <td>KRIVEN</td>
      <td>${b.date_label}, ${b.time}</td>
      <td><span class="status-pill ${b.status}">${statusLabel(b.status)}</span></td>
      ${withActions ? `<td>${actions}</td>` : ""}
    </tr>
  `;
}

async function loadPage(page) {
  currentPage = page;
  const meta = PAGES[page];
  appScreen.innerHTML = pageHead(meta.title, meta.crumb) + `<div class="page-loading">Загрузка...</div>`;

  try {
    if (page === "dashboard") await renderDashboard();
    else if (page === "bookings") await renderBookings();
    else if (page === "clients") await renderClients();
    else if (page === "services") await renderServices();
    else if (page === "barbers") await renderBarbers();
    else if (page === "reviews") await renderReviews();
    else if (page === "gallery") await renderGallery();
    else if (page === "settings") await renderSettings();
    else if (page === "users") await renderUsers();
    else if (page === "logs") await renderLogs();
  } catch {
    appScreen.innerHTML = pageHead(meta.title, meta.crumb) + `<div class="empty-panel">Ошибка загрузки</div>`;
  }
}

async function renderDashboard() {
  const { data } = await api("/api/admin/overview");
  if (!data.ok) throw new Error();
  updateNotifyBadge(data.stats.pending);

  const rows = data.recent.length
    ? data.recent.map((b) => bookingRow(b, false)).join("")
    : `<tr class="empty-row"><td colspan="7">Записей нет</td></tr>`;

  appScreen.innerHTML = pageHead(PAGES.dashboard.title, PAGES.dashboard.crumb)
    + renderStatsRow(data.stats)
    + `
    <div class="quick-links">
      <button type="button" class="quick-link" data-goto="bookings">📅 Бронирования</button>
      <button type="button" class="quick-link" data-goto="clients">👤 Клиенты</button>
      <button type="button" class="quick-link" data-goto="services">✂️ Услуги</button>
      <button type="button" class="quick-link" data-goto="logs">📋 Логи</button>
    </div>
    <div class="panel">
      <div class="panel-head"><h2 class="panel-title">Последние записи</h2></div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>ID</th><th>Клиент</th><th>Контакт</th><th>Услуга</th><th>Барбер</th><th>Дата</th><th>Статус</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

async function renderBookings() {
  const { data } = await api(`/api/admin/dashboard?filter=${currentFilter}`);
  if (!data.ok) throw new Error();
  updateNotifyBadge(data.stats.pending);

  const rows = data.bookings.length
    ? data.bookings.map((b) => bookingRow(b)).join("")
    : `<tr class="empty-row"><td colspan="8">Записей нет</td></tr>`;

  appScreen.innerHTML = pageHead(PAGES.bookings.title, PAGES.bookings.crumb)
    + renderStatsRow(data.stats)
    + `
    <div class="panel">
      <div class="panel-head">
        <h2 class="panel-title">Список бронирований</h2>
        <select class="status-select" id="statusFilter">
          <option value="pending" ${currentFilter === "pending" ? "selected" : ""}>Ждут оплату</option>
          <option value="today" ${currentFilter === "today" ? "selected" : ""}>Сегодня</option>
          <option value="upcoming" ${currentFilter === "upcoming" ? "selected" : ""}>Предстоящие</option>
          <option value="all" ${currentFilter === "all" ? "selected" : ""}>Все статусы</option>
        </select>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>ID</th><th>Клиент</th><th>Контакт</th><th>Услуга</th><th>Барбер</th><th>Дата и время</th><th>Статус</th><th>Действия</th></tr></thead>
          <tbody id="bookingsBody">${rows}</tbody>
        </table>
      </div>
      <div class="table-footer"><span>Показано ${data.bookings.length} из ${data.bookings.length}</span></div>
    </div>`;

  document.getElementById("statusFilter")?.addEventListener("change", (e) => {
    currentFilter = e.target.value;
    renderBookings();
  });
}

async function renderClients() {
  const { data } = await api("/api/admin/clients");
  if (!data.ok) throw new Error();

  const rows = data.clients.length
    ? data.clients.map((c) => `
      <tr>
        <td>${c.user_id}</td>
        <td class="client-cell"><div class="name">${c.full_name}</div></td>
        <td>${c.username ? `@${c.username}` : "—"}</td>
        <td>${c.bookings_count}</td>
        <td>${c.confirmed_count}</td>
        <td>${formatDate(c.last_booking)}</td>
      </tr>`).join("")
    : `<tr class="empty-row"><td colspan="6">Клиентов пока нет</td></tr>`;

  appScreen.innerHTML = pageHead(PAGES.clients.title, PAGES.clients.crumb) + `
    <div class="panel">
      <div class="panel-head"><h2 class="panel-title">База клиентов</h2><span class="panel-meta">${data.clients.length} чел.</span></div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>ID</th><th>Имя</th><th>Telegram</th><th>Записей</th><th>Подтверждено</th><th>Последняя запись</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

async function renderServices() {
  const { data } = await api("/api/admin/services");
  if (!data.ok) throw new Error();

  const hairRows = data.haircuts.map((s) => `
    <tr><td>${s.emoji} ${s.name}</td><td><code>${s.key}</code></td><td>${formatPrice(s.price)}</td></tr>
  `).join("");

  const beardRows = data.beards.map((s) => `
    <tr><td>${s.emoji} ${s.name}</td><td><code>${s.key}</code></td><td>${formatPrice(s.price)}</td></tr>
  `).join("");

  appScreen.innerHTML = pageHead(PAGES.services.title, PAGES.services.crumb) + `
    <div class="grid-2">
      <div class="panel">
        <div class="panel-head"><h2 class="panel-title">Стрижки</h2></div>
        <div class="table-wrap">
          <table class="data-table"><thead><tr><th>Услуга</th><th>Код</th><th>Цена</th></tr></thead><tbody>${hairRows}</tbody></table>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head"><h2 class="panel-title">Борода</h2></div>
        <div class="table-wrap">
          <table class="data-table"><thead><tr><th>Услуга</th><th>Код</th><th>Цена</th></tr></thead><tbody>${beardRows}</tbody></table>
        </div>
      </div>
    </div>
    <p class="hint-block">Изменение прайса — в файле <code>catalog.py</code> или через разработчика.</p>`;
}

async function renderBarbers() {
  const { data } = await api("/api/admin/barbers");
  if (!data.ok) throw new Error();

  const cards = data.barbers.map((b) => `
    <div class="info-card">
      <div class="info-card-top">
        <div class="info-avatar">🧔</div>
        <div>
          <div class="info-title">${b.name}</div>
          <div class="info-sub">${b.role}</div>
        </div>
        <span class="status-pill ${b.active ? "confirmed" : "cancelled"}">${b.active ? "Активен" : "Неактивен"}</span>
      </div>
      <div class="info-meta">ID: ${b.id}</div>
    </div>
  `).join("");

  appScreen.innerHTML = pageHead(PAGES.barbers.title, PAGES.barbers.crumb) + `
    <div class="cards-grid">${cards}</div>
    <p class="hint-block">Список мастеров настраивается в <code>config.py</code> → BARBERS.</p>`;
}

async function renderReviews() {
  const { data } = await api("/api/admin/reviews");
  if (!data.ok) throw new Error();

  const list = data.reviews.length
    ? data.reviews.map((r) => `
      <div class="review-card">
        <div class="review-top">
          <div><strong>${r.author}</strong> <span class="stars">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</span></div>
          <button type="button" class="btn-text-danger" data-delete-review="${r.id}">Удалить</button>
        </div>
        <p class="review-text">${r.text}</p>
        <div class="review-date">${formatDate(r.created_at)}</div>
      </div>`).join("")
    : `<div class="empty-panel">Отзывов пока нет. Добавь первый ниже.</div>`;

  appScreen.innerHTML = pageHead(PAGES.reviews.title, PAGES.reviews.crumb) + `
    <div class="panel">
      <div class="panel-head"><h2 class="panel-title">Отзывы клиентов</h2></div>
      <div class="reviews-list">${list}</div>
    </div>
    <div class="panel form-panel">
      <div class="panel-head"><h2 class="panel-title">Добавить отзыв</h2></div>
      <form id="reviewForm" class="admin-form">
        <input type="text" name="author" placeholder="Имя клиента" required />
        <textarea name="text" rows="3" placeholder="Текст отзыва" required></textarea>
        <select name="rating">
          <option value="5">5 ★</option><option value="4">4 ★</option><option value="3">3 ★</option>
        </select>
        <button type="submit" class="btn-primary">Сохранить</button>
      </form>
    </div>`;

  document.getElementById("reviewForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const { data: res } = await api("/api/admin/reviews", {
      method: "POST",
      body: JSON.stringify({
        author: fd.get("author"),
        text: fd.get("text"),
        rating: Number(fd.get("rating")),
      }),
    });
    if (res.ok) { showToast("Отзыв добавлен"); renderReviews(); }
    else showToast(res.error || "Ошибка");
  };
}

async function renderGallery() {
  const { data } = await api("/api/admin/gallery");
  if (!data.ok) throw new Error();

  const grid = data.items.length
    ? data.items.map((item) => `
      <div class="gallery-card">
        <img src="${item.image_url}" alt="${item.title}" loading="lazy" />
        <div class="gallery-card-body">
          <div class="gallery-title">${item.title}</div>
          <button type="button" class="btn-text-danger" data-delete-gallery="${item.id}">Удалить</button>
        </div>
      </div>`).join("")
    : `<div class="empty-panel">Галерея пуста</div>`;

  appScreen.innerHTML = pageHead(PAGES.gallery.title, PAGES.gallery.crumb) + `
    <div class="gallery-grid">${grid}</div>
    <div class="panel form-panel">
      <div class="panel-head"><h2 class="panel-title">Добавить фото</h2></div>
      <form id="galleryForm" class="admin-form">
        <input type="text" name="title" placeholder="Название" required />
        <input type="url" name="image_url" placeholder="Ссылка на изображение" required />
        <button type="submit" class="btn-primary">Добавить</button>
      </form>
    </div>`;

  document.getElementById("galleryForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const { data: res } = await api("/api/admin/gallery", {
      method: "POST",
      body: JSON.stringify({ title: fd.get("title"), image_url: fd.get("image_url") }),
    });
    if (res.ok) { showToast("Фото добавлено"); renderGallery(); }
    else showToast(res.error || "Ошибка");
  };
}

async function renderSettings() {
  const { data } = await api("/api/admin/settings");
  if (!data.ok) throw new Error();
  const s = data.settings;

  const rows = [
    ["Салон", s.shop_name],
    ["Предоплата %", s.prepay_percent + "%"],
    ["Мин. предоплата", formatPrice(s.prepay_min)],
    ["Телефон СБП", s.prepay_phone],
    ["Получатель", s.prepay_name],
    ["Часы работы", s.work_hours],
    ["Слот", s.slot_minutes + " мин"],
    ["Выходные", s.closed_days],
    ["Запись вперёд", s.days_ahead + " дн."],
    ["Напоминания", s.reminder_enabled ? `Да, в ${s.reminder_hour}:00` : "Нет"],
    ["Admin Telegram ID", s.admin_chat_id],
  ];

  appScreen.innerHTML = pageHead(PAGES.settings.title, PAGES.settings.crumb) + `
    <div class="panel">
      <div class="panel-head"><h2 class="panel-title">Текущие настройки</h2></div>
      <div class="settings-list">
        ${rows.map(([k, v]) => `<div class="settings-row"><span>${k}</span><strong>${v}</strong></div>`).join("")}
      </div>
    </div>
    <p class="hint-block">Меняются через переменные Render и файлы <code>config.py</code> / <code>.env</code>.</p>`;
}

async function renderUsers() {
  const { data } = await api("/api/admin/users");
  if (!data.ok) throw new Error();

  const rows = data.users.map((u) => `
    <tr>
      <td>${u.id}</td>
      <td>${u.name}</td>
      <td>${u.role}</td>
      <td>${u.telegram_id}</td>
    </tr>
  `).join("");

  appScreen.innerHTML = pageHead(PAGES.users.title, PAGES.users.crumb) + `
    <div class="panel">
      <div class="panel-head"><h2 class="panel-title">Администраторы</h2></div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>ID</th><th>Логин</th><th>Роль</th><th>Telegram ID</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
    <p class="hint-block">Пароль админки — переменная <code>ADMIN_PASSWORD</code> в Render.</p>`;
}

async function renderLogs() {
  const { data } = await api("/api/admin/logs");
  if (!data.ok) throw new Error();

  const rows = data.logs.length
    ? data.logs.map((log) => `
      <tr>
        <td>#${log.id}</td>
        <td>${log.action}</td>
        <td>${log.full_name}</td>
        <td>${log.username ? `@${log.username}` : "—"}</td>
        <td>${log.datetime}</td>
        <td><span class="status-pill ${log.status}">${statusLabel(log.status)}</span></td>
        <td>${formatDate(log.created_at)}</td>
      </tr>`).join("")
    : `<tr class="empty-row"><td colspan="7">Логов нет</td></tr>`;

  appScreen.innerHTML = pageHead(PAGES.logs.title, PAGES.logs.crumb) + `
    <div class="panel">
      <div class="panel-head"><h2 class="panel-title">Журнал событий</h2></div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>ID</th><th>Событие</th><th>Клиент</th><th>Контакт</th><th>Запись</th><th>Статус</th><th>Создано</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

async function handleAction(action, bookingId) {
  if (action === "cancel" && !window.confirm("Отменить эту запись?")) return;
  const path = action === "confirm"
    ? `/api/admin/bookings/${bookingId}/confirm`
    : `/api/admin/bookings/${bookingId}/cancel`;
  const { data } = await api(path, { method: "POST", body: "{}" });
  if (!data.ok) { showToast(data.error || "Не удалось"); return; }
  showToast(action === "confirm" ? "Запись подтверждена" : "Запись отменена");
  if (currentPage === "bookings") renderBookings();
  else if (currentPage === "dashboard") renderDashboard();
}

function navigate(page) {
  document.querySelectorAll(".nav-item[data-page]").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === page);
  });
  loadPage(page);
}

async function login() {
  loginError.textContent = "";
  const password = passwordInput.value.trim();
  if (!password) { loginError.textContent = "Введи пароль"; return; }

  const res = await fetch("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const data = await res.json();
  if (!data.ok) { loginError.textContent = data.error || "Ошибка входа"; return; }

  token = data.token;
  localStorage.setItem(TOKEN_KEY, token);
  passwordInput.value = "";
  showApp();
  navigate("dashboard");
}

document.getElementById("loginBtn").onclick = login;
passwordInput.addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });

document.getElementById("logoutBtn").onclick = () => {
  token = "";
  localStorage.removeItem(TOKEN_KEY);
  showLogin();
};

document.getElementById("sidebarToggle")?.addEventListener("click", () => {
  document.getElementById("sidebar")?.classList.toggle("collapsed");
});

document.querySelectorAll(".nav-item[data-page]").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.page));
});

appScreen.addEventListener("click", async (e) => {
  const actionBtn = e.target.closest("[data-action]");
  if (actionBtn) {
    handleAction(actionBtn.dataset.action, actionBtn.dataset.id);
    return;
  }

  const goto = e.target.closest("[data-goto]");
  if (goto) { navigate(goto.dataset.goto); return; }

  const delReview = e.target.closest("[data-delete-review]");
  if (delReview) {
    if (!window.confirm("Удалить отзыв?")) return;
    const { data } = await api(`/api/admin/reviews/${delReview.dataset.deleteReview}`, { method: "DELETE" });
    if (data.ok) { showToast("Удалено"); renderReviews(); }
    return;
  }

  const delGallery = e.target.closest("[data-delete-gallery]");
  if (delGallery) {
    if (!window.confirm("Удалить фото?")) return;
    const { data } = await api(`/api/admin/gallery/${delGallery.dataset.deleteGallery}`, { method: "DELETE" });
    if (data.ok) { showToast("Удалено"); renderGallery(); }
  }
});

if (token) {
  showApp();
  navigate("dashboard").catch(showLogin);
} else {
  showLogin();
}
