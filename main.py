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


def analyze_images(image_paths):
    print("\n[*] Анализ изображений...")

    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    for path in image_paths:
        image = Image.open(path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to(device)
        out = model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        print(f"[📷] {os.path.basename(path)}: {caption}")


def main():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # включи, если не хочешь видеть окно
    driver = webdriver.Chrome(service=Service(), options=options)

    image_paths = download_captcha_images(driver)
    driver.quit()

    if image_paths:
        analyze_images(image_paths)
    else:
        print("[!] Не найдено изображений для анализа")


if __name__ == "__main__":
    main()
