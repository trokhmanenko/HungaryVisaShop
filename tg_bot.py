from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from auth_data import bot_token, group_chat_id
from db import Database
import logging
import messages as msg
import markups
from aiogram.dispatcher.filters import BoundFilter, Filter
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types.input_file import InputFile
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import BotBlocked

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())
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


@dp.message_handler(lambda message: message.text.strip().lower().replace(" ", "") in ["отчет", "jnxtn"],
                    chat_id=group_chat_id)
async def send_report(message: types.Message):
    report = db.get_report()
    await bot.send_message(group_chat_id,
                           report,
                           reply_to_message_id=message.message_id,
                           reply_markup=markups.report_keyboard)


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


@dp.message_handler(chat_id=group_chat_id)
async def handle_manager_reply(message: types.Message, state: FSMContext):
    # Сохраняем текст сообщения в state
    await state.set_data({"message_text": message.text})

    await bot.send_message(message.chat.id,
                           msg.send_to_all_question,
                           reply_markup=markups.send_to_all_keyboard,
                           reply_to_message_id=message.message_id)
    await BulkSendConfirmation.confirm.set()


@dp.message_handler(PrivateChatOnly(), commands=['start'])
async def start(message: types.Message):
    user_id = db.generate_unique_user_id('telegram', message.from_user.id)
    is_user_exists = db.get_row_as_dict({'user_id': user_id}, ['users'])

    user_data = db.create_and_update_user(message, 'telegram')
    if not is_user_exists:
        await message.answer(msg.start_message(user_data), parse_mode='HTML')
        await bot.send_message(group_chat_id, f"🆕 У нас новый пользователь!🆕\n@{message.from_user.username}")
    if user_data.get('start_message_id'):
        await update_message(message.chat.id, user_data['start_message_id'])

    current_step = user_data['progress']
    current_script_item = msg.script_data.get(current_step)

    start_message = await message.answer(msg.generate_message_text(current_script_item, user_data),
                                         reply_markup=markups.generate_keyboard(user_data["progress"]),
                                         parse_mode='HTML')
    db.update_table("users", {"start_message_id": start_message.message_id}, {"user_id": user_data["user_id"]})


@dp.message_handler(PrivateChatOnly())
async def handle_message(message: types.Message):
    user_id = db.generate_unique_user_id('telegram', message.from_user.id)
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])

    # Получаем текущий шаг пользователя
    current_step = user_data['progress']
    current_script_item = msg.script_data.get(current_step)
    current_message_text = msg.unexpected_input_message
    current_keyboard = markups.consultation_keyboard

    # Проверяем наличие действий
    if current_script_item.get('actions'):
        # Удаление клавиатуры у старого сообщения
        await update_message(message.chat.id, user_data.get('start_message_id'))

    # Проверяем, нужно ли слушать ввод пользователя
    if 'listen' in current_script_item:
        # Запись ввода пользователя
        db.record_answer(user_data, message.text, current_script_item.get('question_id'))

        # Получаем новый шаг
        current_step = current_script_item['listen']
        current_script_item = msg.script_data.get(current_step)
        current_message_text = msg.generate_message_text(current_script_item, user_data)
        current_keyboard = markups.generate_keyboard(current_step)

    # Отправка нового сообщения
    start_message = await message.answer(text=current_message_text,
                                         reply_markup=current_keyboard,
                                         parse_mode='HTML')
    db.update_table("users", {"start_message_id": start_message.message_id,
                              "progress": current_step},
                    {"user_id": user_data["user_id"]})

    if current_step == 0:
        await bot.send_message(group_chat_id, f"🟢 Пользователь завершил опрос!🟢\n@{message.from_user.username}")
    elif current_step == -2:
        await bot.send_message(group_chat_id,
                               f"❓ Пользователь задает вопрос! ❓\n@{message.from_user.username}")


