from PIL import Image, ImageDraw, ImageFont
import logging
import os
import random

def generate_image(name1, name2, percentage, data):
    # Добавляем логирование входящих данных
    logging.debug(f"Received data for image generation: {data}")
    
    # Получаем список всех фоновых изображений
    background_dir = "static/background"
    background_images = [f for f in os.listdir(background_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    if not background_images:
        # Если нет фоновых изображений, создаем пустое
        img = Image.new("RGB", (1080, 1920), color="#f9f4ff")
    else:
        # Выбираем случайное фоновое изображение
        random_bg = random.choice(background_images)
        bg_path = os.path.join(background_dir, random_bg)
        
        # Загружаем и масштабируем фоновое изображение
        img = Image.open(bg_path)
        img = img.convert('RGB')
        img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img)

    # Определяем цвета
    BLACK = "#000000"
    BLUE = "#1a73e8"

    font_path = "static/fonts/Dudka_Bold.ttf"
    font_big = ImageFont.truetype(font_path, 100)
    font_small = ImageFont.truetype(font_path, 50)

    # Основной текст
    draw.text((100, 405), f"{name1} + {name2}", font=font_big, fill=BLUE)  # Смещение на 3 пикселя вниз с 400
    draw.text((100, 603), f"Совместимость: {percentage}%", font=font_small, fill=BLACK)  # Смещение на 2 пикселя вниз с 600

    # Топ треков с проверкой на наличие данных
    draw.text((100, 800), "Топ треков:", font=font_small, fill=BLACK)
    top_tracks = data.get("top_tracks", [])
    logging.debug(f"Top tracks received: {top_tracks}")
    
    if top_tracks and len(top_tracks) > 0:
        for i, track in enumerate(top_tracks[:3]):
            text = f"{i+1}. {track}"
            logging.debug(f"Drawing track: {text}")
            draw.text((120, 860 + i * 60), text, font=font_small, fill=BLACK)
    else:
        logging.warning("No tracks data available")
        draw.text((120, 860), "Нет совпадений", font=font_small, fill=BLACK)

    # Топ исполнителей с проверкой на наличие данных
    draw.text((100, 1100), "Топ исполнителей:", font=font_small, fill=BLACK)
    top_artists = data.get("top_artists", [])
    logging.debug(f"Top artists received: {top_artists}")
    
    if top_artists and len(top_artists) > 0:
        for i, artist in enumerate(top_artists[:3]):
            text = f"{i+1}. {artist}"
            logging.debug(f"Drawing artist: {text}")
            draw.text((120, 1160 + i * 60), text, font=font_small, fill=BLACK)
    else:
        logging.warning("No artists data available")
        draw.text((120, 1160), "Нет совпадений", font=font_small, fill=BLACK)

    draw.text((100, 1800), "compare-music.ru", font=font_small, fill="#999999")

    output_path = f"/tmp/share_{name1}_{name2}.jpg"
    img.save(output_path)
    return output_path