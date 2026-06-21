const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor("#050505");
  tg.setBackgroundColor("#050505");
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

const booking = {
  date: null,
  time: null,
  haircut: null,
  beard: null,
};

const screen = document.getElementById("screen");
const progressFill = document.getElementById("progressFill");
const stepLabels = document.querySelectorAll("#stepLabels span");

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

function updateProgress() {
  const pct = ((step + 1) / 5) * 100;
  progressFill.style.width = pct + "%";
  stepLabels.forEach((el, i) => el.classList.toggle("active", i === step));
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
        renderSuccessScreen(result.message);
        setTimeout(() => tg?.close?.(), 2500);
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

    tg?.showAlert?.("Открой Mini App через кнопку в боте");
    if (btn) btn.disabled = false;
    tg?.MainButton?.hideProgress?.();
  } catch {
    tg?.showAlert?.("Ошибка сети. Проверь интернет и попробуй снова.");
    if (btn) btn.disabled = false;
    tg?.MainButton?.hideProgress?.();
  }
}

function renderSuccessScreen(message) {
  step = 4;
  updateProgress();
  screen.innerHTML = `
    <div class="success-screen">
      <div class="success-icon">◈</div>
      <div class="success-title">Готово!</div>
      <div class="success-text" id="successMsg"></div>
    </div>
  `;
  const msgEl = document.getElementById("successMsg");
  if (msgEl) {
    msgEl.style.whiteSpace = "pre-line";
    msgEl.textContent = message;
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
  step = 0;
  updateProgress();
  hideMainButton();

  const { today, max, closed } = getAvailableDates();
  const firstDay = new Date(calYear, calMonth, 1);
  const lastDay = new Date(calYear, calMonth + 1, 0);
  let startPad = (firstDay.getDay() + 6) % 7;

  let html = `
    <div class="screen-title">Выбери дату</div>
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
  screen.innerHTML = html;

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
  step = 1;
  updateProgress();
  hideMainButton();
  await fetchBookedTimes(booking.date);

  const slots = generateTimeSlots(booking.date);
  const html = `
    <button class="back-btn" id="backBtn">◀ Назад</button>
    <div class="screen-title">Выбери время</div>
    <p style="color:var(--chrome-dim);font-size:0.85rem;margin-bottom:16px">${formatDateLabel(booking.date)}</p>
    <div class="time-grid">
      ${slots.map((t) => {
        const taken = bookedTimes.includes(t);
        const sel = booking.time === t ? " selected" : "";
        return `<button class="time-slot${taken ? " taken" : ""}${sel}" data-time="${t}">${t}</button>`;
      }).join("")}
    </div>
  `;
  screen.innerHTML = html;

  document.getElementById("backBtn").onclick = renderDateScreen;
  screen.querySelectorAll(".time-slot:not(.taken)").forEach((btn) => {
    btn.onclick = () => {
      booking.time = btn.dataset.time;
      renderHairScreen();
    };
  });
}

function renderServiceCards(items, selectedKey, onSelect) {
  return Object.entries(items).map(([key, item]) => `
    <div class="service-card${selectedKey === key ? " selected" : ""}" data-key="${key}">
      <div class="left">
        <span class="emoji">${item.emoji}</span>
        <span class="name">${item.name}</span>
      </div>
      <span class="price">${formatPrice(item.price)}</span>
    </div>
  `).join("");
}

function renderHairScreen() {
  step = 2;
  updateProgress();
  hideMainButton();

  screen.innerHTML = `
    <button class="back-btn" id="backBtn">◀ Назад</button>
    <div class="screen-title">Вид стрижки</div>
    <div class="service-list" id="hairList">
      ${renderServiceCards(catalog.haircuts, booking.haircut)}
    </div>
  `;

  document.getElementById("backBtn").onclick = renderTimeScreen;
  document.querySelectorAll("#hairList .service-card").forEach((card) => {
    card.onclick = () => {
      booking.haircut = card.dataset.key;
      renderBeardScreen();
    };
  });
}

function renderBeardScreen() {
  step = 3;
  updateProgress();
  hideMainButton();

  screen.innerHTML = `
    <button class="back-btn" id="backBtn">◀ Назад</button>
    <div class="screen-title">Вид бороды</div>
    <div class="service-list" id="beardList">
      ${renderServiceCards(catalog.beards, booking.beard)}
    </div>
  `;

  document.getElementById("backBtn").onclick = renderHairScreen;
  document.querySelectorAll("#beardList .service-card").forEach((card) => {
    card.onclick = () => {
      booking.beard = card.dataset.key;
      renderConfirmScreen();
    };
  });
}

function renderConfirmScreen() {
  step = 4;
  updateProgress();

  const hair = catalog.haircuts[booking.haircut];
  const beard = catalog.beards[booking.beard];
  const total = hair.price + beard.price;

  screen.innerHTML = `
    <button class="back-btn" id="backBtn">◀ Назад</button>
    <div class="screen-title">Подтверждение</div>
    <div class="summary">
      <div class="summary-row"><span>Дата</span><span>${formatDateLabel(booking.date)}</span></div>
      <div class="summary-row"><span>Время</span><span>${booking.time}</span></div>
      <div class="summary-row"><span>Стрижка</span><span>${hair.name}</span></div>
      <div class="summary-row"><span>Борода</span><span>${beard.name}</span></div>
      <div class="summary-total">
        <span class="label">Итого</span>
        <span class="amount">${formatPrice(total)}</span>
      </div>
    </div>
    <button type="button" class="confirm-btn" id="confirmBtn">Записаться</button>
  `;

  document.getElementById("backBtn").onclick = renderBeardScreen;
  document.getElementById("confirmBtn").onclick = submitBooking;
  hideMainButton();
}

async function init() {
  screen.innerHTML = `<div class="loading">Загрузка KRIVEN...</div>`;
  try {
    await loadCatalog();
    renderDateScreen();
  } catch (e) {
    screen.innerHTML = `<div class="error-msg">Ошибка загрузки. Перезапусти Mini App.</div>`;
  }
}

init();
