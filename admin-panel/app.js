const TOKEN_KEY = "kriven_admin_token";
let token = localStorage.getItem(TOKEN_KEY) || "";
let currentPage = "bookings";
let currentFilter = "pending";

const PAGES = {
  dashboard: { title: "Панель управления", crumb: "Главная" },
  bookings: { title: "Бронирования", crumb: "Главная / Бронирования" },
  clients: { title: "Клиенты", crumb: "Главная / Клиенты" },
  services: { title: "Услуги", crumb: "Главная / Услуги" },
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
  const service = b.service || `${b.haircut}`;
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
    : `<tr class="empty-row"><td colspan="6">Записей нет</td></tr>`;

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
          <thead><tr><th>ID</th><th>Клиент</th><th>Контакт</th><th>Услуга</th><th>Дата</th><th>Статус</th></tr></thead>
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
    : `<tr class="empty-row"><td colspan="7">Записей нет</td></tr>`;

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
          <thead><tr><th>ID</th><th>Клиент</th><th>Контакт</th><th>Услуга</th><th>Дата и время</th><th>Статус</th><th>Действия</th></tr></thead>
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

function escAttr(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function serviceEditRow(kind, service) {
  const inactive = service.active ? "" : " class=\"row-inactive\"";
  return `<tr${inactive}>
    <td><input type="text" class="svc-input svc-emoji" value="${escAttr(service.emoji)}" maxlength="4" title="Эмодзи" /></td>
    <td><input type="text" class="svc-input svc-name" value="${escAttr(service.name)}" required /></td>
    <td><code>${escAttr(service.key)}</code></td>
    <td><input type="number" class="svc-input svc-price" value="${service.price}" min="0" step="50" /></td>
    <td><label class="svc-toggle"><input type="checkbox" class="svc-active" ${service.active ? "checked" : ""} /> ${service.active ? "Вкл" : "Выкл"}</label></td>
    <td><button type="button" class="btn-small btn-primary" data-save-service data-kind="${kind}" data-key="${escAttr(service.key)}">Сохранить</button></td>
  </tr>`;
}

function bindServiceForms() {
  document.querySelectorAll("[data-save-service]").forEach((btn) => {
    btn.onclick = async () => {
      const row = btn.closest("tr");
      const { kind, key } = btn.dataset;
      const { data: res } = await api(`/api/admin/services/${kind}/${encodeURIComponent(key)}`, {
        method: "PUT",
        body: JSON.stringify({
          emoji: row.querySelector(".svc-emoji")?.value.trim() || "",
          name: row.querySelector(".svc-name")?.value.trim() || "",
          price: Number(row.querySelector(".svc-price")?.value || 0),
          active: row.querySelector(".svc-active")?.checked ?? true,
        }),
      });
      if (res.ok) {
        showToast("Услуга сохранена");
        renderServices();
      } else {
        showToast(res.error || "Ошибка сохранения");
      }
    };
  });

  document.querySelectorAll(".svc-add-form").forEach((form) => {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const kind = form.dataset.kind;
      const fd = new FormData(form);
      const { data: res } = await api(`/api/admin/services/${kind}`, {
        method: "POST",
        body: JSON.stringify({
          emoji: String(fd.get("emoji") || "").trim(),
          name: String(fd.get("name") || "").trim(),
          price: Number(fd.get("price") || 0),
        }),
      });
      if (res.ok) {
        showToast("Услуга добавлена");
        renderServices();
      } else {
        showToast(res.error || "Ошибка");
      }
    };
  });
}

async function renderServices() {
  const { data } = await api("/api/admin/services");
  if (!data.ok) throw new Error();

  const hairRows = data.haircuts.map((s) => serviceEditRow("haircut", s)).join("");
  const beardRows = data.beards.map((s) => serviceEditRow("beard", s)).join("");

  appScreen.innerHTML = pageHead(PAGES.services.title, PAGES.services.crumb) + `
    <p class="hint-block">Изменения сразу попадают в бота и Mini App. Снятая галочка «Вкл» скрывает услугу из записи, но старые брони сохраняются.</p>
    <div class="grid-2">
      <div class="panel">
        <div class="panel-head"><h2 class="panel-title">Стрижки</h2></div>
        <div class="table-wrap">
          <table class="data-table svc-table">
            <thead><tr><th></th><th>Название</th><th>Код</th><th>Цена</th><th>Статус</th><th></th></tr></thead>
            <tbody>${hairRows || `<tr><td colspan="6" class="empty-cell">Нет услуг</td></tr>`}</tbody>
          </table>
        </div>
        <form class="admin-form svc-add-form" data-kind="haircut">
          <div class="svc-add-row">
            <input type="text" name="emoji" placeholder="✂️" maxlength="4" />
            <input type="text" name="name" placeholder="Название" required />
            <input type="number" name="price" placeholder="Цена" min="0" step="50" required />
            <button type="submit" class="btn-primary">Добавить</button>
          </div>
        </form>
      </div>
      <div class="panel">
        <div class="panel-head"><h2 class="panel-title">Борода</h2></div>
        <div class="table-wrap">
          <table class="data-table svc-table">
            <thead><tr><th></th><th>Название</th><th>Код</th><th>Цена</th><th>Статус</th><th></th></tr></thead>
            <tbody>${beardRows || `<tr><td colspan="6" class="empty-cell">Нет услуг</td></tr>`}</tbody>
          </table>
        </div>
        <form class="admin-form svc-add-form" data-kind="beard">
          <div class="svc-add-row">
            <input type="text" name="emoji" placeholder="🧔" maxlength="4" />
            <input type="text" name="name" placeholder="Название" required />
            <input type="number" name="price" placeholder="Цена" min="0" step="50" required />
            <button type="submit" class="btn-primary">Добавить</button>
          </div>
        </form>
      </div>
    </div>`;

  bindServiceForms();
}

async function renderReviews() {
  const { data } = await api("/api/admin/reviews");
  if (!data.ok) throw new Error();

  const list = data.reviews.length
    ? data.reviews.map((r) => `
      <div class="review-card" data-review-id="${r.id}">
        <div class="review-top">
          <input type="text" class="svc-input review-author" value="${escAttr(r.author)}" />
          <select class="review-rating">
            ${[5, 4, 3, 2, 1].map((n) => `<option value="${n}" ${r.rating === n ? "selected" : ""}>${n} ★</option>`).join("")}
          </select>
        </div>
        <textarea class="svc-input review-text" rows="3">${escAttr(r.text)}</textarea>
        <div class="review-actions">
          <span class="review-date">${formatDate(r.created_at)}</span>
          <div class="review-btns">
            <button type="button" class="btn-small btn-primary" data-save-review="${r.id}">Сохранить</button>
            <button type="button" class="btn-text-danger" data-delete-review="${r.id}">Удалить</button>
          </div>
        </div>
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

  document.querySelectorAll("[data-save-review]").forEach((btn) => {
    btn.onclick = async () => {
      const card = btn.closest("[data-review-id]");
      const { data: res } = await api(`/api/admin/reviews/${btn.dataset.saveReview}`, {
        method: "PUT",
        body: JSON.stringify({
          author: card.querySelector(".review-author")?.value.trim(),
          text: card.querySelector(".review-text")?.value.trim(),
          rating: Number(card.querySelector(".review-rating")?.value || 5),
        }),
      });
      if (res.ok) { showToast("Отзыв сохранён"); renderReviews(); }
      else showToast(res.error || "Ошибка");
    };
  });
}

async function renderGallery() {
  const { data } = await api("/api/admin/gallery");
  if (!data.ok) throw new Error();

  const grid = data.items.length
    ? data.items.map((item) => `
      <div class="gallery-card" data-gallery-id="${item.id}">
        <img src="${escAttr(item.image_url)}" alt="${escAttr(item.title)}" loading="lazy" />
        <div class="gallery-card-body gallery-edit-body">
          <input type="text" class="svc-input gallery-title-input" value="${escAttr(item.title)}" />
          <input type="url" class="svc-input gallery-url-input" value="${escAttr(item.image_url)}" />
          <div class="gallery-btns">
            <button type="button" class="btn-small btn-primary" data-save-gallery="${item.id}">Сохранить</button>
            <button type="button" class="btn-text-danger" data-delete-gallery="${item.id}">Удалить</button>
          </div>
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

  document.querySelectorAll("[data-save-gallery]").forEach((btn) => {
    btn.onclick = async () => {
      const card = btn.closest("[data-gallery-id]");
      const { data: res } = await api(`/api/admin/gallery/${btn.dataset.saveGallery}`, {
        method: "PUT",
        body: JSON.stringify({
          title: card.querySelector(".gallery-title-input")?.value.trim(),
          image_url: card.querySelector(".gallery-url-input")?.value.trim(),
        }),
      });
      if (res.ok) { showToast("Фото сохранено"); renderGallery(); }
      else showToast(res.error || "Ошибка");
    };
  });
}

const WEEKDAYS = [
  { v: 0, label: "Пн" }, { v: 1, label: "Вт" }, { v: 2, label: "Ср" },
  { v: 3, label: "Чт" }, { v: 4, label: "Пт" }, { v: 5, label: "Сб" }, { v: 6, label: "Вс" },
];

async function renderSettings() {
  const { data } = await api("/api/admin/settings");
  if (!data.ok) throw new Error();
  const s = data.settings;
  const closed = s.closed_weekdays || [];

  const dayChecks = WEEKDAYS.map((d) => `
    <label class="day-check"><input type="checkbox" name="closed_weekdays" value="${d.v}" ${closed.includes(d.v) ? "checked" : ""} /> ${d.label}</label>
  `).join("");

  appScreen.innerHTML = pageHead(PAGES.settings.title, PAGES.settings.crumb) + `
    <p class="hint-block">Все настройки применяются сразу в боте и Mini App.</p>
    <div class="panel form-panel">
      <div class="panel-head"><h2 class="panel-title">Настройки салона</h2></div>
      <form id="settingsForm" class="admin-form settings-form">
        <label class="field-label">Название салона<input type="text" name="shop_name" value="${escAttr(s.shop_name)}" required /></label>
        <div class="settings-grid-2">
          <label class="field-label">Предоплата %<input type="number" name="prepay_percent" value="${s.prepay_percent}" min="0" max="100" /></label>
          <label class="field-label">Мин. предоплата ₽<input type="number" name="prepay_min" value="${s.prepay_min}" min="0" step="50" /></label>
          <label class="field-label">Телефон СБП<input type="text" name="prepay_phone" value="${escAttr(s.prepay_phone)}" /></label>
          <label class="field-label">Получатель<input type="text" name="prepay_name" value="${escAttr(s.prepay_name)}" /></label>
          <label class="field-label">Начало работы<input type="number" name="work_start_hour" value="${s.work_start_hour}" min="0" max="23" /></label>
          <label class="field-label">Конец работы<input type="number" name="work_end_hour" value="${s.work_end_hour}" min="1" max="24" /></label>
          <label class="field-label">Слот (мин)<input type="number" name="slot_minutes" value="${s.slot_minutes}" min="15" step="15" /></label>
          <label class="field-label">Запись вперёд (дн)<input type="number" name="booking_days_ahead" value="${s.booking_days_ahead}" min="1" max="90" /></label>
          <label class="field-label">Час напоминаний<input type="number" name="reminder_hour" value="${s.reminder_hour}" min="0" max="23" /></label>
          <label class="field-label checkbox-field"><input type="checkbox" name="reminder_enabled" ${s.reminder_enabled ? "checked" : ""} /> Напоминания за день до визита</label>
        </div>
        <div class="field-label">Выходные дни<div class="days-row">${dayChecks}</div></div>
        <label class="field-label">Admin Telegram ID<input type="text" name="admin_chat_id" value="${escAttr(s.admin_chat_id)}" placeholder="123456789" /></label>
        <button type="submit" class="btn-primary">Сохранить настройки</button>
      </form>
    </div>`;

  document.getElementById("settingsForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const closedDays = [...e.target.querySelectorAll('input[name="closed_weekdays"]:checked')].map((cb) => Number(cb.value));
    const { data: res } = await api("/api/admin/settings", {
      method: "PUT",
      body: JSON.stringify({
        shop_name: fd.get("shop_name"),
        prepay_percent: Number(fd.get("prepay_percent")),
        prepay_min: Number(fd.get("prepay_min")),
        prepay_phone: fd.get("prepay_phone"),
        prepay_name: fd.get("prepay_name"),
        work_start_hour: Number(fd.get("work_start_hour")),
        work_end_hour: Number(fd.get("work_end_hour")),
        slot_minutes: Number(fd.get("slot_minutes")),
        booking_days_ahead: Number(fd.get("booking_days_ahead")),
        reminder_hour: Number(fd.get("reminder_hour")),
        reminder_enabled: fd.get("reminder_enabled") === "on",
        closed_weekdays: closedDays,
        admin_chat_id: fd.get("admin_chat_id"),
      }),
    });
    if (res.ok) { showToast("Настройки сохранены"); renderSettings(); }
    else showToast(res.error || "Ошибка");
  };
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
    <div class="panel form-panel">
      <div class="panel-head"><h2 class="panel-title">Сменить пароль админки</h2></div>
      <form id="passwordForm" class="admin-form">
        <input type="password" name="current_password" placeholder="Текущий пароль" required autocomplete="current-password" />
        <input type="password" name="new_password" placeholder="Новый пароль (мин. 4 символа)" required autocomplete="new-password" />
        <button type="submit" class="btn-primary">Обновить пароль</button>
      </form>
      <p class="hint-block">Telegram ID меняется в разделе «Настройки». После смены пароля нужно войти заново.</p>
    </div>`;

  document.getElementById("passwordForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const { data: res } = await api("/api/admin/password", {
      method: "PUT",
      body: JSON.stringify({
        current_password: fd.get("current_password"),
        new_password: fd.get("new_password"),
      }),
    });
    if (res.ok) {
      showToast("Пароль обновлён — войди снова");
      token = "";
      localStorage.removeItem(TOKEN_KEY);
      setTimeout(showLogin, 1200);
    } else {
      showToast(res.error || "Ошибка");
    }
  };
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
