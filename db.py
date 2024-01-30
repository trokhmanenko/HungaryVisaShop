import sqlite3
from datetime import datetime
from typing import List, Union, Dict, Any
from aiogram.types import Message
import logging


class Database:
    TABLE_DEFINITIONS = {
        "users": [
            ("user_id", "TEXT PRIMARY KEY"),
            ("source", "TEXT"),
            ("first_name", "TEXT"),
            ("last_name", "TEXT"),
            ("username", "TEXT"),
            ("registration_date", "TEXT"),
            # ("status", "TEXT"),
            ("progress", "INTEGER DEFAULT 1"),
            ("last_activity", "TEXT"),
            ("is_active", "INTEGER DEFAULT 1"),
            ("start_message_id", "INTEGER")
        ],
        "questions": [
            ("question_id", "INTEGER PRIMARY KEY"),
            ("question_text", "TEXT"),
            ("next_question_yes", "INTEGER"),
            ("next_question_no", "INTEGER"),
            ("next_question_other", "INTEGER")
        ],
        "answers": [
            ("answer_id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            ("user_id", "INTEGER"),
            ("question_id", "INTEGER"),
            ("answer_text", "TEXT"),
            ("answer_date", "TEXT"),
        ]
    }

    QUESTIONS = [
        {"question_id": 1,
         "question_text": "Приступим?",
         "next_question_yes": 2,
         "next_question_no": 0,
         "next_question_other": 0},

        {"question_id": 2,
         "question_text": "Есть ли у Вас загранпаспорт, до срока окончания действия которого более 2х лет?",
         "next_question_yes": 3,
         "next_question_no": 3,
         "next_question_other": 0},

        {"question_id": 3,
         "question_text": "Есть ли у Вас действующая шенгенская виза?",
         "next_question_yes": 4,
         "next_question_no": 5,
         "next_question_other": 0},

        {"question_id": 4,
         "question_text": "Какой срок окончания визы?",
         "next_question_yes": 5,
         "next_question_no": 5,
         "next_question_other": 0},

        {"question_id": 5,
         "question_text": "В какой стране вы сейчас находитесь?",
         "next_question_yes": 0,
         "next_question_no": 0,
         "next_question_other": 0},
    ]

    def __init__(self, db_file: str) -> None:
        self.db_file = db_file
        self.connection = sqlite3.connect(db_file)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def initialize_questions(self):
        self.cursor.execute("DROP TABLE IF EXISTS questions")
        self.create_table("questions", self.TABLE_DEFINITIONS["questions"])

        for question in self.QUESTIONS:
            self.insert_into_table("questions", question)

    def initialize_database(self):
        with self.connection:
            for table_name, table_columns in self.TABLE_DEFINITIONS.items():
                if table_name != "questions":
                    self.create_table(table_name, table_columns)
            self.initialize_questions()
        logging.info("Database initialized successfully.")

    def create_table(self, table_name: str, columns: list):
        columns_with_types = ", ".join([" ".join(column) for column in columns])
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_with_types})")

    def get_row_as_dict(self,
                        conditions: Dict[str, Any],
                        table_names: Union[List[str], str] = None) -> Union[Dict[str, Any], None]:
        data = {}

        if table_names is None:
            table_names = ['users', 'files']

        if isinstance(table_names, str):
            table_names = [table_names]

        for table_name in table_names:
            # Формируем строку для WHERE
            where_str = " AND ".join([f"{col} = ?" for col in conditions.keys()])

            query = f"""
                    SELECT * 
                    FROM {table_name}
                    WHERE {where_str}
                """

            row = self.cursor.execute(query, tuple(conditions.values())).fetchone()

            if row is not None:
                data.update(dict(row))

        return data if data else None

    def insert_into_table(self, table_name: str, values: Dict[str, Any]) -> None:
        with self.connection:
            cursor = self.connection.cursor()

            # Формируем строку для колонок и значения
            columns_str = ", ".join(values.keys())
            values_str = ", ".join(["?" for _ in values])

            # Формируем SQL-запрос
            sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"

            # Выполняем запрос
            cursor.execute(sql, list(values.values()))

    def update_table(self, table_name: str, values: Dict[str, Any],
                     conditions: Dict[str, Any]) -> Union[Dict[str, Any], None]:
        """
        Обновляет значения в указанной таблице и возвращает обновленную строку.

        :param table_name: Имя таблицы для обновления.
        :param values: Словарь с новыми значениями { 'column1': new_value1, 'column2': new_value2, ... }.
        :param conditions: Словарь с условиями для WHERE { 'column1': value1, 'column2': value2, ... }.
        :return: Обновленная строка или None, если строка не найдена.
        """
        with self.connection:
            # Формируем строку для SET
            set_str = ", ".join([f"{col} = ?" for col in values.keys()])

            # Формируем строку для WHERE
            where_str = " AND ".join([f"{col} = ?" for col in conditions.keys()])

            # Формируем SQL-запрос
            sql = f"UPDATE {table_name} SET {set_str} WHERE {where_str}"

            # Выполняем запрос
            self.cursor.execute(sql, list(values.values()) + list(conditions.values()))

        # Получаем и возвращаем обновленную строку
        return self.get_row_as_dict(conditions, table_name)

    def create_and_update_user(self, message: Message, source: str) -> Dict[str, Any]:
        user_id = self.generate_unique_user_id(source, message.from_user.id)
        user_data = self.get_row_as_dict({'user_id': user_id}, ['users'])

        if user_data:
            updated_data = {
                'last_name': user_data['last_name'] or message.from_user.last_name or "Not specified",
                'progress': 1,
                'last_activity': self.get_current_time_formatted()}
            user_data = self.update_table("users", updated_data, {"user_id": user_id})
            return user_data
        else:
            user_data = {
                "user_id": user_id,
                "source": source,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name or "Not specified",
                "username": message.from_user.username,
                "registration_date": self.get_current_time_formatted(),
                "progress": 1,
                "last_activity": self.get_current_time_formatted(),
                "is_active": 1,
                "start_message_id": None
            }

            self.insert_into_table("users", user_data)
        return user_data

    def move_user(self, user_id: str, forward=True) -> Dict[str, Any]:
        user_data = self.get_row_as_dict({'user_id': user_id}, 'users')
        if user_data:
            step = 1 if forward else -1
            user_data['progress'] += step
            self.update_user_progress(user_id, user_data['progress'])
        return user_data

    def update_user_progress(self, user_id: str, new_progress: int) -> Dict:
        return self.update_table("users", {"progress": new_progress}, {"user_id": user_id})

    def update_user_status(self, user_id: str, new_status: str):
        self.update_table("users", {"status": new_status}, {"user_id": user_id})

    def record_answer(self, user_data, answer):
        current_time = self.get_current_time_formatted()
        data = {
            "user_id": user_data["user_id"],
            "question_id": user_data["progress"],
            "answer_text": answer,
            "answer_date": current_time
        }
        self.insert_into_table("answers", data)

        update_data = {"last_activity": current_time}
        conditions = {"user_id": user_data["user_id"]}
        self.update_table("users", update_data, conditions)

    def get_next_question(self, current_question_id, answer):
        current_question = self.get_row_as_dict({'question_id': current_question_id}, 'questions')

        if current_question:
            next_question_id = None
            if answer in ['yes', 'russia'] or current_question_id in (4, 5):
                next_question_id = current_question['next_question_yes']
            elif answer == 'no' and current_question['next_question_no'] is not None:
                next_question_id = current_question['next_question_no']
            elif answer == 'other' and current_question['next_question_other'] is not None:
                next_question_id = current_question['next_question_other']

            if next_question_id is not None:
                return self.get_row_as_dict({'question_id': next_question_id}, 'questions')

        return None

    def get_last_answer(self, user_id: str):
        query = """
            SELECT * FROM answers 
            WHERE user_id = ? 
            ORDER BY answer_date DESC 
            LIMIT 1
        """
        row = self.cursor.execute(query, (user_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_current_time_formatted():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def generate_unique_user_id(source: str, user_id: int) -> str:
        return f"{source}_{user_id}"

    def get_user_by_username(self, username: str):
        query = "SELECT * FROM users WHERE username = ?"
        row = self.cursor.execute(query, (username,)).fetchone()
        return dict(row) if row else None

    def get_user_info_for_group_chat(self, user_id: str):
        # Получение информации о пользователе
        user_data = self.get_row_as_dict({'user_id': user_id}, ['users'])

        if user_data:
            # Формирование сообщения с информацией о пользователе
            user_info_msg = f"Информация о пользователе:\n" \
                            f"Имя: {user_data['first_name']}\n" \
                            f"Фамилия: {user_data['last_name']}\n" \
                            f"Юзернейм: @{user_data['username']}\n" \
                            f"Дата регистрации: {user_data['registration_date']}\n" \
                            f"Дата последней активности: {user_data['last_activity']}\n\n"

            answers = self.get_answers_by_user_id(user_id)
            additional_questions = []
            last_answers = {}

            for answer in answers:
                if answer['question_id'] == 0:
                    additional_questions.append(answer)
                elif answer['question_id'] > 1:
                    last_answers[answer['question_id']] = answer
            # Добавление последних ответов
            if last_answers:
                user_info_msg += "Ответы на вопросы:\n"
                for question_id, answer in last_answers.items():
                    question_text = self.get_question_text(question_id)
                    user_info_msg += f"- {question_text}: {answer['answer_text']}\n"

            # Добавление дополнительных вопросов
            if additional_questions:
                user_info_msg += "Дополнительные вопросы:\n"
                for answer in additional_questions:
                    user_info_msg += f"- {answer['answer_text']}\n"

            return user_info_msg

    def get_answers_by_user_id(self, user_id: str):
        return self.cursor.execute(
            "SELECT * FROM answers WHERE user_id = ?", (user_id,)
        ).fetchall()

    def get_question_text(self, question_id: int):
        question = self.get_row_as_dict({'question_id': question_id}, 'questions')
        return question['question_text'] if question else "Неизвестный вопрос"

    def get_report(self) -> str:
        # Получить количество всех пользователей
        total_users = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        # # Получить количество пользователей по тарифам
        # user_tariffs = self.cursor.execute(
        #     "SELECT t.id, t.name, COUNT(u.user_id) "
        #     "FROM tariffs t "
        #     "LEFT JOIN users u ON t.id = u.tariff_id "
        #     "GROUP BY t.id, t.name "
        #     "ORDER BY t.id"
        # ).fetchall()
        #
        # # Получить количество активных и заблокированных пользователей
        # active_users = self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0]
        # blocked_users = total_users - active_users
        #
        # # Получить сумму балансов всех пользователей
        # total_balance = self.cursor.execute("SELECT SUM(balance) FROM users").fetchone()[0]
        #
        # # Получить сумму всех успешных покупок
        # total_amount = self.cursor.execute(
        #     "SELECT SUM(amount) FROM transactions WHERE status = 'CONFIRMED' AND transaction_type != 'withdrawal'"
        # ).fetchone()[0]
        #
        # # Получить сумму всех успешных выводов
        # total_withdrawn = self.cursor.execute(
        #     "SELECT SUM(amount) FROM transactions WHERE status = 'CONFIRMED' AND transaction_type = 'withdrawal'"
        # ).fetchone()[0]
        #
        # if total_amount is None:
        #     total_amount = 0
        # if total_balance is None:
        #     total_balance = 0
        # if total_withdrawn is None:
        #     total_withdrawn = 0
        #
        # # Вычислить общий профит
        # total_profit = total_amount - total_balance + total_withdrawn
        #
        # report = f"📊 Отчет\n\nВсего пользователей: {total_users}\n\nТарифы:\n"
        # for i, tariff_name, count in user_tariffs:
        #     report += f"{i}. {tariff_name}: {count}\n"
        # report += f"\nАктивных: {active_users}\nЗаблокировано: {blocked_users}"
        # report += f"\n\nНа счетах: {total_balance:.2f}₽"
        # report += f"\nВсего покупок: {total_amount:.2f}₽"
        # report += f"\nВсего выведено: {-total_withdrawn:.2f}₽"
        # report += f"\nОбщий профит: {total_profit:.2f}₽"

        return f"ВСего пользователей: {total_users}"

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed.")
