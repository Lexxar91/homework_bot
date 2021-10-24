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

PRACTICUM_TOKEN = os.getenv('PTOKEN')
TELEGRAM_TOKEN = os.getenv('TTOKEN')
CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600  # А я заметил что тут 300сек было а не 600 =)
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_message(bot, message):
    """Отправка сообщения боту."""
    try:
        logging.info(f'Отправленно сообщение {message}')
        return bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as err:
        logging.error(f'Cообщение не отправлено: {err}')


def get_api_answer(url, current_timestamp):
    """Запрос к API сервера Яндекс."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}

    try:
        homework = requests.get(url, headers=headers, params=payload)
        if homework.status_code != 200:
            homework.raise_for_status()
        logging.info('Все отлично')
        return homework.json()

    except requests.exceptions.RequestException:
        logging.error(
            'Что-то пошло не так при подключении'
            'к серверу')


def parse_status(homework):
    """Парсим статус работы."""
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error("Домашняя работа отсувствует")
    if verdict is None:
        logging.error("Решение по домашний работе отсувствует")
    logging.info(f'Статус изменился на {verdict}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверка ответа с сервера."""
    homeworks = response.get('homeworks')
    if homeworks is None:
        logging.error('homeworks не найден')
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES.keys():
            return homeworks
        else:
            raise Exception('Нет подходящего статуса')
    return homeworks


def main():
    """Король функций."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    url = ENDPOINT
    while True:
        try:
            get_api_answer_result = get_api_answer(url, current_timestamp)
            check_response_result = check_response(get_api_answer_result)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error('бот не доступен')
            bot.send_message(
                chat_id=CHAT_ID, text=f'Что-то пошло не так: {error}'
            )
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
