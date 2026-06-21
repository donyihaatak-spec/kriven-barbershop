BRAND = "KRIVEN"
SHOP_NAME = "KRIVEN BARBERS"

DIVIDER = ""
DIVIDER_THIN = ""


def header(title: str = "") -> str:
    if title:
        return f"◈ {SHOP_NAME}\n{title}"
    return f"◈ {SHOP_NAME}"


def price_tag(amount: int) -> str:
    if amount == 0:
        return "бесплатно"
    return f"{amount:,}".replace(",", " ") + " ₽"


def welcome() -> str:
    return (
        f"◈ {SHOP_NAME}\n\n"
        "Запись на стрижку и бороду.\n"
        "Предоплата по СБП перед записью.\n"
        "«Мои записи» — вкладка в Mini App."
    )


def pick_date() -> str:
    return "Выбери дату в календаре."


def pick_time(date_label: str) -> str:
    return f"📅 {date_label}\n\nВыбери время:"


def pick_haircut() -> str:
    return "Выбери стрижку:"


def pick_beard() -> str:
    return "Выбери бороду:"


def confirmation(
    date_label: str,
    time_label: str,
    haircut_name: str,
    haircut_price: int,
    beard_name: str,
    beard_price: int,
) -> str:
    total = haircut_price + beard_price
    return (
        f"Проверь запись:\n\n"
        f"📅 {date_label}, {time_label}\n"
        f"✂️ {haircut_name}\n"
        f"🧔 {beard_name}\n"
        f"💰 {price_tag(total)}\n\n"
        "Подтвердить?"
    )


def booking_success(
    date_label: str,
    time_label: str,
    haircut_name: str,
    beard_name: str,
    total: int,
    prepayment: int = 0,
    rest: int = 0,
) -> str:
    lines = [
        "✅ Запись подтверждена",
        "",
        f"📅 {date_label}, {time_label}",
        f"✂️ {haircut_name}",
        f"🧔 {beard_name}",
        f"💰 Итого: {price_tag(total)}",
    ]
    if prepayment:
        lines.append(f"✅ Предоплата: {price_tag(prepayment)}")
        lines.append(f"💵 Остаток в барбершопе: {price_tag(rest)}")
    lines.extend(["", "Ждём тебя в KRIVEN"])
    return "\n".join(lines)


def booking_cancelled() -> str:
    return "Запись отменена. Нажми кнопку, когда будешь готов."


def slot_taken() -> str:
    return "Это время занято. Выбери другой слот."


def price_list() -> str:
    from catalog import BEARD_STYLES, HAIRCUT_STYLES

    lines = [f"◈ {SHOP_NAME} — прайс", ""]
    lines.append("✂️ Стрижки")
    for item in HAIRCUT_STYLES.values():
        lines.append(f"{item['name']} — {price_tag(item['price'])}")
    lines.append("")
    lines.append("🧔 Борода")
    for item in BEARD_STYLES.values():
        lines.append(f"{item['name']} — {price_tag(item['price'])}")
    return "\n".join(lines)
