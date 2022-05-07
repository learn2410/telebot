import logging
import os
import time

import requests
import telegram

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEVMAN_TOKEN = os.getenv('DEVMAN_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

REVIEWS_URL = 'https://dvmn.org/api/user_reviews/'
LONGPOLLING_URL = 'https://dvmn.org/api/long_polling/'

logger = logging.getLogger('telegram')


class TelegramLogsHandler(logging.Handler):

    def __init__(self, bot, chat_id=TELEGRAM_CHAT_ID):
        super().__init__()
        self.chat_id = chat_id
        self.bot = bot

    def emit(self, record):
        log_entry = f'# {self.format(record)}'
        self.bot.send_message(text=log_entry, chat_id=self.chat_id)


def prepare_message(attempt):
    lesson_title = attempt['lesson_title']
    lesson_url = attempt['lesson_url']
    submitted_at = attempt['submitted_at'][:16].replace('T', ' ')
    result_text = 'Unfortunately, there were errors in the work.' if attempt['is_negative'] \
        else 'The teacher liked everything, you can proceed to the next lesson!'
    message_text = f'''\
    Hi, your work is checked at {submitted_at}\r
    *work name:* ["{lesson_title}"]({lesson_url})\r
    *result:* {result_text}\n 
    '''
    return message_text


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.setLevel(logging.WARNING)
    logger.addHandler(TelegramLogsHandler(bot, chat_id=TELEGRAM_CHAT_ID))
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
                    bot.send_message(text=prepare_message(attempt),
                                     chat_id=int(TELEGRAM_CHAT_ID),
                                     parse_mode=telegram.ParseMode.MARKDOWN)
        except requests.exceptions.ReadTimeout:
            pass
        except requests.exceptions.ConnectionError:
            time.sleep(60)
        except Exception:
            logger.exception('Unexpected exception')
            time.sleep(60)
    logger.warning("Bot stopped.")


if __name__ == '__main__':
    main()
