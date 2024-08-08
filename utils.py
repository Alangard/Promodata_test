import json
import re
from typing import Optional

def separate_words_and_numbers(text):
    # Регулярное выражение для поиска чисел и текста
    match = re.match(r'^(.*?)(\d+)$', text.strip())
    
    if match:
        words = match.group(1).strip()
        number = match.group(2)
        return words
    else:
        # Если число не найдено, возвращаем оригинальный текст и пустую строку
        return text.strip()
    
def check_availability(target_address: str, store_list: list) -> Optional[str]:
    for store in store_list:
        # Проверяем, содержит ли поле address искомый адрес
        if target_address in store["address"]:
            # Если объект найден, возвращаем значение поля text из availability
            return store["availability"]["text"]
    return None


# Чтение конфигурации
with open('config.json', 'r', encoding='utf-8') as file:
    config = json.load(file)

city = config['city']
category = config['category']
store_address = config['store_address']
file_path = config['info_file_path']
target_address = f'{city}, {store_address}'


# Настройка заголовков
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0',
    'referer': 'https://www.bethowen.ru/iwaf-captcha'
}