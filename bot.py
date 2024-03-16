import time
import telebot
from telebot.types import ReplyKeyboardMarkup, BotCommand, BotCommandScope, InlineKeyboardMarkup, InlineKeyboardButton
from gpt import GPT
import logging
from database import (create_db, create_users_table, add_user_to_database, find_user_data, update_user_data,
                      count_subjects_popularity, find_latest_issues)
from settings import get_settings
from config import TOKEN, ADMIN

create_db()
create_users_table()

admin_id = int(ADMIN)

bot = telebot.TeleBot(token=TOKEN)

gpt = GPT()
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H",
    filename="log_file.txt",
    filemode="w",
    force=True
)


@bot.message_handler(commands=['debug'])
def send_logs(message):
    user_id = message.chat.id

    if user_id == admin_id:
        try:

            with open("log_file.txt", "rb") as f:
                bot.send_document(message.chat.id, f)

        except telebot.apihelper.ApiTelegramException:

            bot.send_message(message.chat.id, "Логов пока нет.")

    else:
        bot.send_message(message.chat.id, "У Вас недостаточно прав для использования этой команды.")


def check_user(user_id):
    if not find_user_data(user_id):
        add_user_to_database(user_id)
        logging.info("Пользователь успешно добавлен в базу данных")


def check_processing_answer(user_id, message):
    if find_user_data(user_id)['processing_answer'] == 1:
        logging.debug("попытка задать еще один вопрос, когда нейросеть уже генерирует другой")

        bot.reply_to(message, "Нейросеть уже отвечает на Ваш вопрос. Прежде чем задать следующий,"
                              " дождитесь ответа на предыдущий.")
        return True
    return False


# клавиатуры
main_menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add("Запуск GPT", "⚙️Параметры", "📊Статистика")


def make_reply_keyboard(btns: list):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for btn in btns:
        keyboard.add(btn)
    return keyboard


def make_inline_keyboard(data, user_id: None | int):
    keyboard = InlineKeyboardMarkup(row_width=1)

    back_btn = InlineKeyboardButton(text="Вернуться назад", callback_data="go_back")

    if data in ['settings', 'go_back']:
        btn1 = InlineKeyboardButton(text="Предмет", callback_data="subject")
        btn2 = InlineKeyboardButton(text="Уровень объяснения", callback_data="level")
        keyboard.add(btn1, btn2)

    if data in ["subject", "level", "Астрономия", "География", "Новичок", "Профи"]:
        user_data = find_user_data(user_id)

        if data in ['subject', "Астрономия", "География"]:

            current_subject = user_data["subject"]

            btn1_text = "💫Астрономия"
            btn2_text = "🗺️География"

            if current_subject == "Астрономия":
                btn1_text += " ✅"

            elif current_subject == "География":
                btn2_text += " ✅"

            btn1 = InlineKeyboardButton(text=btn1_text, callback_data="Астрономия")
            btn2 = InlineKeyboardButton(text=btn2_text, callback_data="География")

            keyboard.add(btn1, btn2, back_btn)

        elif data in ['level', "Новичок", "Профи"]:

            current_level = user_data["level"]

            btn1_text = "Новичок"
            btn2_text = "Профи"

            if current_level == "Новичок":
                btn1_text += " ✅"

            elif current_level == "Профи":
                btn2_text += " ✅"

            btn1 = InlineKeyboardButton(text=btn1_text, callback_data="Новичок")
            btn2 = InlineKeyboardButton(text=btn2_text, callback_data="Профи")

            keyboard.add(btn1, btn2, back_btn)
    return keyboard


# функция старт
@bot.message_handler(commands=["start"])
def start_bot(message):
    logging.info("Бот запущен")

    commands = [  # Установка списка команд
        BotCommand('start', 'перезапустить бота'),
        BotCommand('help', 'узнайте о доступных командах'),
        BotCommand('settings', 'изменить конфигурацию для нейросети'),
        BotCommand('talk', 'начать диалог с нейросетью'),
        BotCommand('exit', 'завершить диалог с нейросетью'),
        BotCommand('stats', 'показать статистику использования бота')
    ]

    bot.set_my_commands(commands)
    BotCommandScope('private', chat_id=message.chat.id)
    user_id = message.from_user.id  # создание пользователя

    check_user(user_id)  # данная проверка есть в каждой функции, на случай, чтобы не возникла ошибка, если бд удалена.

    # эта проверка также есть везде, чтобы блокировать команды во время выполнения запроса
    if check_processing_answer(user_id, message):
        return

    #  приветствие
    bot.send_message(message.chat.id, 'Привет! Я бот-помощник с нейросетью. '
                                      'ты можешь задать мне вопросы по астрономии и географии. '
                                      'Также я могу отвечать Вам в'
                                      'зависимости от вашего уровня знаний.\n\n'
                                      'Чтобы я смог лучше ответить на ваш вопрос,'
                                      ' пожалуйста, нажмите на кнопку "параметры" и сделайте выбор.\n\n'
                                      'Вы можете не делать этого, тогда будут выставлены значения по умолчанию:\n'
                                      'Предмет: Астрономия\n'
                                      'Уровень знаний: Начинающий', reply_markup=main_menu_keyboard)


