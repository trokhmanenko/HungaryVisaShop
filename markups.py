from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import messages as msg

# Text
inline_button_texts = {
    "get_excel_report": "📊 Отчет Excel",
    "send_to_all": "📨 Отправить всем",
    "do_not_send_to_all": "🔴 Отмена",
    "yes": "✅ Да",
    "no": "❌ Нет",
    "go_to_manager": "👩‍💼 Перейти к консультации",
    "no_go_to_manager": "👩‍💼 Нет, сразу перейти к консультации",
    "russia": "🇷🇺 Россия",
    "other": "🌍 Другое...",
    "back_to_survey": "🔙 Вернуться к опросу",
    "go_back": "🔙 Назад"
}

# Buttons
inline_btns = {callback_data: InlineKeyboardButton(text, callback_data=callback_data)
               for callback_data, text in inline_button_texts.items()}


def generate_keyboard(msg_number):
    keyboard = InlineKeyboardMarkup()
    if msg_number in msg.script_data:
        buttons_info = msg.script_data[msg_number].get("buttons", [])
        for btn_row in buttons_info:
            row = [inline_btns[btn] for btn in btn_row if btn in inline_btns]
            keyboard.row(*row)
    return keyboard


consultation_keyboard = InlineKeyboardMarkup().row(inline_btns["go_to_manager"]).row(inline_btns["back_to_survey"])

# Клавиатура отчета в групповом чате
report_keyboard = InlineKeyboardMarkup().add(inline_btns["get_excel_report"])

# Клавиатура групповой отправки
send_to_all_keyboard = InlineKeyboardMarkup().add(inline_btns["send_to_all"]).add(inline_btns["do_not_send_to_all"])
