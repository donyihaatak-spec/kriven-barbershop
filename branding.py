BRAND = "KRIVEN"


def shop_name() -> str:
    from settings_store import get_shop_name

    return get_shop_name()

DIVIDER = ""
DIVIDER_THIN = ""


def header(title: str = "") -> str:
    if title:
        return f"◈ {shop_name()}\n{title}"
    return f"◈ {shop_name()}"


def price_tag(amount: int) -> str:
    if amount == 0:
        return "бесплатно"
    return f"{amount:,}".replace(",", " ") + " ₽"


def welcome() -> str:
    return f"{shop_name()}\n\nЗапись онлайн — кнопка ниже."


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


def booking_pending(
    date_label: str,
    time_label: str,
    haircut_name: str,
    beard_name: str,
    total: int,
    prepayment: int,
    rest: int,
    payment_code: str,
    phone: str,
    recipient: str,
) -> str:
    return (
        "Ждём оплату\n\n"
        f"{date_label}, {time_label}\n"
        f"{haircut_name}, {beard_name}\n"
        f"Сумма: {price_tag(total)}\n\n"
        f"Переведи {price_tag(prepayment)} на {phone}\n"
        f"Комментарий: {payment_code}\n\n"
        f"В салоне: {price_tag(rest)}"
    )


def booking_payment_rejected(date_label: str, time_label: str) -> str:
    return (
        "Запись отменена\n\n"
        f"{date_label}, {time_label}"
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
        "Запись подтверждена",
        "",
        f"{date_label}, {time_label}",
        f"{haircut_name}, {beard_name}",
        f"Сумма: {price_tag(total)}",
    ]
    if prepayment:
        lines.append(f"Предоплата: {price_tag(prepayment)}")
        lines.append(f"В салоне: {price_tag(rest)}")
    lines.extend(["", "Ждём в KRIVEN"])
    return "\n".join(lines)


def booking_cancelled() -> str:
    return "Запись отменена. Нажми кнопку, когда будешь готов."


def booking_reminder(
    date_label: str,
    time_label: str,
    haircut_name: str,
    beard_name: str,
) -> str:
    return (
        f"Напоминание · {shop_name()}\n\n"
        f"Завтра: {date_label}, {time_label}\n"
        f"{haircut_name}, {beard_name}\n\n"
        "Ждём тебя."
    )


def user_self_cancel(date_label: str, time_label: str) -> str:
    return f"Ты отменил запись\n\n{date_label}, {time_label}"


def admin_user_cancelled(
    full_name: str,
    username: str | None,
    date_label: str,
    time_label: str,
) -> str:
    return (
        "Клиент отменил запись\n\n"
        f"👤 {full_name} (@{username or '—'})\n"
        f"📅 {date_label}, {time_label}"
    )


def slot_taken() -> str:
    return "Это время занято. Выбери другой слот."


def price_list() -> str:
    from catalog_store import get_beard_styles, get_haircut_styles

    lines = [f"◈ {shop_name()} — прайс", ""]
    lines.append("✂️ Стрижки")
    for item in get_haircut_styles().values():
        lines.append(f"{item['name']} — {price_tag(item['price'])}")
    lines.append("")
    lines.append("🧔 Борода")
    for item in get_beard_styles().values():
        lines.append(f"{item['name']} — {price_tag(item['price'])}")
    return "\n".join(lines)