# функции
@bot.message_handler(commands=["help"])
def tell_about_bot(message):
    text = ("Привет! Тут Вы найдете основную информацию о моих функциях.\n\n"
            "/start - проснуться заново, забыв всю свою прошлую жизнь! Только для бота...\n\n"
            "/help - поможет Вам узнать основную информацию о моих функциях\n\n"
            '/settings или кнопка "Параметры" - позволит вам изменить параметры, с помощью которых нейросеть лучше '
            'поймет, как вам ответить.\n\n'
            '/talk или кнопка "Запуск GPT" - позволяет мне выступить посредником между Вами и нейросетью, а Вам - '
            'получить от нее ответ на Ваш вопрос.\n\n'
            'После того, как нейросеть ответит на Ваш вопрос, Вы сможете попросить ее продолжить свой ответ, нажав на'
            ' кнопку "Продолжи!"\n\n'
            '/exit или кнопка "Выход" - позволит Вам закончить диалог с нейросетью.\n\n'
            '/stats или кнопка "Статистика" - покажет статистику использования бота.')

    user_id = message.from_user.id

    if check_processing_answer(user_id, message):
        return

    bot.reply_to(message, text=text)

    logging.info("сообщение с инструкцией по использованию бота успешно отправлено")


@bot.message_handler(commands=['settings'])
@bot.message_handler(content_types=['text'], func=lambda message: message.text.lower() == "⚙️параметры")
def settings(message):
    c_id = message.chat.id

    user_id = message.from_user.id
    check_user(user_id)

    if check_processing_answer(user_id, message):
        return
    previous_msg = find_user_data(user_id)['settings_msg_id']

    if message.text.lower() == "вернуться в главное меню":
        bot.send_message(c_id, 'Теперь можете начать диалог с нейросетью, нажав на кнопку "Запуск GPT"',
                         reply_markup=main_menu_keyboard)

        for i in range(0, 3):  # удаляем предыдущие сообщения, связанные с параметрами во избежание ошибок
            m_id = previous_msg - i
            bot.delete_message(chat_id=c_id, message_id=m_id)
            update_user_data(user_id, "settings_msg_id", -1)

        return

    if message.text.lower() in ["⚙️параметры", "/settings", "параметры"]:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add("Вернуться в главное меню")  # меняем reply клавиатуру

        bot.send_message(c_id, "Перехожу в режим настроек...", reply_markup=keyboard)
        time.sleep(0.5)

        keyboard = make_inline_keyboard('settings', None)  # меняем inline клавиатуру

        msg = bot.send_message(chat_id=c_id, text="Какой параметр вы хотите изменить?", reply_markup=keyboard)

        if previous_msg != -1:  # удаляем предыдущие сообщения, связанные с параметрами во избежание ошибок
            for i in range(0, 3):
                m_id = previous_msg - i
                bot.delete_message(chat_id=c_id, message_id=m_id)

        update_user_data(user_id, "settings_msg_id", msg.message_id)

    else:
        bot.delete_message(chat_id=c_id, message_id=message.message_id)

    bot.register_next_step_handler(message, settings)


# на случай, если бот был перезапущен во время исполнения запроса к нейросети
@bot.message_handler(commands=["delete_process_resp"])
def delete_process_resp(message):
    user_id = message.from_user.id
    if user_id == admin_id:
        update_user_data(user_id, 'processing_answer', 0)
        bot.send_message(message.chat.id, "Ошибка успешно исправлена.")
    else:
        bot.send_message(message.chat.id, "Доступ запрещен.")


