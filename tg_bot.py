from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from auth_data import bot_token, group_chat_id
from db import Database
import logging
import messages as msg
import markups
from aiogram.dispatcher.filters import BoundFilter, Filter
from aiogram.dispatcher.filters.state import StatesGroup, State

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=bot_token)
dp = Dispatcher(bot)
db = Database("database.db")
db.initialize_database()


class PrivateChatOnly(Filter):
    async def check(self, message: types.Message) -> bool:
        # Возвращает True, если тип чата - private (личный чат)
        return message.chat.type == "private"


class ChatIdFilter(BoundFilter):
    key = 'chat_id'

    def __init__(self, chat_id):
        if isinstance(chat_id, int):
            self.chat_id = [chat_id]
        else:
            self.chat_id = chat_id

    def check(self, message: types.Message):
        return message.chat.id in self.chat_id


class BulkSendConfirmation(StatesGroup):
    confirm = State()


dp.filters_factory.bind(ChatIdFilter)
dp.filters_factory.bind(PrivateChatOnly)


@dp.message_handler(lambda message: message.text.startswith("@"), chat_id=group_chat_id)
async def handle_user_info_request(message: types.Message):
    username = message.text.strip("@")
    user_data = db.get_user_by_username(username)
    if user_data:
        user_info_msg = db.get_user_info_for_group_chat(user_data['user_id'])

        # Разбиваем сообщение на части, если оно слишком длинное
        for i in range(0, len(user_info_msg), 4096):
            chunk = user_info_msg[i:i + 4096]
            await bot.send_message(group_chat_id, chunk)
    else:
        await bot.send_message(group_chat_id, f"Пользователь с никнеймом @{username} не найден.")


@dp.message_handler(PrivateChatOnly(), commands=['start'])
async def start(message: types.Message):
    user_id = db.generate_unique_user_id('telegram', message.from_user.id)
    is_user_exists = db.get_row_as_dict({'user_id': user_id}, ['users'])

    user_data = db.create_and_update_user(message, 'telegram')
    if not is_user_exists:
        await bot.send_message(group_chat_id, f"У нас новый пользователь!\n@{message.from_user.username}")
    if user_data.get('start_message_id'):
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=user_data['start_message_id'])
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")
    start_message = await message.answer(msg.start_message(user_data),
                                         reply_markup=markups.generate_keyboard(user_data["progress"]))
    db.update_table("users", {"start_message_id": start_message.message_id}, {"user_id": user_data["user_id"]})


@dp.message_handler(PrivateChatOnly())
async def handle_message(message: types.Message):
    user_id = db.generate_unique_user_id('telegram', message.from_user.id)
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])
    if user_data.get('progress') in (0, 4, 5):
        answer = message.text
        db.record_answer(user_data, answer)

        if user_data.get('progress') == 0:
            start_message = await message.answer(text=msg.question_pending_msg)
        else:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=user_data['start_message_id'],
                    reply_markup=None  # Удаляем клавиатуру
                )
            except Exception as e:
                logging.error(f"Ошибка при удалении клавиатуры из сообщения: {e}")
            next_question = db.get_next_question(user_data['progress'], answer)
            if next_question and next_question.get('question_id'):
                db.update_user_progress(user_id, next_question['question_id'])
                start_message = await message.answer(
                    text=next_question['question_text'],
                    reply_markup=markups.generate_keyboard(next_question['question_id'])
                )
            else:
                db.update_user_progress(user_id, 0)
                start_message = await message.answer(
                    text=msg.final_message(user_data),
                    reply_markup=None)
                await bot.send_message(group_chat_id, db.get_user_info_for_group_chat(user_id))
    else:
        if user_data.get('start_message_id'):
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=user_data['start_message_id'])
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")
        start_message = await message.answer(
            text=msg.unexpected_input_message,
            reply_markup=markups.consultation_keyboard
        )

    db.update_table("users", {"start_message_id": start_message.message_id}, {"user_id": user_data["user_id"]})


@dp.callback_query_handler(lambda c: c.data in ["yes", "no", "russia"])
async def handle_answer(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)
    answer = callback_query.data
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])

    db.record_answer(user_data, answer)

    next_question = db.get_next_question(user_data['progress'], answer)

    if next_question and next_question.get('question_id'):
        db.update_user_progress(user_id, next_question['question_id'])
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=next_question['question_text'],
            reply_markup=markups.generate_keyboard(next_question['question_id'])
        )
    else:
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=msg.final_message(user_data)
        )
        await bot.send_message(group_chat_id, db.get_user_info_for_group_chat(user_id))


@dp.callback_query_handler(lambda c: c.data == "other")
async def handle_other(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=msg.your_option,
        reply_markup=markups.false_go_back_keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "back_to_survey")
async def handle_back_to_survey(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])

    current_question_id = user_data['progress']
    current_question = db.get_row_as_dict({'question_id': current_question_id}, 'questions')

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=current_question['question_text'],
        reply_markup=markups.generate_keyboard(current_question_id)
    )


@dp.callback_query_handler(lambda c: c.data == "go_to_manager")
async def handle_go_to_manager(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)
    user_data = db.update_user_progress(user_id, 0)

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=msg.final_message(user_data),
        reply_markup=None
    )
    await bot.send_message(group_chat_id, db.get_user_info_for_group_chat(user_id))


@dp.callback_query_handler(lambda c: c.data == "no_go_to_manager")
async def handle_go_to_manager(callback_query: types.CallbackQuery):
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)

    await bot.answer_callback_query(callback_query.id)

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=msg.follow_up_message,
        reply_markup=None
    )
    await bot.send_message(group_chat_id, db.get_user_info_for_group_chat(user_id))


@dp.callback_query_handler(lambda c: c.data == "back")
async def handle_back(callback_query: types.CallbackQuery):
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)

    # Находим последний ответ пользователя
    last_answer = db.get_last_answer(user_id)

    # Возвращаем пользователя на предыдущий вопрос
    if last_answer:
        previous_question_id = last_answer['question_id']
        db.update_user_progress(user_id, previous_question_id)

        previous_question = db.get_row_as_dict({'question_id': previous_question_id}, 'questions')

        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=previous_question['question_text'],
            reply_markup=markups.generate_keyboard(previous_question_id)
        )


async def on_shutdown(*args):  # noqa
    db.close()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=on_shutdown)
