import os
import time
import logging
import requests
import telegram

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEVMAN_TOKEN = os.getenv('DEVMAN_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

REVIEWS_URL = 'https://dvmn.org/api/user_reviews/'
LONGPOLLING_URL = 'https://dvmn.org/api/long_polling/'


def send_message(devman_response, token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    bot = telegram.Bot(token=token)
    name = 'Hi'
    for post in bot.get_updates():
        if post.message.from_user.id == chat_id:
            name = post.message.from_user.name
            break
    lesson_title = devman_response['lesson_title']
    lesson_url = devman_response['lesson_url']
    submitted_at = devman_response['submitted_at'][:16].replace('T',' ')
    result_text = 'Unfortunately, there were errors in the work.' if devman_response['is_negative']\
        else 'The teacher liked everything, you can proceed to the next lesson!'
    message_text = f'''\
    {name}, your work is checked at {submitted_at}\r
    *work name:* ["{lesson_title}"]({lesson_url})\r
    *result:* {result_text}\n 
    '''
    bot.send_message(text=message_text, chat_id=int(chat_id),parse_mode=telegram.ParseMode.MARKDOWN)


def main():
    logging.warning("bot started")
    timestamp = time.time()-86400*6
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


if __name__ == '__main__':
    main()
