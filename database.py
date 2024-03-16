import logging
import sqlite3


def create_db():
    connection = sqlite3.connect("sqlite3.db")
    connection.close()
    logging.info("База данных успешно создана")


def process_query(query, params):
    connection = sqlite3.connect("sqlite3.db")
    connection.row_factory = sqlite3.Row
    cur = connection.cursor()
    if not params:
        if 'SELECT' in query:
            result = cur.execute(query)
            return result
        cur.execute(query)
    else:
        if 'SELECT' in query:
            result = cur.execute(query, tuple(params))
            return list(result)
        cur.execute(query, tuple(params))
    connection.commit()
    connection.close()


def create_users_table():
    query = '''
    CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,
    subject TEXT DEFAULT "Астрономия",
    level TEXT DEFAULT "Новичок",
    task TEXT DEFAULT "", 
    answer TEXT DEFAULT "",
    number_of_tasks INTEGER DEFAULT 0, 
    processing_answer INTEGER DEFAULT 0,
    settings_msg_id INTEGER DEFAULT -1);'''
    process_query(query, None)


def add_user_to_database(user_id):
    query = '''INSERT INTO users (user_id) VALUES (?);'''
    process_query(query, [user_id])
    logging.info(f"Пользователь с user_id = {user_id} успешно добавлен в базу данных")


def find_user_data(user_id):
    query = '''SELECT * FROM users WHERE user_id = ?;'''
    result = process_query(query, [user_id])
    if result:
        logging.info(f"Данные пользователя с user_id {user_id} успешно найдены.")
        return result[0]
    logging.error("Не получилось собрать данные пользователя.")
    return result


def update_user_data(user_id, column_name, value):
    query = f'''UPDATE users SET {column_name} = ? WHERE user_id = ?;'''
    process_query(query, [value, user_id])
    logging.info(f"база данных успешно обновлена, колонка: {column_name}, user_id - {user_id}")


def count_subjects_popularity():
    query = f"SELECT subject, COUNT(*) FROM users GROUP BY subject; "
    counter = process_query(query, None)
    if counter:
        logging.info("Данные об использовании предметов успешно собраны")
        return dict(counter)
    logging.error("Не получилось собрать данные об использовании предметов.")


def find_latest_issues():
    query = f"SELECT task FROM users ORDER BY id DESC LIMIT 3"
    tasks_rows_list = list(process_query(query, None))
    tasks_list = []
    if tasks_rows_list:
        for task in tasks_rows_list:
            tasks_list.append(task["task"])
        logging.info("Последние записи успешно найдены")
    else:
        logging.error("Не удалось найти последние записи, так как их еще нет.")
    return tasks_list


def delete_user(user_id):
    query = f"DELETE FROM users WHERE user_id = ?"
    process_query(query, [user_id])
    logging.info(f"Пользователь с user_id = {user_id} успешно удален из базы данных")