@bot.message_handler(commands=["stats"])
@bot.message_handler(content_types=['text'], func=lambda message: message.text.lower() == "📊статистика")
def show_statistics(message):
    user_id = message.from_user.id

    check_user(user_id)
    if check_processing_answer(user_id, message):
        return

    user_data = find_user_data(user_id)
    subjects_popularity = count_subjects_popularity()
    most_popular_subject = []

    if subjects_popularity:

        for subject, value in subjects_popularity.items():

            if value == max(subjects_popularity.values()):
                most_popular_subject.append(subject)
                most_popular_subject.append(value)

    latest_tasks = find_latest_issues()
    tasks_text = ""

    if latest_tasks[0]:
        for i, task in enumerate(latest_tasks):
            if task:
                tasks_text += f'{i + 1}. "{task}"\n'

    else:
        tasks_text = "Запросов пока нет"

    bot.send_message(message.chat.id, "Статистика Ваша и общая:\n\n"
                                      "<b>Личная статистика:\n\n</b>"
                                      f"<b>Ваше имя:</b> {message.from_user.first_name}\n"
                                      f"<b>Выбранный предмет:</b> {user_data['subject']}\n"
                                      f"<b>Выбранный уровень объяснения:</b> {user_data['level']}\n"
                                      f"<b>Общее количество запросов:</b> {user_data['number_of_tasks']}\n\n\n"
                                      "<b>Общая статистика:\n\n</b>"
                                      f"<b>Самый популярный предмет на данный момент:</b> {most_popular_subject[0]}\n"
                                      f"<b>Количество пользователей, использующих его:</b> {most_popular_subject[1]}\n"
                                      f"<b>Последние запросы к нейросети:</b>\n\n{tasks_text}", parse_mode='html')


# работа с GPT
@bot.message_handler(content_types=['text'], func=lambda message: message.text.lower() == "запуск gpt")
@bot.message_handler(commands=['talk'])
def take_issue(message):
    user_id = message.from_user.id

    check_user(user_id)
    if check_processing_answer(user_id, message):
        return

    bot.send_message(message.chat.id, 'Можете задать Ваш вопрос.\n\n'
                                      'Важно:\n\n'
                                      "0. Нейросеть призвана предоставить вам информацию по астрономии или географии"
                                      " (в зависимости от вашего выбора) и на определенном уровне (новичок или профи),"
                                      " поэтому для получения лучших ответов следует "
                                      "задавать ей вопросы, связанные с данной тематикой."
                                      '\n\n1. Запрос должен быть текстовым,'
                                      ' иначе у Вас просто не получится его сделать.\n\n'
                                      '2. Если захотите продолжить, то'
                                      ' смело жмите на кнопку "Продолжи!", '
                                      'которая появится после Вашего первого запроса.\n\n'
                                      '3. Если хотите воспользоваться командами или изменить что-то в параметрах,'
                                      ' то Вам нужно сначала '
                                      'завершить диалог с нейросетью. Иначе команда будет воспринята как запрос.',
                     reply_markup=make_reply_keyboard(["Выход"]))

    logging.info("сообщение с инструкцией по созданию промта успешно отправлено")

    bot.register_next_step_handler(message, ask_gpt)


