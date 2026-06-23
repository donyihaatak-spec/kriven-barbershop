# Скрины для галереи Kwork

**Реальные скрины** из Mini App и админки — не AI-мокапы.

| Файл | Экран | URL для пересъёмки |
|------|--------|-------------------|
| `01-calendar.png` | Календарь | `/?demo=calendar` |
| `02-summary.png` | Итого | `/?demo=summary` |
| `03-payment.png` | Ждём оплату | `/?demo=payment` |
| `04-confirmed.png` | Подтверждено | `/?demo=confirmed` |
| `05-admin.png` | Админка | `/admin/demo` |

## Переснять локально

```bash
python -m server  # или python -c "from server import run_server; run_server(8765)"
python scripts/capture_gallery.py
```

Или открой URL в браузере (ширина ~390px) и сделай скрин вручную.

Демо: https://t.me/kriventestbot
