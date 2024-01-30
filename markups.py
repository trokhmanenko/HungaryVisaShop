from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Text
SEND_TO_ALL_TEXT = "📨 Отправить всем"
CANCEL_TEXT = "🔴 Отмена"
YES_TEXT = "✅ Да"
NO_TEXT = "❌ Нет"
GO_TO_MANAGER = "👩‍💼 Перейти к консультации"
NO_GO_TO_MANAGER = "👩‍💼 Нет, сразу перейти к консультации"
RUSSIA = "🇷🇺 Россия"
OTHER_TEXT = "🌍 Другое..."
BACK_TO_SURVEY_TEXT = "🔙 Вернуться к опросу"
GO_BACK_TEXT = "🔙 Назад"

# Buttons
yes_btn = InlineKeyboardButton(YES_TEXT, callback_data="yes")
no_btn = InlineKeyboardButton(NO_TEXT, callback_data="no")
go_to_manager_btn = InlineKeyboardButton(GO_TO_MANAGER, callback_data="go_to_manager")
no_go_to_manager_btn = InlineKeyboardButton(NO_GO_TO_MANAGER, callback_data="no_go_to_manager")
russia_btn = InlineKeyboardButton(RUSSIA, callback_data="russia")
other_btn = InlineKeyboardButton(OTHER_TEXT, callback_data="other")
back_to_survey_btn = InlineKeyboardButton(BACK_TO_SURVEY_TEXT, callback_data="back_to_survey")
go_back_btn = InlineKeyboardButton(GO_BACK_TEXT, callback_data="back")
false_go_back_btn = InlineKeyboardButton(GO_BACK_TEXT, callback_data="back_to_survey")


QUESTION_KEYBOARDS = {
    1: [[yes_btn],
        [no_go_to_manager_btn]],

    2: [[yes_btn, no_btn],
        [go_to_manager_btn]],

    3: [[yes_btn, no_btn],
        [go_to_manager_btn],
        [go_back_btn]],

    4: [[go_back_btn]],

    5: [[russia_btn, other_btn],
        [go_to_manager_btn],
        [go_back_btn]],

}


def generate_keyboard(question_number):
    keyboard = InlineKeyboardMarkup()
    rows = QUESTION_KEYBOARDS.get(question_number, [])
    for row in rows:
        keyboard.row(*row)
    return keyboard


consultation_keyboard = InlineKeyboardMarkup().row(go_to_manager_btn).row(back_to_survey_btn)
go_back_keyboard = InlineKeyboardMarkup().row(go_back_btn)
false_go_back_keyboard = InlineKeyboardMarkup().row(false_go_back_btn)

# Клавиатура отчета в групповом чате
report_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Отчет Excel", callback_data="get_excel_report"))

# Клавиатура групповой отправки
btn1 = InlineKeyboardButton(SEND_TO_ALL_TEXT, callback_data="send_to_all")
btn2 = InlineKeyboardButton(CANCEL_TEXT, callback_data="do_not_send_to_all")
send_to_all_keyboard = InlineKeyboardMarkup().add(btn1).add(btn2)
