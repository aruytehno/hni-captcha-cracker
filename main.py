from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import base64
import os
import time
import requests
import torch
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.humansnotinvited.com/"
SAVE_DIR = "captcha_images"
os.makedirs(SAVE_DIR, exist_ok=True)


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


def click_matching_tiles(driver, task_keyword, image_captions):
    print(f"[*] Кликаю по картинкам с '{task_keyword}'...")
    # На странице в .captcha-image лежат div'ы с картинками
    captcha_images = driver.find_elements(By.CSS_SELECTOR, ".captcha-image")

    for idx, caption in enumerate(image_captions):
        if task_keyword.lower() in caption.lower():
            print(f"[✓] Кликаю по tile_{idx}.png → {caption}")
            captcha_images[idx].click()
        else:
            print(f"[✗] Не кликаю по tile_{idx}.png → {caption}")


# В analyze_images нужно вернуть captions, чтобы потом использовать
def analyze_images(image_paths):
    print("\n[*] Анализ изображений...")

    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    captions = []
    for path in image_paths:
        image = Image.open(path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to(device)
        out = model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        captions.append(caption)
        print(f"[📷] {os.path.basename(path)}: {caption}")
    return captions

def solve_captcha(driver, image_paths):
    print("\n[*] Начинаю решение капчи...")

    # Шаг 1: Извлекаем задание
    task_element = driver.find_element(By.CSS_SELECTOR, ".header strong")
    task_keyword = task_element.text.lower().strip()
    print(f"[🎯] Задание: выбрать все с «{task_keyword}»")

    # Шаг 2: Загружаем модель и процессор
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    # Шаг 3: Анализируем изображения
    captions = []
    for path in image_paths:
        image = Image.open(path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to(device)
        out = model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        captions.append(caption)

    # Шаг 4: Выбираем подходящие
    selected_indices = []
    for idx, caption in enumerate(captions):
        if task_keyword in caption.lower():
            selected_indices.append(idx)
            print(f"[✓] Подходит: tile_{idx}.png → {caption}")
        else:
            print(f"[✗] Не подходит: tile_{idx}.png → {caption}")

    # Шаг 5: Кликаем по нужным
    image_divs = driver.find_elements(By.CLASS_NAME, "captcha-image")
    for idx in selected_indices:
        try:
            image_divs[idx].click()
            print(f"[🖱️] Клик по изображению tile_{idx}.png")
        except IndexError:
            print(f"[!] Не найден элемент для индекса {idx}")

    # Шаг 6: Кликаем на кнопку "Verify"
    verify_button = driver.find_element(By.CLASS_NAME, "button")
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

    image_paths = download_captcha_images(driver)
    if image_paths:
        captions = analyze_images(image_paths)
        task_keyword = "cars"  # можно парсить с сайта, если хочешь
        click_matching_tiles(driver, task_keyword, captions)
    else:
        print("[!] Не найдено изображений для анализа")

    # Нажать кнопку Verify после кликов
    verify_button = driver.find_element(By.CSS_SELECTOR, ".button")
    print("[🚀] Нажата кнопка Verify")
    verify_button.click()

    input("[⏸] Нажмите Enter, чтобы закрыть окно браузера...")
    driver.quit()


if __name__ == "__main__":
    main()
