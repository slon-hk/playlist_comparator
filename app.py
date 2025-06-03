import os
import logging
from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template, send_file
from image_generator import generate_image
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from yandex_music import Client

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
app = Flask(__name__)
comparison_cache = {}  # Для хранения результатов сравнения

# --- Spotify Setup ---
client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

sp = None
if client_id and client_secret:
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Spotify Helpers ---
def get_spotify_playlist_id(url):
    parts = url.split("/")
    for i, part in enumerate(parts):
        if part == "playlist":
            return parts[i + 1].split("?")[0]
    return None

def fetch_spotify_tracks(url):
    playlist_id = get_spotify_playlist_id(url)
    if not playlist_id:
        raise ValueError("Некорректная ссылка на плейлист Spotify.")

    tracks = []
    offset = 0
    while True:
        results = sp.playlist_items(playlist_id, offset=offset,
            fields='items.track(id,name,artists(name)),next')
        if not results['items']:
            break
        for item in results['items']:
            track = item['track']
            if not track:
                continue
            title = track['name']
            artists = [artist['name'] for artist in track['artists']]
            tracks.append({'title': title, 'artists': artists})
        if not results['next']:
            break
        offset += 100
    return tracks

# --- Yandex Helpers ---
YANDEX_TOKEN = os.getenv('YANDEX_MUSIC_TOKEN')
def fetch_yandex_tracks(url: str):
    if not YANDEX_TOKEN:
        raise RuntimeError("Токен Яндекс Музыки не найден в переменных окружения (YANDEX_MUSIC_TOKEN)")

    client = Client(YANDEX_TOKEN).init()

    # Парсим ссылку
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if len(parts) < 4 or parts[0] != 'users' or parts[2] != 'playlists':
        raise ValueError("Некорректная ссылка на плейлист Яндекс Музыки.")

    username = parts[1]
    playlist_id = int(parts[3].split('?')[0])

    # Получаем плейлист
    playlist = client.users_playlists(kind=playlist_id, user_id=username)

    # Получаем список объектов TrackShort
    track_shorts = playlist.fetch_tracks()

    tracks = []
    for track_short in track_shorts:
        track = track_short.track
        if not track:
            continue
        title = track.title
        artists = [artist.name for artist in track.artists]
        tracks.append({
            'title': title,
            'artists': artists
        })

    return tracks

# --- Сравнение ---
def get_top_artists(tracks, limit=5):
    """
    Подсчитывает частоту встречаемости исполнителей и возвращает топ самых частых
    
    Args:
        tracks (list): Список треков, где каждый трек - словарь с ключом 'artists'
        limit (int): Количество исполнителей для возврата
    
    Returns:
        list: Список кортежей (исполнитель, количество появлений)
    """
    artist_counts = {}
    
    for track in tracks:
        if isinstance(track, dict) and 'artists' in track:
            for artist in track['artists']:
                if isinstance(artist, str):
                    artist = artist.lower().strip()
                    artist_counts[artist] = artist_counts.get(artist, 0) + 1
    
    # Сортируем по убыванию количества и берем топ limit
    sorted_artists = sorted(artist_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]
    return sorted_artists

def get_top_artists_from_common_tracks(common_tracks, limit=5):
    artist_counts = {}
    
    for track in common_tracks:
        artists = track.split(' - ')[0].split(' & ')
        for artist in artists:
            artist = artist.lower().strip()
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
    
    # Сортируем по убыванию количества и берем топ limit
    sorted_artists = sorted(artist_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]
    return sorted_artists

def calculate_compatibility(tracks1, tracks2):
    if not tracks1 or not tracks2:
        return {
            "percentage": 0,
            "common_tracks": [],
            "common_artists": [],
            "message": "Один или оба плейлиста пусты."
        }

    # Сравнение треков по названию и артистам
    def normalize(s):
        return s.strip().lower() if isinstance(s, str) else ""

    def process_track(track):
        if not isinstance(track, dict):
            return None
        title = track.get('title')
        artists = track.get('artists', [])
        
        if not title or not artists:
            return None
            
        return (normalize(title), tuple(sorted(map(normalize, artists))))

    # Фильтруем невалидные треки и создаем множества
    valid_tracks1 = [t for t in (process_track(track) for track in tracks1) if t is not None]
    valid_tracks2 = [t for t in (process_track(track) for track in tracks2) if t is not None]

    set1 = set(valid_tracks1)
    set2 = set(valid_tracks2)
    common_tracks = set1.intersection(set2)

    # Формируем список общих треков и одновременно собираем статистику по исполнителям
    formatted_common_tracks = []
    artist_counts = {}

    for title, artists in common_tracks:
        track_string = f"{' & '.join(artists)} - {title}"
        formatted_common_tracks.append(track_string)
        
        # Подсчитываем исполнителей сразу при обработке общих треков
        for artist in artists:
            artist = artist.lower().strip()
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

    # Сортируем исполнителей по количеству появлений
    top_artists = sorted(artist_counts.items(), key=lambda x: (-x[1], x[0]))[:5]

    # Процент совместимости
    total_unique_tracks = len(set1.union(set2))
    percent = round((len(common_tracks) / total_unique_tracks) * 100, 2) if total_unique_tracks else 0.0

    return {
        "percentage": percent,
        "common_tracks": formatted_common_tracks,
        "common_tracks_count": len(common_tracks),
        "common_artists": [artist for artist, _ in top_artists],
        "common_artists_count": len(top_artists),
        "artist_frequencies": {artist: count for artist, count in top_artists}
    }

