from PIL import Image, ImageDraw, ImageFont
import logging
import os

def generate_image(name1, name2, percentage, data):
    logging.debug(f"Generating image with frames for: {name1}, {name2}, {percentage}%, data: {data}")

    WIDTH, HEIGHT = 1080, 1920
    IMAGE_BACKGROUND_COLOR = "#1A1A1A"

    # Цвета для рамок и текста
    FRAME_FILL_COLOR = "#252525"  # Фон внутри рамки
    FRAME_OUTLINE_COLOR = "#F0A500" # Акцентный цвет для обводки
    TEXT_COLOR_MAIN = "#E0E0E0"
    ACCENT_COLOR = "#F0A500" # Для заголовков и важных элементов
    TEXT_COLOR_MUTED = "#A7A7A4"

    # Параметры рамок
    FRAME_CORNER_RADIUS = 25
    FRAME_OUTLINE_WIDTH = 4 # Толщина обводки
    CONTENT_PADDING_X = 60  # Горизонтальный отступ от края изображения до рамок
    CONTENT_PADDING_Y_TOP = 150 # Вертикальный отступ сверху до первого элемента
    FRAME_PADDING_INTERNAL = 40 # Внутренний отступ в рамках

    img = Image.new("RGB", (WIDTH, HEIGHT), color=IMAGE_BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_path_bold = "static/fonts/Inter-Bold.ttf"
        font_path_regular = "static/fonts/Inter-Regular.ttf"

        font_names = ImageFont.truetype(font_path_bold, 80)
        font_percentage_val = ImageFont.truetype(font_path_bold, 120)
        font_percentage_label = ImageFont.truetype(font_path_regular, 50) # "совместимость"
        font_section_title = ImageFont.truetype(font_path_bold, 50) # "Общие треки"
        font_list_item_track = ImageFont.truetype(font_path_regular, 38)
        font_list_item_artist_detail = ImageFont.truetype(font_path_regular, 30) # Для исполнителей под треком
        font_site_url = ImageFont.truetype(font_path_regular, 36)
    except IOError as e:
        logging.error(f"Не удалось загрузить шрифты: {e}. Используется шрифт по умолчанию.")
        # Это приведет к плохому виду, но предотвратит падение
        font_names = ImageFont.load_default()
        font_percentage_val = ImageFont.load_default()
        font_percentage_label = ImageFont.load_default()
        font_section_title = ImageFont.load_default()
        font_list_item_track = ImageFont.load_default()
        font_list_item_artist_detail = ImageFont.load_default()
        font_site_url = ImageFont.load_default()

    current_y = CONTENT_PADDING_Y_TOP

    # 1. Имена пользователей (без рамки, как заголовок)
    name_text = f"{name1} + {name2}"
    name_text_bbox = draw.textbbox((0,0), name_text, font=font_names, anchor="mt") # anchor "mt" для центрирования по верхней средней точке
    draw.text((WIDTH / 2, current_y), name_text, font=font_names, fill=ACCENT_COLOR, anchor="mt")
    current_y += (name_text_bbox[3] - name_text_bbox[1]) + 60 # Отступ

    # 2. Блок с процентом совместимости (в рамке)
    # Размеры текста внутри этого блока
    percentage_val_text = f"{percentage}%"
    percentage_val_bbox = draw.textbbox((0,0), percentage_val_text, font=font_percentage_val, anchor="mt")
    percentage_val_height = percentage_val_bbox[3] - percentage_val_bbox[1]

    percentage_label_text = "совместимость"
    percentage_label_bbox = draw.textbbox((0,0), percentage_label_text, font=font_percentage_label, anchor="mt")
    percentage_label_height = percentage_label_bbox[3] - percentage_label_bbox[1]
    
    percentage_block_content_height = percentage_val_height + 10 + percentage_label_height
    percentage_block_height = percentage_block_content_height + 2 * FRAME_PADDING_INTERNAL
    
    frame_percent_x0 = CONTENT_PADDING_X
    frame_percent_y0 = current_y
    frame_percent_x1 = WIDTH - CONTENT_PADDING_X
    frame_percent_y1 = current_y + percentage_block_height

    draw.rounded_rectangle(
        (frame_percent_x0, frame_percent_y0, frame_percent_x1, frame_percent_y1),
        radius=FRAME_CORNER_RADIUS,
        fill=FRAME_FILL_COLOR,
        outline=FRAME_OUTLINE_COLOR,
        width=FRAME_OUTLINE_WIDTH
    )

    # Текст внутри рамки процента
    y_text_in_frame = frame_percent_y0 + FRAME_PADDING_INTERNAL
    draw.text((WIDTH / 2, y_text_in_frame), percentage_val_text, font=font_percentage_val, fill=TEXT_COLOR_MAIN, anchor="mt")
    y_text_in_frame += percentage_val_height + 15 # небольшой отступ
    draw.text((WIDTH / 2, y_text_in_frame), percentage_label_text, font=font_percentage_label, fill=ACCENT_COLOR, anchor="mt")
    current_y = frame_percent_y1 + 40 # Отступ после рамки

    # --- Функция для отрисовки блока списка (треки/исполнители) ---
    def draw_list_block(title, items_data, item_type, start_y):
        # Рассчитываем высоту контента для рамки
        title_bbox = draw.textbbox((0,0), title, font=font_section_title)
        title_height = title_bbox[3] - title_bbox[1]
        
        list_content_height = 0
        num_items_to_draw = min(len(items_data), 3)
        if num_items_to_draw > 0:
            if item_type == "track":
                # Примерная высота для трека с исполнителем (2 строки)
                list_content_height = num_items_to_draw * (font_list_item_track.size + font_list_item_artist_detail.size * 0.8 + 15) # 15 отступ между элементами
                list_content_height -= 15 # Убираем лишний отступ после последнего
            else: # artist
                list_content_height = num_items_to_draw * (font_list_item_track.size + 15) # 15 отступ
                list_content_height -= 15

        block_content_height = title_height + 30 + list_content_height # 30 отступ от заголовка до списка
        if not items_data: # Если список пуст
             no_items_bbox = draw.textbbox((0,0), "Нет совпадений", font=font_list_item_track)
             block_content_height = title_height + 30 + (no_items_bbox[3] - no_items_bbox[1])


        block_height = block_content_height + 2 * FRAME_PADDING_INTERNAL
        
        frame_x0 = CONTENT_PADDING_X
        frame_y0 = start_y
        frame_x1 = WIDTH - CONTENT_PADDING_X
        frame_y1 = start_y + block_height

        draw.rounded_rectangle(
            (frame_x0, frame_y0, frame_x1, frame_y1),
            radius=FRAME_CORNER_RADIUS,
            fill=FRAME_FILL_COLOR,
            outline=FRAME_OUTLINE_COLOR, # Можно использовать другой цвет, например TEXT_COLOR_MUTED
            width=FRAME_OUTLINE_WIDTH
        )

        # Текст внутри рамки
        y_text_in_block = frame_y0 + FRAME_PADDING_INTERNAL
        title_actual_bbox = draw.textbbox((0,0), title, font=font_section_title, anchor="lt")
        draw.text((frame_x0 + FRAME_PADDING_INTERNAL, y_text_in_block), title, font=font_section_title, fill=ACCENT_COLOR, anchor="lt")
        y_text_in_block += (title_actual_bbox[3] - title_actual_bbox[1]) + 30

        if items_data:
            for i, item_data in enumerate(items_data[:3]):
                if item_type == "track":
                    parts = item_data.split(' - ', 1)
                    track_name = parts[-1]
                    item_text = f"{i + 1}. {track_name}"
                    draw.text((frame_x0 + FRAME_PADDING_INTERNAL + 20, y_text_in_block), item_text, font=font_list_item_track, fill=TEXT_COLOR_MAIN)
                    y_text_in_block += font_list_item_track.size * 0.8 # Сдвиг для исполнителя
                    if len(parts) > 1:
                        artist_name_detail = parts[0]
                        draw.text((frame_x0 + FRAME_PADDING_INTERNAL + 50, y_text_in_block), artist_name_detail, font=font_list_item_artist_detail, fill=TEXT_COLOR_MUTED)
                    y_text_in_block += font_list_item_artist_detail.size * 0.8 + 25 # Отступ до следующего элемента трека
                else: # artist
                    item_text = f"{i + 1}. {item_data}"
                    draw.text((frame_x0 + FRAME_PADDING_INTERNAL + 20, y_text_in_block), item_text, font=font_list_item_track, fill=TEXT_COLOR_MAIN)
                    y_text_in_block += font_list_item_track.size + 15 # Отступ до следующего элемента исполнителя
        else:
            draw.text((frame_x0 + FRAME_PADDING_INTERNAL + 20, y_text_in_block), "Нет совпадений", font=font_list_item_track, fill=TEXT_COLOR_MUTED)
        
        return frame_y1 # Возвращаем нижнюю координату рамки
    # --- Конец функции отрисовки блока списка ---

    # 3. Блок "Общие треки"
    top_tracks = data.get("top_tracks", [])
    current_y = draw_list_block("Общие треки:", top_tracks, "track", current_y)
    current_y += 40 # Отступ между блоками

    # 4. Блок "Общие исполнители"
    top_artists = data.get("top_artists", [])
    current_y = draw_list_block("Общие исполнители:", top_artists, "artist", current_y)

    # 5. URL сайта (внизу, вне основных рамок)
    site_url_text = "compare-music.ru"
    site_url_bbox = draw.textbbox((0,0), site_url_text, font=font_site_url, anchor="mb") # anchor "mb" для центрирования по нижней средней точке
    draw.text((WIDTH / 2, HEIGHT - 60), site_url_text, font=font_site_url, fill=TEXT_COLOR_MUTED, anchor="mb")

    # Сохранение
    output_dir = "/tmp"
    if not os.path.exists(output_dir) or not os.path.isdir(output_dir):
        logging.warning(f"Директория {output_dir} не найдена, сохраняю в текущую директорию.")
        output_dir = "." 
    
    safe_name1 = "".join(c if c.isalnum() else "_" for c in name1)
    safe_name2 = "".join(c if c.isalnum() else "_" for c in name2)
    output_filename = f"share_{safe_name1}_{safe_name2}.jpg"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        img.save(output_path, "JPEG", quality=90)
        logging.info(f"Image saved to {output_path}")
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        return None
        
    return output_path