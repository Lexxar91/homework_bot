import logging
import requests
import telegram
import time
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    filemode='w',
    encoding='utf-8'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"

HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


class MyOwnException(Exception):
    """Кастомное исключения."""
    pass


def send_message(bot, message):
    """Отправка сообщения боту."""
    try:
        logging.info(f"Отправленно сообщение {message}")
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as err:
        logging.error(f"Cообщение не отправлено: {err}", exc_info=True)


def get_api_answer(current_timestamp):
    """Запрос к API сервера Яндекс."""
    payload = {"from_date": current_timestamp}

    try:
        homework = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if homework.status_code != 200:
            homework.raise_for_status()
        logging.info("Все отлично")
        return homework.json()

    except requests.exceptions.RequestException:
        logging.error(
            "Что-то пошло не так при подключении"
            "к серверу", exc_info=True)


def parse_status(homework):
    """Парсим статус работы."""
    homework_status = HOMEWORK_STATUSES[homework.get("status")]
    homework_name = homework.get("homework_name")
    if homework_name is None:
        logging.warning("Домашняя работа отсувствует")
    if homework_status is None:
        logging.warning("Решение по домашний работе отсувствует")
    logging.info(f"Статус изменился на {homework_status}")

    return f'Изменился статус проверки работы "{homework_name}".' \
           f'{homework_status}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN is None or\
            TELEGRAM_TOKEN is None or \
            TELEGRAM_CHAT_ID is None:
        return False
    return True


def check_response(response):
    """Проверка ответа с сервера."""
    if response['homeworks'] is None:
        raise MyOwnException("Задания не обнаружены")

    if not isinstance(response['homeworks'], list):
        raise MyOwnException("response['homeworks'] не является списком")
    logging.debug("API проверен на корректность")
    return response['homeworks']


def main():
    """Король функций."""
    if not check_tokens():
        logging.critical("Отсутствует переменная(-ные) окружения")
        return 0
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            get_api_answer_result = get_api_answer(ENDPOINT, current_timestamp)
            check_response_result = check_response(get_api_answer_result)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error("бот не доступен")
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text=f'Что-то пошло не так: {error}'
            )
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