@dp.callback_query_handler(lambda c: c.data in ["yes", "no", "russia", "go_to_manager", "no_go_to_manager"])
async def handle_answer(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])

    # Получаем текущий шаг пользователя
    current_step = user_data['progress']
    current_script_item = msg.script_data.get(current_step)

    if 'question_id' in current_script_item and callback_query.data in ["yes", "no", "russia"]:
        # Запись ответа в базу данных
        db.record_answer(user_data, callback_query.data, current_script_item['question_id'])

    # Обновление прогресса пользователя
    next_step = current_script_item['actions'].get(callback_query.data)
    if next_step is not None:
        db.update_user_progress(user_id, next_step)

    # Обновление предыдущего сообщения с добавлением ответа или удалением клавиатуры
    answer_text = markups.inline_button_texts.get(callback_query.data)
    await update_message(callback_query.message.chat.id,
                         callback_query.message.message_id,
                         msg.generate_message_text(current_script_item, user_data),
                         answer_text)

    # Отправка сообщения следующего шага
    next_script_item = msg.script_data.get(next_step)
    next_message_text = msg.generate_message_text(next_script_item, user_data)
    start_message = await bot.send_message(chat_id=callback_query.message.chat.id,
                                           text=next_message_text,
                                           reply_markup=markups.generate_keyboard(next_step),
                                           parse_mode='HTML')

    db.update_table("users", {"start_message_id": start_message.message_id}, {"user_id": user_data["user_id"]})

    if next_step < 1:
        await bot.send_message(group_chat_id, f"🟢 Пользователь завершил опрос!🟢\n@{callback_query.from_user.username}")


@dp.callback_query_handler(lambda c: c.data == "other")
async def handle_other(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])

    # Получаем текущий шаг пользователя
    current_step = user_data['progress']
    current_script_item = msg.script_data.get(current_step)

    # Обновление прогресса пользователя
    next_step = current_script_item['actions'].get(callback_query.data)
    if next_step is not None:
        db.update_user_progress(user_id, next_step)

    # Обновление сообщения следующего шага
    next_script_item = msg.script_data.get(next_step)
    next_message_text = msg.generate_message_text(next_script_item, user_data)

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=user_data.get('start_message_id'),
        text=next_message_text,
        reply_markup=markups.generate_keyboard(next_step),
        parse_mode='HTML'
    )


@dp.callback_query_handler(lambda c: c.data in ("back_to_survey", "go_back"))
async def handle_back_to_survey(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = db.generate_unique_user_id('telegram', callback_query.from_user.id)
    user_data = db.get_row_as_dict({'user_id': user_id}, ['users'])

    # Получаем текущий шаг пользователя
    current_step = user_data['progress']
    if callback_query.data == "go_back":
        current_step = max(current_step - 1, 0)
        db.update_user_progress(user_id, current_step)

    current_script_item = msg.script_data.get(current_step)
    current_message_text = msg.generate_message_text(current_script_item, user_data)

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=user_data.get('start_message_id'),
        text=current_message_text,
        reply_markup=markups.generate_keyboard(current_step),
        parse_mode='HTML'
    )


@dp.callback_query_handler(text="get_excel_report")
async def on_get_excel_report_clicked(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    excel_report = db.create_excel_report()
    await bot.send_document(group_chat_id, InputFile(*excel_report))


@dp.callback_query_handler(lambda c: c.data == 'send_to_all', state=BulkSendConfirmation.confirm)
async def on_send_to_all_clicked(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    user_data = await state.get_data()
    message_text = user_data.get("message_text", "")
    await state.finish()

    successful_sends = 0
    blocked_users_count = 0

    # Получаем список ID пользователей Telegram
    all_users_id = db.get_all_users_id("telegram")

    for user_id in all_users_id:
        try:
            # Отправка сообщения по числовому ID пользователя
            telegram_user_id = int(user_id.split('_')[1])
            await bot.send_message(telegram_user_id, message_text)
            db.update_table('users', {'is_active': 1}, {'user_id': user_id})
            successful_sends += 1
        except BotBlocked:
            db.update_table('users', {'is_active': 0}, {'user_id': user_id})
            blocked_users_count += 1
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")

    report_msg = msg.bulk_send_report_msg(len(all_users_id), successful_sends, blocked_users_count, success=True)
    await bot.edit_message_text(chat_id=group_chat_id,
                                message_id=callback_query.message.message_id,
                                text=report_msg,
                                reply_markup=None, parse_mode='HTML')


@dp.callback_query_handler(lambda c: c.data == 'do_not_send_to_all', state=BulkSendConfirmation.confirm)
async def process_callback_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await state.finish()
    await bot.edit_message_text(chat_id=group_chat_id,
                                message_id=callback_query.message.message_id,
                                text=msg.bulk_send_report_msg(),
                                reply_markup=None, parse_mode='HTML')


async def update_message(chat_id, message_id, original_text=None, answer_text=None):
    try:
        if original_text and answer_text:
            # Если предоставлен текст ответа, добавляем его к сообщению
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=f"{original_text}\n\n→ {answer_text}",
                                        reply_markup=None, parse_mode='HTML')
        else:
            # Если текст ответа не предоставлен, удаляем только клавиатуру
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Ошибка при обновлении сообщения: {e}")


async def on_shutdown(*args):  # noqa
    db.close()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=on_shutdown)
