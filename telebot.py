import logging
import os
import time
import traceback

import requests
import telegram

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEVMAN_TOKEN = os.getenv('DEVMAN_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

REVIEWS_URL = 'https://dvmn.org/api/user_reviews/'
LONGPOLLING_URL = 'https://dvmn.org/api/long_polling/'


class TelegramLogsHandler(logging.Handler):

    def __init__(self, token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        super().__init__()
        self.chat_id = chat_id
        self.bot = telegram.Bot(token=token)

    def emit(self, record):
        log_prefix = '#'
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_text = f'Exception: {exc_type.__name__} ({exc_value})\n{"".join(traceback.format_tb(exc_traceback))}'
            self.bot.send_message(
                text=f'{log_prefix} {log_text}',
                chat_id=self.chat_id)
        else:
            self.bot.send_message(text=f'{log_prefix} {self.format(record)}',
                                  chat_id=self.chat_id)


def prepare_message(devman_response):
    lesson_title = devman_response['lesson_title']
    lesson_url = devman_response['lesson_url']
    submitted_at = devman_response['submitted_at'][:16].replace('T', ' ')
    result_text = 'Unfortunately, there were errors in the work.' if devman_response['is_negative'] \
        else 'The teacher liked everything, you can proceed to the next lesson!'
    message_text = f'''\
    Hi, your work is checked at {submitted_at}\r
    *work name:* ["{lesson_title}"]({lesson_url})\r
    *result:* {result_text}\n 
    '''
    return message_text


def send_message(devman_response, token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    bot = telegram.Bot(token=token)
    bot.send_message(text=prepare_message(devman_response),
                     chat_id=int(chat_id),
                     parse_mode=telegram.ParseMode.MARKDOWN)


def main():
    logger = logging.getLogger('telegram')
    logger.setLevel(logging.WARNING)
    logger.addHandler(TelegramLogsHandler(token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID))
    logger.warning("Bot started.")
    timestamp = time.time()
    while True:
        try:
            response = requests.get(LONGPOLLING_URL, allow_redirects=False, timeout=120,
                                    headers={'Authorization': DEVMAN_TOKEN}, params={'timestamp': timestamp})
            response.raise_for_status()
            checked_tasks = response.json()
            if 'status' not in checked_tasks:
                continue
            if checked_tasks['status'] == 'timeout':
                timestamp = checked_tasks['timestamp_to_request']
            elif checked_tasks['status'] == 'found':
                timestamp = checked_tasks['last_attempt_timestamp']
                for attempt in checked_tasks['new_attempts']:
                    send_message(attempt)
        except requests.exceptions.ReadTimeout:
            pass
        except requests.exceptions.ConnectionError:
            time.sleep(60)
        except Exception:
            logger.error('', exc_info=True)
            break
    logger.warning("Bot stopped.")


if __name__ == '__main__':
    main()