def ask_gpt(message):
    user_id = message.from_user.id

    check_user(user_id)
    if check_processing_answer(user_id, message):
        return

    prompt = message.text

    if not prompt:  # проверка типа сообщения

        logging.error("неправильный формат запроса")

        bot.send_message(message.chat.id, "Кажется, Вы отправили не текстовый запрос. Я пока не умею принимать"
                                          " такие. Попробуйте отправить что-то другое!")

        bot.register_next_step_handler(message, ask_gpt)

        return

    if prompt in ["Выход", "/exit", "выход"]:
        bot.send_message(message.chat.id, "До скорого!", reply_markup=main_menu_keyboard)
        logging.info("выход осуществлен успешно")
        return

    user_data = find_user_data(user_id)

    if prompt.lower() == "продолжи!":

        if user_data['answer'] == "":
            logging.error("попытка продолжить, когда вопрос еще не была задан")

            bot.reply_to(message, "Так как запроса еще не было, то и продолжать пока нечего. Чтобы "
                                  "воспользоваться данной опцией, сначала задайте ваш вопрос.")
            bot.register_next_step_handler(message, ask_gpt)
            return

    else:
        update_user_data(user_id, 'answer', "")
        update_user_data(user_id, 'task', "")

    update_user_data(user_id, 'processing_answer', 1)

    previous_answer = user_data['answer']

    current_subject = user_data["subject"]
    current_level = user_data["level"]
    settings_for_prompt = get_settings(subject=current_subject, level=current_level)

    msg = bot.reply_to(message=message, text="Ваш запрос принят! Уже обрабатываю...")
    bot.send_chat_action(message.chat.id, "TYPING")
    answer_gpt = gpt.make_prompt(user_content=prompt, gpt_answer=previous_answer, system_prompt=settings_for_prompt)

    update_user_data(user_id, 'processing_answer', 0)
    update_user_data(user_id, 'answer', answer_gpt[2])  # сохраняем ответ нейросети (если он есть)

    if prompt.lower() != "продолжи!":
        update_user_data(user_id, 'task', prompt)
        update_user_data(user_id, "number_of_tasks", user_data["number_of_tasks"] + 1)

    bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)

    if not answer_gpt[0]:  # если ответ окончен или произошла ошибка

        if answer_gpt[1] == "Ответ окончен.\n\nЖду Ваших вопросов!":

            logging.info("ответ нейросети окончен")

        else:

            logging.error(f"Произошла ошибка: {answer_gpt[1]}")

        bot.send_message(message.chat.id, answer_gpt[1], reply_markup=make_reply_keyboard(["Выход"]))

    else:  # если запрос успешно пришел
        bot.reply_to(message, answer_gpt[1], reply_markup=make_reply_keyboard(["Продолжи!", "Выход"]))

        logging.info("Ответ нейросети успешно доставлен")

    bot.register_next_step_handler(message, ask_gpt)


# ответ на остальную всякую всячину, которую очень редко отправляют
CONTENT_TYPES = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice"]


@bot.message_handler(content_types=CONTENT_TYPES)
def any_msg(message):
    user_id = message.from_user.id

    if find_user_data(user_id)['processing_answer'] == 1:

        logging.debug("попытка задать еще один вопрос, когда нейросеть уже генерирует другой")

        bot.reply_to(message, "Нейросеть уже отвечает на Ваш вопрос. Прежде чем задать следующий,"
                              " дождитесь ответа на предыдущий.")

    else:

        logging.debug("попытка общения с ботом")

        bot.send_message(message.chat.id, '👍 \n'
                                          'Если хотите задать вопрос, то сначала нажмите на кнопку"Запуск GPT"',
                         reply_markup=main_menu_keyboard)


# дружелюбность и вежливость бота
def filter_bye(message):
    word = "пока"
    return word in message.text.lower()


def filter_hi(message):
    word = "привет"
    return word in message.text.lower()


def filter_wasup(message):
    word = "как дела?"
    return word in message.text.lower()


@bot.message_handler(content_types=['text'], func=filter_bye)
def say_bye(message):
    user_name = message.from_user.first_name
    logging.info("с кем-то попрощались")
    bot.send_message(message.from_user.id, text=f"{user_name}, пока...")


@bot.message_handler(content_types=['text'], func=filter_wasup)
def say_wasup(message):
    logging.info("кому-то ответили, как дела")
    bot.send_message(message.from_user.id, text=f"Спасибо, что спросил_а! Дела отлично! 👍")


@bot.message_handler(content_types=['text'], func=filter_hi)
def say_wasup(message):
    user_name = message.from_user.first_name
    logging.info("с кем-то поздоровались")
    bot.send_message(message.from_user.id, text=f"{user_name}, Привет! 🙃")


@bot.callback_query_handler(func=lambda call: True)
def process_calls(call):
    c_id = call.message.chat.id
    m_id = call.message.message_id
    user_id = call.from_user.id

    check_user(user_id)
    if check_processing_answer(user_id, call.message):
        return

    data = call.data
    text = ""

    if data == "subject":
        text = "Выберите предмет:"

    if data == "level":
        text = "Выберите уровень объяснения:"

    if data in ["Астрономия", "География"]:
        update_user_data(user_id, "subject", value=data)
        text = "Выберите предмет:"

    if data in ["Новичок", "Профи"]:
        update_user_data(user_id, "level", value=data)
        text = "Выберите уровень объяснения:"

    if data == "go_back":
        text = "Какой параметр вы хотите изменить?"

    keyboard = make_inline_keyboard(data, user_id=user_id)

    bot.edit_message_text(chat_id=c_id, message_id=m_id, text=text, reply_markup=keyboard)


# запуск бота 🎉
if __name__ == "__main__":
    logging.info("Бот запущен")
    bot.infinity_polling()
