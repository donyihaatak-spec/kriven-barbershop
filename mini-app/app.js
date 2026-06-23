const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor("#080808");
  tg.setBackgroundColor("#080808");
}

const MONTHS = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];
const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

let catalog = null;
let step = 0;
let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth();
let bookedTimes = [];
let activeTab = "book";

const booking = {
  date: null,
  time: null,
  haircut: null,
  beard: null,
};

const screen = document.getElementById("screen");
const tabsEl = document.getElementById("tabs");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");

function updateProgress(s) {
  step = s;
  if (progressFill) {
    progressFill.style.width = ((s + 1) / 5) * 100 + "%";
  }
}

function setScreenHtml(html) {
  screen.innerHTML = html;
  screen.style.animation = "none";
  void screen.offsetWidth;
  screen.style.animation = "";
}

function setProgressVisible(visible) {
  if (progressBar) progressBar.classList.toggle("hidden", !visible);
}

function setTabsVisible(visible) {
  if (tabsEl) tabsEl.classList.toggle("hidden", !visible);
  document.querySelector(".app")?.classList.toggle("no-tabs", !visible);
}

function calcPrepayment(total) {
  const cfg = catalog?.config || {};
  const percent = cfg.prepayPercent ?? 50;
  const min = cfg.prepayMin ?? 300;
  if (total <= 0) return 0;
  const amount = Math.max(min, Math.round(total * percent / 100));
  return Math.min(amount, total);
}

async function loadCatalog() {
  if (window.KRIVEN_CATALOG) {
    catalog = window.KRIVEN_CATALOG;
    return;
  }
  const res = await fetch("/api/catalog");
  catalog = await res.json();
}

function formatPrice(n) {
  if (n === 0) return "бесплатно";
  return n.toLocaleString("ru-RU") + " ₽";
}

function toIsoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatDateLabel(iso) {
  const d = new Date(iso + "T12:00:00");
  return `${WEEKDAYS[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

function setActiveTab(tab) {
  stopStatusPoll();
  activeTab = tab;
  tabsEl?.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  setProgressVisible(tab === "book");
  if (tab === "book") {
    renderDateScreen();
  } else {
    renderMyBookingsScreen();
  }
}

let mainButtonHandler = null;

function setMainButton(text, onClick) {
  if (!tg) return;
  if (mainButtonHandler) {
    tg.MainButton.offClick(mainButtonHandler);
  }
  mainButtonHandler = onClick;
  tg.MainButton.setText(text);
  tg.MainButton.enable();
  tg.MainButton.show();
  tg.MainButton.onClick(mainButtonHandler);
}

function hideMainButton() {
  if (!tg) return;
  if (mainButtonHandler) {
    tg.MainButton.offClick(mainButtonHandler);
    mainButtonHandler = null;
  }
  tg.MainButton.hide();
}

async function submitBooking() {
  if (!booking.date || !booking.time || !booking.haircut || !booking.beard) {
    tg?.showAlert?.("Заполни все поля");
    return;
  }

  const payload = {
    date: booking.date,
    time: booking.time,
    haircut: booking.haircut,
    beard: booking.beard,
  };

  const btn = document.getElementById("confirmBtn");
  if (btn) btn.disabled = true;
  tg?.MainButton?.showProgress?.();

  try {
    if (tg?.initData) {
      const res = await fetch("/api/book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, initData: tg.initData }),
      });
      const result = await res.json();

      if (result.ok) {
        tg?.MainButton?.hideProgress?.();
        hideMainButton();
        renderPendingScreen(result.message, result.payment_code, result.booking_id);
        return;
      }

      const err = result.error || result.message || "Не удалось записаться";
      tg?.showAlert?.(err);
      if (btn) btn.disabled = false;
      tg?.MainButton?.hideProgress?.();
      return;
    }

    if (tg?.sendData) {
      tg.sendData(JSON.stringify(payload));
      return;
    }

    tg?.showAlert?.("Открой через бота");
    if (btn) btn.disabled = false;
    tg?.MainButton?.hideProgress?.();
  } catch {
    tg?.showAlert?.("Ошибка сети. Проверь интернет и попробуй снова.");
    if (btn) btn.disabled = false;
    tg?.MainButton?.hideProgress?.();
  }
}

function renderPendingScreen(message, paymentCode, bookingId) {
  stopStatusPoll();
  setProgressVisible(false);
  setTabsVisible(false);
  setScreenHtml(`
    <div class="success-screen pending-state">
      <div class="success-title" id="pendingTitle">Ждём оплату</div>
      ${paymentCode ? `<div class="payment-code" id="paymentCode">${paymentCode}</div>` : ""}
      <div class="success-text" id="successMsg"></div>
      <p class="pending-hint" id="pendingHint">После перевода подтвердим запись. Статус — в «Мои записи».</p>
    </div>
  `);
  const msgEl = document.getElementById("successMsg");
  if (msgEl) msgEl.textContent = message;
  if (tg?.initData && (paymentCode || bookingId)) {
    startStatusPoll({ paymentCode, bookingId });
  }
}

let statusPollTimer = null;
let statusPollTarget = null;

function stopStatusPoll() {
  if (statusPollTimer) {
    clearInterval(statusPollTimer);
    statusPollTimer = null;
  }
  statusPollTarget = null;
}

function formatConfirmedMessage(b) {
  let text = `${b.date_label}, ${b.time}\n${b.haircut}, ${b.beard}\nСумма: ${formatPrice(b.total)}`;
  if (b.prepayment) {
    text += `\nПредоплата: ${formatPrice(b.prepayment)}`;
    text += `\nВ салоне: ${formatPrice(b.rest)}`;
  }
  text += "\n\nЖдём в KRIVEN";
  return text;
}

async function fetchBookingStatus({ paymentCode, bookingId }) {
  const body = { initData: tg.initData };
  if (bookingId) body.booking_id = bookingId;
  if (paymentCode) body.payment_code = paymentCode;

  const res = await fetch("/api/booking-status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) return res.json();

  // Fallback for older deploys: scan my-bookings
  const listRes = await fetch("/api/my-bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ initData: tg.initData }),
  });
  const listData = await listRes.json();
  if (!listData.ok || !listData.bookings?.length) return { ok: false };

  const match = listData.bookings.find((b) => {
    if (bookingId && b.booking_id === bookingId) return true;
    return paymentCode && b.payment_code === paymentCode;
  });
  if (!match) return { ok: false };

  return {
    ok: true,
    status: match.status,
    booking: {
      date_label: match.date_label,
      time: match.time,
      haircut: match.haircut,
      beard: match.beard,
      total: match.total,
      prepayment: match.prepayment,
      rest: match.rest,
    },
  };
}

function startStatusPoll(target) {
  stopStatusPoll();
  statusPollTarget = target;

  const poll = async () => {
    if (!statusPollTarget || !tg?.initData) return;
    try {
      const data = await fetchBookingStatus(statusPollTarget);
      if (!data.ok) return;
      if (data.status === "confirmed") {
        stopStatusPoll();
        playConfirmedTransition(data.booking);
      } else if (data.status === "cancelled") {
        stopStatusPoll();
        playCancelledTransition(data.booking);
      }
    } catch {
      /* retry on next tick */
    }
  };

  poll();
  statusPollTimer = setInterval(poll, 2000);
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && statusPollTarget) {
    fetchBookingStatus(statusPollTarget).then((data) => {
      if (!data.ok) return;
      if (data.status === "confirmed") {
        stopStatusPoll();
        playConfirmedTransition(data.booking);
      } else if (data.status === "cancelled") {
        stopStatusPoll();
        playCancelledTransition(data.booking);
      }
    }).catch(() => {});
  }
});

function playConfirmedTransition(booking) {
  const root = screen.querySelector(".success-screen");
  if (!root) return;

  root.classList.add("is-transitioning");
  root.querySelector("#paymentCode")?.classList.add("fade-out");
  root.querySelector("#pendingHint")?.classList.add("fade-out");

  setTimeout(() => {
    root.querySelector("#paymentCode")?.remove();
    root.querySelector("#pendingHint")?.remove();

    const title = root.querySelector("#pendingTitle");
    if (title) {
      title.textContent = "Запись подтверждена";
      title.classList.add("confirmed-title");
    }

    if (!root.querySelector(".confirm-check")) {
      const check = document.createElement("div");
      check.className = "confirm-check";
      check.innerHTML = '<span class="confirm-check-mark">✓</span>';
      root.insertBefore(check, root.firstChild);
    }

    const msgEl = root.querySelector("#successMsg");
    if (msgEl && booking) {
      msgEl.textContent = formatConfirmedMessage(booking);
      msgEl.classList.add("confirmed-card");
    }

    root.classList.remove("pending-state", "is-transitioning");
    root.classList.add("confirmed-state");
    setTabsVisible(true);
    tg?.HapticFeedback?.notificationOccurred?.("success");
  }, 420);
}

function playCancelledTransition(booking) {
  const root = screen.querySelector(".success-screen");
  if (!root) return;

  root.classList.add("is-transitioning", "cancelled-state");
  root.querySelector("#paymentCode")?.classList.add("fade-out");
  root.querySelector("#pendingHint")?.classList.add("fade-out");

  setTimeout(() => {
    root.querySelector("#paymentCode")?.remove();
    root.querySelector("#pendingHint")?.remove();

    const title = root.querySelector("#pendingTitle");
    if (title) title.textContent = "Запись отменена";

    const msgEl = root.querySelector("#successMsg");
    if (msgEl && booking) {
      msgEl.textContent = `${booking.date_label}, ${booking.time}`;
    }

    root.classList.remove("pending-state", "is-transitioning");
    setTabsVisible(true);
    tg?.HapticFeedback?.notificationOccurred?.("error");
  }, 420);
}

async function renderMyBookingsScreen() {
  hideMainButton();
  setTabsVisible(true);
  screen.innerHTML = `<div class="loading">Загрузка...</div>`;

  if (!tg?.initData) {
    screen.innerHTML = `
      <div class="screen-title">Мои записи</div>
      <div class="empty-state">Открой через бота</div>
    `;
    return;
  }

  try {
    const res = await fetch("/api/my-bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData: tg.initData }),
    });
    const data = await res.json();

    if (!data.ok) {
      screen.innerHTML = `
        <div class="screen-title">Мои записи</div>
        <div class="empty-state">${data.error || "Не удалось загрузить"}</div>
      `;
      return;
    }

    if (!data.bookings?.length) {
      screen.innerHTML = `
        <div class="screen-title">Мои записи</div>
        <div class="empty-state">Записей нет</div>
      `;
      return;
    }

    screen.innerHTML = `
      <div class="screen-title">Мои записи</div>
      <div class="bookings-list">
        ${data.bookings.map((b) => {
          const status = b.status === "confirmed" ? "подтверждена" : "ждёт оплату";
          const codeLine = b.status === "pending" && b.payment_code
            ? `<div class="booking-code">Код: ${b.payment_code}</div>`
            : "";
          const cancelBtn = b.can_cancel
            ? `<button type="button" class="cancel-booking-btn" data-id="${b.booking_id}">Отменить</button>`
            : "";
          return `
          <div class="booking-card ${b.status}">
            <div class="booking-status">${status}</div>
            <div class="booking-date">${b.date_label}, ${b.time}</div>
            <div class="booking-meta">${b.haircut}, ${b.beard}</div>
            <div class="booking-meta">${formatPrice(b.total)} · предоплата ${formatPrice(b.prepayment)}</div>
            ${codeLine}
            ${cancelBtn}
          </div>
        `}).join("")}
      </div>
    `;

    screen.querySelectorAll(".cancel-booking-btn").forEach((btn) => {
      btn.onclick = () => cancelBooking(Number(btn.dataset.id), btn);
    });
  } catch {
    screen.innerHTML = `
      <div class="screen-title">Мои записи</div>
      <div class="empty-state">Ошибка сети. Попробуй позже.</div>
    `;
  }
}

function askConfirm(message) {
  return new Promise((resolve) => {
    if (tg?.showConfirm) {
      tg.showConfirm(message, resolve);
      return;
    }
    resolve(window.confirm(message));
  });
}

async function cancelBooking(bookingId, btn) {
  if (!tg?.initData) {
    tg?.showAlert?.("Открой через бота");
    return;
  }

  const confirmed = await askConfirm("Отменить эту запись?");
  if (!confirmed) return;

  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/cancel-booking", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData: tg.initData, booking_id: bookingId }),
    });
    const data = await res.json();
    if (data.ok) {
      tg?.HapticFeedback?.notificationOccurred?.("warning");
      renderMyBookingsScreen();
      return;
    }
    tg?.showAlert?.(data.error || "Не удалось отменить");
    if (btn) btn.disabled = false;
  } catch {
    tg?.showAlert?.("Ошибка сети");
    if (btn) btn.disabled = false;
  }
}

function getAvailableDates() {
  const cfg = catalog.config;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const max = new Date(today);
  max.setDate(max.getDate() + cfg.daysAhead);
  return { today, max, closed: new Set(cfg.closedWeekdays) };
}

function isDateAvailable(d, today, max, closed) {
  if (d < today || d > max) return false;
  const wd = (d.getDay() + 6) % 7;
  return !closed.has(wd);
}

function generateTimeSlots(isoDate) {
  const cfg = catalog.config;
  const slots = [];
  const now = new Date();
  const isToday = isoDate === toIsoDate(now);

  for (let h = cfg.workStart; h < cfg.workEnd; h++) {
    for (let m = 0; m < 60; m += cfg.slotMinutes) {
      const label = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
      if (isToday) {
        const slotDate = new Date(`${isoDate}T${label}:00`);
        if (slotDate <= now) continue;
      }
      slots.push(label);
    }
  }
  return slots;
}

async function fetchBookedTimes(isoDate) {
  try {
    const res = await fetch(`/api/slots/${isoDate}`);
    const data = await res.json();
    bookedTimes = data.booked || [];
  } catch {
    bookedTimes = [];
  }
}

function renderDateScreen() {
  if (activeTab !== "book") return;
  updateProgress(0);
  setTabsVisible(true);
  hideMainButton();

  const { today, max, closed } = getAvailableDates();
  const firstDay = new Date(calYear, calMonth, 1);
  const lastDay = new Date(calYear, calMonth + 1, 0);
  let startPad = (firstDay.getDay() + 6) % 7;

  let html = `
    <div class="screen-title">Дата</div>
    <div class="calendar-nav">
      <button type="button" id="prevMonth">◀</button>
      <span>${MONTHS[calMonth]} ${calYear}</span>
      <button type="button" id="nextMonth">▶</button>
    </div>
    <div class="calendar-grid">
      ${WEEKDAYS.map((d) => `<div class="cal-head">${d}</div>`).join("")}
  `;

  for (let i = 0; i < startPad; i++) {
    html += `<button class="cal-day empty"></button>`;
  }

  for (let day = 1; day <= lastDay.getDate(); day++) {
    const d = new Date(calYear, calMonth, day);
    const iso = toIsoDate(d);
    const avail = isDateAvailable(d, today, max, closed);
    const cls = avail ? "available" : "empty";
    const selected = booking.date === iso ? " selected" : "";
    html += `<button class="cal-day ${cls}${selected}" data-date="${avail ? iso : ""}">${day}</button>`;
  }

  html += `</div>`;
  setScreenHtml(html);

  document.getElementById("prevMonth").onclick = () => {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    renderDateScreen();
  };
  document.getElementById("nextMonth").onclick = () => {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    renderDateScreen();
  };

  screen.querySelectorAll(".cal-day.available").forEach((btn) => {
    btn.onclick = async () => {
      booking.date = btn.dataset.date;
      await renderTimeScreen();
    };
  });
}

async function renderTimeScreen() {
  updateProgress(1);
  hideMainButton();
  await fetchBookedTimes(booking.date);

  const slots = generateTimeSlots(booking.date);
  const html = `
    <button class="back-btn" id="backBtn">Назад</button>
    <div class="screen-title">Время</div>
    <p class="screen-sub">${formatDateLabel(booking.date)}</p>
    <div class="time-grid">
      ${slots.map((t) => {
        const taken = bookedTimes.includes(t);
        const sel = booking.time === t ? " selected" : "";
        return `<button class="time-slot${taken ? " taken" : ""}${sel}" data-time="${t}">${t}</button>`;
      }).join("")}
    </div>
  `;
  setScreenHtml(html);

  document.getElementById("backBtn").onclick = renderDateScreen;
  screen.querySelectorAll(".time-slot:not(.taken)").forEach((btn) => {
    btn.onclick = () => {
      booking.time = btn.dataset.time;
      renderHairScreen();
    };
  });
}

function renderServiceCards(items, selectedKey) {
  return Object.entries(items).map(([key, item]) => `
    <div class="service-card${selectedKey === key ? " selected" : ""}" data-key="${key}">
      <span class="name">${item.name}</span>
      <span class="price">${formatPrice(item.price)}</span>
    </div>
  `).join("");
}

function renderHairScreen() {
  updateProgress(2);
  hideMainButton();

  setScreenHtml(`
    <button class="back-btn" id="backBtn">Назад</button>
    <div class="screen-title">Стрижка</div>
    <div class="service-list" id="hairList">
      ${renderServiceCards(catalog.haircuts, booking.haircut)}
    </div>
  `);

  document.getElementById("backBtn").onclick = renderTimeScreen;
  document.querySelectorAll("#hairList .service-card").forEach((card) => {
    card.onclick = () => {
      booking.haircut = card.dataset.key;
      renderBeardScreen();
    };
  });
}

function renderBeardScreen() {
  updateProgress(3);
  hideMainButton();

  setScreenHtml(`
    <button class="back-btn" id="backBtn">Назад</button>
    <div class="screen-title">Борода</div>
    <div class="service-list" id="beardList">
      ${renderServiceCards(catalog.beards, booking.beard)}
    </div>
  `);

  document.getElementById("backBtn").onclick = renderHairScreen;
  document.querySelectorAll("#beardList .service-card").forEach((card) => {
    card.onclick = () => {
      booking.beard = card.dataset.key;
      renderConfirmScreen();
    };
  });
}

function renderConfirmScreen() {
  updateProgress(4);
  setTabsVisible(false);
  const hair = catalog.haircuts[booking.haircut];
  const beard = catalog.beards[booking.beard];
  const total = hair.price + beard.price;
  const prepay = calcPrepayment(total);
  const rest = total - prepay;
  const cfg = catalog.config;

  setScreenHtml(`
    <button class="back-btn" id="backBtn">Назад</button>
    <div class="screen-title">Итого</div>
    <div class="summary">
      <div class="summary-row"><span>Дата</span><span>${formatDateLabel(booking.date)}</span></div>
      <div class="summary-row"><span>Время</span><span>${booking.time}</span></div>
      <div class="summary-row"><span>Стрижка</span><span>${hair.name}</span></div>
      <div class="summary-row"><span>Борода</span><span>${beard.name}</span></div>
      <div class="summary-total">
        <span>Сумма</span>
        <span>${formatPrice(total)}</span>
      </div>
    </div>
    <div class="prepay-box">
      Предоплата: <strong>${formatPrice(prepay)}</strong><br>
      Остаток в салоне: ${formatPrice(rest)}<br><br>
      После записи переведи на <strong>${cfg.prepayPhone || "+79000000000"}</strong><br>
      Код для комментария пришлём ниже.
    </div>
    <button type="button" class="confirm-btn" id="confirmBtn">Записаться</button>
  `);

  document.getElementById("backBtn").onclick = renderBeardScreen;
  document.getElementById("confirmBtn").onclick = submitBooking;
  hideMainButton();
}

async function init() {
  const params = new URLSearchParams(window.location.search);
  const demo = params.get("demo");

  tabsEl?.querySelectorAll(".tab").forEach((btn) => {
    btn.onclick = () => setActiveTab(btn.dataset.tab);
  });

  screen.innerHTML = `<div class="loading">Загрузка...</div>`;
  try {
    await loadCatalog();
    if (demo) {
      document.body.classList.add("demo-mode");
      runDemoScreen(demo);
      return;
    }
    const startTab = params.get("tab") === "bookings" ? "bookings" : "book";
    setActiveTab(startTab);
  } catch {
    screen.innerHTML = `<div class="error-msg">Не загрузилось. Закрой и открой снова.</div>`;
  }
}

function buildDemoPendingMessage() {
  const hair = catalog.haircuts.undercut;
  const beard = catalog.beards.razor;
  const total = hair.price + beard.price;
  const prepay = calcPrepayment(total);
  const rest = total - prepay;
  const dateLabel = formatDateLabel("2026-06-25");
  const phone = catalog.config?.prepayPhone || "+79991234567";
  return (
    `Ждём оплату\n\n${dateLabel}, 16:30\n${hair.name}, ${beard.name}\n` +
    `Сумма: ${formatPrice(total)}\n\nПереведи ${formatPrice(prepay)} на ${phone}\n` +
    `Комментарий: KRV-E029\n\nВ салоне: ${formatPrice(rest)}`
  );
}

function renderDemoConfirmed() {
  stopStatusPoll();
  setProgressVisible(false);
  setTabsVisible(true);
  const hair = catalog.haircuts.undercut;
  const beard = catalog.beards.razor;
  const total = hair.price + beard.price;
  const prepay = calcPrepayment(total);
  const rest = total - prepay;
  const bookingData = {
    date_label: formatDateLabel("2026-06-25"),
    time: "16:30",
    haircut: hair.name,
    beard: beard.name,
    total,
    prepayment: prepay,
    rest,
  };

  setScreenHtml(`
    <div class="success-screen confirmed-state">
      <div class="confirm-check"><span class="confirm-check-mark">✓</span></div>
      <div class="success-title confirmed-title">Запись подтверждена</div>
      <div class="success-text confirmed-card" id="successMsg"></div>
    </div>
  `);
  const msgEl = document.getElementById("successMsg");
  if (msgEl) msgEl.textContent = formatConfirmedMessage(bookingData);
}

function runDemoScreen(name) {
  activeTab = "book";
  calYear = 2026;
  calMonth = 5;
  booking.date = "2026-06-25";
  booking.time = "16:30";
  booking.haircut = "undercut";
  booking.beard = "razor";

  switch (name) {
    case "calendar":
      setActiveTab("book");
      renderDateScreen();
      break;
    case "summary":
      renderConfirmScreen();
      break;
    case "payment":
      renderPendingScreen(buildDemoPendingMessage(), "KRV-E029", null);
      break;
    case "confirmed":
      renderDemoConfirmed();
      break;
    case "bookings":
      renderDemoBookings();
      break;
    default:
      renderDateScreen();
  }
}

function renderDemoBookings() {
  hideMainButton();
  setTabsVisible(true);
  setProgressVisible(false);
  activeTab = "bookings";
  tabsEl?.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === "bookings");
  });

  const items = [
    {
      status: "confirmed",
      date_label: formatDateLabel("2026-06-25"),
      time: "16:30",
      haircut: catalog.haircuts.undercut.name,
      beard: catalog.beards.razor.name,
      total: 2000,
      prepayment: 1000,
    },
    {
      status: "pending",
      date_label: formatDateLabel("2026-06-28"),
      time: "12:00",
      haircut: catalog.haircuts.fade.name,
      beard: catalog.beards.contour.name,
      total: 1500,
      prepayment: 750,
      payment_code: "KRV-E029",
    },
  ];

  screen.innerHTML = `
    <div class="screen-title">Мои записи</div>
    <div class="bookings-list">
      ${items.map((b) => {
        const status = b.status === "confirmed" ? "подтверждена" : "ждёт оплату";
        const codeLine = b.status === "pending" && b.payment_code
          ? `<div class="booking-code">Код: ${b.payment_code}</div>`
          : "";
        const cancelBtn = b.status === "pending"
          ? `<button type="button" class="cancel-booking-btn">Отменить</button>`
          : "";
        return `
        <div class="booking-card ${b.status}">
          <div class="booking-status">${status}</div>
          <div class="booking-date">${b.date_label}, ${b.time}</div>
          <div class="booking-meta">${b.haircut}, ${b.beard}</div>
          <div class="booking-meta">${formatPrice(b.total)} · предоплата ${formatPrice(b.prepayment)}</div>
          ${codeLine}
          ${cancelBtn}
        </div>`;
      }).join("")}
    </div>
  `;
}

init();
