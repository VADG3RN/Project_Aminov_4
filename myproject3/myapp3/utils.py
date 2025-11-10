import os
import json
from django.conf import settings
from datetime import datetime
import uuid

# Каталог для json-файлов (можно задать BOOKS_JSON_DIR в settings.py)
BOOKS_DIR = getattr(settings, 'BOOKS_JSON_DIR', os.path.join(settings.BASE_DIR, 'books_json'))
os.makedirs(BOOKS_DIR, exist_ok=True)

MAIN_FILE = os.path.join(BOOKS_DIR, 'books_main.json')

def get_books_file_path():
    return MAIN_FILE

def save_book_to_main_file(book_dict):
    path = get_books_file_path()
    data = []
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except Exception:
            data = []
    entry = book_dict.copy()
    entry['saved_at'] = datetime.utcnow().isoformat()
    data.append(entry)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_uploaded_file(file_obj):
    # генерируем безопасное имя — timestamp + uuid
    name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.json"
    path = os.path.join(BOOKS_DIR, name)
    with open(path, 'wb') as dest:
        for chunk in file_obj.chunks():
            dest.write(chunk)
    return name