# --- API Route ---
app = Flask(__name__)

def detect_platform(url):
    if "spotify" in url:
        return "spotify"
    elif "yandex" in url:
        return "yandex"
    else:
        return "unknown"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compare', methods=['POST'])
def compare():
    data = request.get_json()
    
    # Проверяем наличие обязательных полей
    if not data or 'playlist1_url' not in data or 'playlist2_url' not in data:
        logging.warning("Отсутствуют обязательные поля в запросе")
        return jsonify({'error': 'Необходимо указать оба URL плейлистов'}), 400

    playlist1_url = data['playlist1_url']
    playlist2_url = data['playlist2_url']

    # Проверяем, что URL не None и не пустые
    if not isinstance(playlist1_url, str) or not isinstance(playlist2_url, str):
        logging.warning("URL плейлистов должны быть строками")
        return jsonify({'error': 'URL плейлистов должны быть строками'}), 400

    playlist1_url = playlist1_url.strip()
    playlist2_url = playlist2_url.strip()
    
    if not playlist1_url or not playlist2_url:
        logging.warning("Получены пустые URL")
        return jsonify({'error': 'URL плейлистов не могут быть пустыми'}), 400

    logging.info(f"Получены URL: playlist1 = {playlist1_url}, playlist2 = {playlist2_url}")

    if not playlist1_url or not playlist2_url:
        logging.warning("Один из URL не передан.")
        return jsonify({'error': 'Не переданы оба URL плейлистов'}), 400

    try:
        platform1 = detect_platform(playlist1_url)
        platform2 = detect_platform(playlist2_url)

        logging.info(f"Определены платформы: playlist1 = {platform1}, playlist2 = {platform2}")

        if platform1 == 'spotify':
            if not sp:
                logging.error("Spotify API не инициализирован.")
                return jsonify({'error': 'Spotify API не инициализирован'}), 500
            tracks1 = fetch_spotify_tracks(playlist1_url)
        elif platform1 == 'yandex':
            tracks1 = fetch_yandex_tracks(playlist1_url)
        else:
            return jsonify({'error': f'Неизвестный формат плейлиста 1: {playlist1_url}'}), 400

        if platform2 == 'spotify':
            if not sp:
                logging.error("Spotify API не инициализирован.")
                return jsonify({'error': 'Spotify API не инициализирован'}), 500
            tracks2 = fetch_spotify_tracks(playlist2_url)
        elif platform2 == 'yandex':
            tracks2 = fetch_yandex_tracks(playlist2_url)
        else:
            return jsonify({'error': f'Неизвестный формат плейлиста 2: {playlist2_url}'}), 400

        logging.info(f"Получено треков: playlist1 = {len(tracks1)}, playlist2 = {len(tracks2)}")

        result = calculate_compatibility(tracks1, tracks2)
        
        # Сохраняем результат в кэш
        cache_key = f"{playlist1_url}:{playlist2_url}"
        comparison_cache[cache_key] = result

        logging.debug(f"Результат сравнения: {result}")

        return jsonify({
            'percentage': result.get('percentage', 0),
            'message': result.get('message', ''),
            'playlist1_track_count': len(tracks1),
            'playlist2_track_count': len(tracks2),
            'common_tracks_count': result.get('common_tracks_count', 0),
            'common_tracks_details': [
                {'name': item.split(' - ')[1], 'artists': item.split(' - ')[0].split(' & ')}
                for item in result.get('common_tracks', [])
            ],
            'common_artists_count': result.get('common_artists_count', 0),
            'common_artists_details': result.get('common_artists', []),
            'top_tracks': result.get('common_tracks', [])[:5],  # Send full track strings
            'top_artists': result.get('common_artists', [])[:5]
        })

    except Exception as e:
        logging.exception("Ошибка при сравнении плейлистов")
        return jsonify({'error': f'Ошибка при сравнении: {str(e)}'}), 500

@app.route('/api/share-image', methods=['POST'])
def share_image():
    data = request.get_json()
    logging.debug(f"Received data in share-image: {data}")
    
    name1 = data.get("name1")
    name2 = data.get("name2")
    percentage = data.get("percentage")
    playlist1_url = data.get("playlist1_url")
    playlist2_url = data.get("playlist2_url")
    
    if not all([name1, name2, percentage is not None, playlist1_url, playlist2_url]):
        return jsonify({"error": "Недостаточно данных"}), 400
    
    try:
        # Используем только кэшированные данные
        cache_key = f"{playlist1_url}:{playlist2_url}"
        cached_result = comparison_cache.get(cache_key)
        
        if not cached_result:
            return jsonify({"error": "Данные сравнения не найдены. Пожалуйста, сначала выполните сравнение."}), 404
            
        formatted_data = {
            "top_tracks": cached_result.get("common_tracks", [])[:3],
            "top_artists": cached_result.get("common_artists", [])[:3]
        }

        logging.debug(f"Using cached data for image generation: {formatted_data}")
        
        img_path = generate_image(name1, name2, percentage, formatted_data)
        return send_file(img_path, mimetype='image/jpeg')

    except Exception as e:
        logging.exception("Ошибка при генерации изображения")
        return jsonify({'error': f'Ошибка при генерации изображения: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)