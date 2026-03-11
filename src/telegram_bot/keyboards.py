"""Teclados inline para el bot."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_keyboard(is_admin: bool, notif_active: bool) -> InlineKeyboardMarkup:
    """Teclado principal que aparece con /start."""
    notif_label = "🔕 Notif" if notif_active else "🔔 Notif"

    row1 = [
        InlineKeyboardButton(text="⚡ Precio", callback_data="cb:price"),
        InlineKeyboardButton(text="📅 Hoy", callback_data="cb:today"),
        InlineKeyboardButton(text="📅 Mañana", callback_data="cb:tomorrow"),
    ]
    row2 = []
    if is_admin:
        row2.append(InlineKeyboardButton(text="🔄", callback_data="cb:fetch"))
    row2.append(InlineKeyboardButton(text=notif_label, callback_data="cb:notif"))
    row2.append(InlineKeyboardButton(text="⚙️ Ajustes", callback_data="cb:settings"))

    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def build_settings_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    """Submenú de ajustes."""
    rows: list[list[InlineKeyboardButton]] = []

    if is_admin:
        rows.append([
            InlineKeyboardButton(text="📋 Generar alertas", callback_data="cb:gen_alerts"),
            InlineKeyboardButton(text="👀 Ver alertas", callback_data="cb:show_alerts"),
        ])
        rows.append([
            InlineKeyboardButton(text="🧪 Test alertas", callback_data="cb:test_alerts"),
            InlineKeyboardButton(text="📥 Fetch mañana", callback_data="cb:fetch_tom"),
        ])
        rows.append([
            InlineKeyboardButton(text="🤖 Modelos", callback_data="cb:models"),
            InlineKeyboardButton(text="🔌 Test Ollama", callback_data="cb:testollama"),
        ])

    rows.append([InlineKeyboardButton(text="❓ Ayuda", callback_data="cb:help")])
    rows.append([InlineKeyboardButton(text="⬅️ Volver", callback_data="cb:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)
