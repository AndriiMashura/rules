import requests
from bs4 import BeautifulSoup
import re
import time
from random import randint
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Регулярное выражение для проверки кириллицы
cyrillic_pattern = re.compile(r'[А-Яа-яЁё]')
exclude_phrases = ['blocked-sites-casinos', 'blocked-sites-bookmakers', 'blocked-sites-russian', 'pirates']

# Заголовки для имитации запроса от браузера
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def fetch_page(url, retries=3):
    """Запрашивает страницу с повторной попыткой при ошибках и возвращает объект BeautifulSoup, либо None в случае ошибки"""
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            else:
                logging.warning(f"Ошибка {response.status_code} при запросе страницы {url}")
        except requests.RequestException as e:
            logging.error(f"Сетевая ошибка: {e}")
            attempt += 1
            time.sleep(2)  # Задержка между повторными попытками
    return None

def get_total_pages():
    """Определяет количество страниц, парсируя первую страницу для получения максимального числа"""
    url = 'https://uablocklist.com/blocklist?page=1'
    soup = fetch_page(url)
    if not soup:
        logging.info("Не удалось получить первую страницу для определения количества страниц.")
        return 800  # Значение по умолчанию, если определение страниц не удалось

    # Ищем элемент с максимальным значением страницы
    last_page_links = soup.select("a.page-link[href*='blocklist?page=']")
    max_page = 800
    for link in last_page_links:
        try:
            page_number = int(link.text)
            max_page = max(max_page, page_number)
        except ValueError:
            continue

    logging.info(f"Обнаружено страниц для парсинга: {max_page}")
    return max_page

def parse_page(soup, domains_set, new_domains):
    """Парсит ссылки с доменами на странице, фильтрует и добавляет уникальные домены в список для записи"""
    domain_elements = soup.select("a[href*='/blocklist/']")

    for element in domain_elements:
        href = element['href']
        domain = href.split('/blocklist/')[-1]

        if any(phrase in domain for phrase in exclude_phrases) or domain in domains_set:
            continue

        if cyrillic_pattern.search(domain):
            logging.info(f"Домен с кириллицей пропущен: {domain}")
            continue

        domains_set.add(domain)
        new_domains.append(domain)

def save_domains(domains, file_path='blocked_domains.txt'):
    """Сохраняет домены в указанный файл и очищает буфер"""
    with open(file_path, 'a') as file:
        for domain in domains:
            file.write(domain + '\n')
    logging.info(f"Сохранено {len(domains)} новых доменов.")
    domains.clear()

def parse_domains(batch_size=50):
    """Главная функция парсинга доменов с автоматическим определением количества страниц и батчевой записью"""
    max_pages = get_total_pages()
    page_number = 1
    domains_set = set()
    new_domains = []

    try:
        while page_number <= max_pages:
            url = f'https://uablocklist.com/blocklist?page={page_number}'
            logging.info(f"Открываем {url}...")

            soup = fetch_page(url)
            if not soup:
                logging.info("Пропускаем страницу из-за ошибки.")
                page_number += 1
                continue

            parse_page(soup, domains_set, new_domains)
            logging.info(f"Страница {page_number} успешно пройдена и обработана.")

            # Периодическая запись на диск
            if page_number % batch_size == 0:
                save_domains(new_domains)

            # Адаптивная задержка
            time.sleep(randint(1, 3))  # Задержка в пределах 1-3 секунд
            page_number += 1

        # Сохранение оставшихся доменов после завершения
        if new_domains:
            save_domains(new_domains)

    except KeyboardInterrupt:
        logging.info("Парсинг был прерван пользователем.")
        if new_domains:
            logging.info("Сохраняем оставшиеся данные перед завершением.")
            save_domains(new_domains)
    
    logging.info("Парсинг завершен. Данные сохранены в 'blocked_domains.txt'.")
    return domains_set

# Запуск парсинга
if __name__ == "__main__":
    parse_domains()
