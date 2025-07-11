import hashlib
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.humansnotinvited.com/"
SAVE_DIR = "captcha_images"
DB_FILE = "db.txt"

os.makedirs(SAVE_DIR, exist_ok=True)


def load_db(path=DB_FILE):
    db = {}
    with open(path, 'r') as f:
        for line in f:
            md5_hash, category = line.strip().split(';')
            db[md5_hash] = category
    return db


def get_md5(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    return hashlib.md5(content).hexdigest()


def download_captcha_images(driver):
    driver.get(URL)
    try:
        print("[*] Ожидание появления изображений...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "img"))
        )
    except:
        print("[!] Изображения не загрузились")

    tiles = driver.find_elements(By.TAG_NAME, "img")
    print(f"[+] Найдено {len(tiles)} <img> тегов")

    image_paths = []
    for idx, tile in enumerate(tiles):
        src = tile.get_attribute('src')
        if not src:
            continue
        if "/captcha/image.php" in src:
            response = requests.get(src, verify=False)
            filename = os.path.join(SAVE_DIR, f"tile_{idx}.png")
            with open(filename, "wb") as f:
                f.write(response.content)
            image_paths.append(filename)
            print(f"[✓] Скачал tile_{idx}.png")
        else:
            print(f"[i] Пропущено изображение {idx} с внешним src: {src}")

    return image_paths


def solve_captcha_with_db(driver, db):
    # Получаем текст задания
    task_element = driver.find_element(By.CSS_SELECTOR, ".header strong")
    task_keyword = task_element.text.lower().strip()
    print(f"[🎯] Задание: выбрать все с «{task_keyword}»")

    # Скачиваем картинки капчи
    image_paths = download_captcha_images(driver)
    if not image_paths:
        print("[!] Не найдено изображений для анализа")
        return

    # Находим все div с картинками (чтобы кликать)
    image_divs = driver.find_elements(By.CLASS_NAME, "captcha-image")

    # Для каждой картинки считаем md5 и смотрим в базе
    for idx, path in enumerate(image_paths):
        md5_hash = get_md5(path)
        category = db.get(md5_hash, None)
        if category == task_keyword:
            print(f"[✓] Подходит: tile_{idx}.png (категория: {category})")
            try:
                image_divs[idx].click()
                print(f"[🖱️] Клик по tile_{idx}.png")
            except IndexError:
                print(f"[!] Элемент для tile_{idx}.png не найден")
        else:
            print(f"[✗] Не подходит: tile_{idx}.png (категория: {category})")

    # Нажать Verify
    verify_button = driver.find_element(By.CSS_SELECTOR, ".button")
    verify_button.click()
    print("[🚀] Нажата кнопка Verify")


def main():
    chrome_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")

    if not os.path.exists(chrome_path):
        print(f"[❌] chromedriver.exe не найден по пути: {chrome_path}")
        return
    else:
        print(f"[✓] Используется chromedriver по пути: {chrome_path}")

    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # если хочешь скрыть окно браузера

    service = Service(executable_path=chrome_path)
    driver = webdriver.Chrome(service=service, options=options)

    db = load_db()

    driver.get(URL)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".header strong"))
    )
    solve_captcha_with_db(driver, db)

    input("[⏸] Нажмите Enter, чтобы закрыть окно браузера...")
    driver.quit()


if __name__ == "__main__":
    main()
