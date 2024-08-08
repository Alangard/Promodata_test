import os
import requests
import csv
import json
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils import separate_words_and_numbers, check_availability, headers, city, category, store_address, file_path, target_address


def setup_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument('--headless') 
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_all_categories_links(driver: webdriver, category_name_request: Optional[str] = None) -> List[str]:


    if category_name_request:
        if '/' in category_name_request:
            category_keywords = list(category_name_request.split('/'))
            category_name_request = {'category_name': category_keywords[0].lower(), 'sub_category_name': category_keywords[1].lower()}
        else:
            category_name_request = {'category_name': category_name_request.lower(), 'sub_category_name': None}

    url = 'https://www.bethowen.ru/catalogue/'

    driver.get(url)

    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "section_item_inner")))
    tables = driver.find_elements(By.CLASS_NAME, "section_item_inner")

    # Список для хранения всех ссылок
    categories_links = []

    for table in tables:
        category_element = table.find_element(By.CLASS_NAME, 'name')
        sub_categories = table.find_elements(By.CLASS_NAME, 'sect')
        category_link_tag = category_element.find_element(By.CSS_SELECTOR, 'a.dark_link')
        category_name = category_link_tag.text.strip()

        if category_name_request:
            if category_name_request['category_name'] == category_name.lower():
                if category_name_request['sub_category_name'] is None:
                    categories_links.append(category_link_tag.get_attribute('href'))
                    break
                else:
                    for sub_category in sub_categories:
                        sub_category_link_tag = sub_category.find_element(By.CSS_SELECTOR, 'a.dark_link')
                        sub_category_name = separate_words_and_numbers(sub_category_link_tag.text.strip())
                        if category_name_request['sub_category_name'] == sub_category_name.lower():
                            categories_links.append(sub_category_link_tag.get_attribute('href'))
                            break
                    break
        else:
            categories_links.append(category_link_tag.get_attribute('href'))
    print(f'categories_links: {categories_links}')
    return categories_links

def get_products_ids_by_category_link(driver: webdriver, category_url: Optional[str] = None) -> List[str]:    
    driver.get(category_url)

    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "bth-card-element")))

    # Получение всех элементов товаров
    product_elements = driver.find_elements(By.CLASS_NAME, "bth-card-element")
    
    products_ids = []

    for product in product_elements:
        product_id = product.get_attribute("data-product-id")
        products_ids.append(product_id)

    return products_ids 

def get_product_info_by_id(product_id: str, target_address: str) -> List[Dict]:
    product_response = requests.get(f'https://www.bethowen.ru/api/local/v1/catalog/products/{product_id}/details')
    
    if product_response.status_code == 200:
        try:
            product_json_data = product_response.json()
            products_info = []

            if product_json_data['offers']:
                for offer in product_json_data['offers']:
                    product_info = {
                        'name': product_json_data['name'],
                        'articul': offer['code'],
                        'retail_price': offer['retail_price'],
                        'discount_price': offer['discount_price'] if offer['discount_price'] != offer['retail_price'] else None,
                        'product_option_name': offer['size']
                        }
                    
                    offer_response = requests.get(f'https://www.bethowen.ru/api/local/v1/catalog/offers/{offer['id']}/details')
                    
                    if offer_response.status_code == 200:
                        try:
                            offer_json_data = offer_response.json()
                            stores_info = offer_json_data['availability_info']['offer_store_amount']
                            product_info['availability'] = check_availability(target_address, stores_info)
                        except json.JSONDecodeError:
                            print("Не удалось декодировать JSON")

                    else:
                        print(f"Ошибка запроса: {offer_response.status_code}") 

                    products_info.append(product_info)
            
            return products_info

        except json.JSONDecodeError:
            print("Не удалось декодировать JSON")
    else:
        print(f"Ошибка запроса: {product_response.status_code}") 

def write_product_to_csv(product_info: List[Dict], file_path: str, append=False, write_header=False) -> None:

    mode = 'a' if append else 'w'  # Режим добавления ('a') или записи ('w')
    with open(file_path, mode, newline='', encoding='utf-8') as file:
        if len(product_info) > 0:
            writer = csv.DictWriter(file, fieldnames=product_info[0].keys())
            if write_header:
                writer.writeheader()
            for product_info in product_info:
                writer.writerow(product_info)

    print(f"Данные успешно записаны в файл {file_path}")

def get_page_count_by_category(driver: webdriver, category_url: Optional[str] = None) -> str:
    driver.get(category_url)

    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "bth-card-element")))

    # Получение nav_bar элемента
    bottom_nav = driver.find_element(By.CLASS_NAME, "bottom_nav")

    max_page_count = 1

    if bottom_nav:
        a_tags = bottom_nav.find_elements(By.TAG_NAME, 'a')
        if not a_tags:
            return max_page_count
        else:
            max_page_count = int(a_tags[-1].text.strip())
            return max_page_count
    else:
        return max_page_count    

# Основная функция для сбора данных
def main():
    driver = setup_driver()
    file_exists = os.path.isfile(file_path)

    categories_links = get_all_categories_links(driver, category)
    
    for category_link in categories_links:
        current_page = 1
        max_page_num = get_page_count_by_category(driver, category_link)
        
        try:
            while current_page <= max_page_num:
                link = f'{category_link}?PAGEN_1={current_page}'
                products_ids = get_products_ids_by_category_link(driver, link)
                for product_id in products_ids:
                    product_info = get_product_info_by_id(product_id, target_address)
                    write_product_to_csv(product_info, file_path, append=True, write_header= not file_exists)
                    file_exists = True  # После первой записи устанавливаем флаг, чтобы больше не писать заголовки
                current_page += 1
        finally:
            driver.quit()


if __name__ == '__main__':
    main()