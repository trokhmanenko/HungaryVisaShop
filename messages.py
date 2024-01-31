# import markups as m

follow_up_message = "📝 Мы свяжемся с вами в течение суток. " \
                    "Если у вас возникнут дополнительные вопросы, обязательно пишите их здесь."

question_pending_msg = "🕒 Спасибо, Ваш вопрос взят в работу.\n\n" + follow_up_message

your_option = "🖊 Предложите свой вариант"

unexpected_input_message = (
    "🤔 Кажется, я не совсем понял ваше сообщение.\n\n"
    "🆘 Если у вас есть вопросы или вам требуется помощь, "
    "вы можете в любой момент перейти к консультации с нашим специалистом."
)


def start_message(user_data):
    name = user_data['first_name']
    msg = f"<b>👋 Добрый день, {name}!</b>\n\n" \
          "Спасибо за ваше обращение 🙏\n" \
          "Для того, чтобы мы могли точно предоставить информацию о <b>получении ВНЖ в Венгрии 🇭🇺</b>, " \
          "предлагаем ответить на несколько вопросов, которые ускорят коммуникацию!\n\n" \
          "<b>🚀 Приступим?</b>"
    return msg


def final_message(user_data):
    name = user_data['first_name']
    msg = f"🎉 {name}, благодарим за предоставленные ответы!\n\n{follow_up_message}"
    return msg


script_data = {
    1: {
        "text": "<b>🚀 Приступим?</b>",
        "buttons": [["yes"],
                    ["no_go_to_manager"]],
        "actions": {
            "yes": 2,
            "no_go_to_manager": -1,
            "go_to_manager": -1
        }
    },
    2: {
        "text": "<b>🌍 Есть ли у Вас загранпаспорт, до срока окончания действия которого более 2х лет?</b>",
        "buttons": [["yes", "no"],
                    ["go_to_manager"]],
        "question_id": 1,
        "actions": {
            "yes": 3,
            "no": 3,
            "go_to_manager": 0
        }
    },
    3: {
        "text": "<b>🛂 Есть ли у Вас действующая шенгенская виза?</b>",
        "buttons": [["yes", "no"],
                    ["go_back"],
                    ["go_to_manager"]],
        "question_id": 2,
        "actions": {
            "yes": 4,
            "no": 5,
            "go_to_manager": 0,
            "go_back": 2
        }
    },
    4: {
        "text": "<b>⏳ Какой срок окончания вашей визы?</b>\n<i>⌨ Напишите свой вариант ниже.</i>",
        "buttons": [["go_back"],
                    ["go_to_manager"]],
        "question_id": 3,
        "listen": 5,
        "actions": {
            "go_to_manager": 0,
            "go_back": 3
        }
    },
    5: {
        "text": "<b>📍 В какой стране вы сейчас находитесь?</b>",
        "buttons": [["russia", "other"],
                    ["go_back"],
                    ["go_to_manager"]],
        "question_id": 4,

        "actions": {
            "russia": 0,
            "other": 6,
            "go_to_manager": 0,
            "go_back": 4
        }
    },
    6: {
        "text": "<b>📍 В какой стране вы сейчас находитесь?</b>\n<i>⌨ Напишите свой вариант ниже.</i>",
        "buttons": [["go_back"],
                    ["go_to_manager"]],
        "question_id": 4,
        "listen": 0,
        "actions": {
            "go_to_manager": 0,
            "go_back": 5
        }
    },
    0: {
        "text_function": final_message,
        "question_id": 0,
        "listen": -2,
    },
    -1: {
        "text": follow_up_message,
        "listen": -2,
        "question_id": 0,
    },
    -2: {
        "text": question_pending_msg,
        "listen": -2,
        "question_id": 0,
    }
}


def generate_message_text(script_item, user_data=None):
    if "text_function" in script_item:
        # Если текст сообщения должен генерироваться функцией
        return script_item["text_function"](user_data)
    else:
        # Если текст сообщения уже задан
        return script_item["text"]


# ======================GROUP CHAT MESSAGES=================================

send_to_all_question = "Вы хотите отправить это сообщение всем пользователям?"


def bulk_send_report_msg(all_users=None, successful_sends=0, blocked_users=0, success=False):
    if success:
        return f"📬 Рассылка завершена!\n\nВсего пользователей: {len(all_users)}\n" \
               f"Успешно доставлено: {successful_sends}\nЗаблокированные: {blocked_users}"
    else:
        return "❌ Рассылка отменена."
