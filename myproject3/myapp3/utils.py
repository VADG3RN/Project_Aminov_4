import os
import uuid
import json
from django.conf import settings

BOOK_FIELDS = [
    {"name": "author", "label": "Автор"},
    {"name": "title", "label": "Название"},
    {"name": "pages", "label": "Количество страниц"},
    {"name": "year", "label": "Год издания"},
]


def ensure_books_dir():
    folder = getattr(settings, 'BOOKS_JSON_DIR', None)
    if folder is None:
        folder = os.path.join(settings.BASE_DIR, 'books_json')
    os.makedirs(folder, exist_ok=True)
    return folder


def get_books_file_path():
    folder = ensure_books_dir()
    return os.path.join(folder, 'books.json')


def safe_filename(ext='.json'):
    return f"{uuid.uuid4().hex}{ext}"


def is_valid_book_obj(obj):
    if not isinstance(obj, dict):
        return False
    for field in BOOK_FIELDS:
        if field["name"] not in obj:
            return False
    return True


def is_valid_json_data_for_books(data):
    if isinstance(data, list):
        return all(is_valid_book_obj(item) for item in data)
    elif isinstance(data, dict):
        return is_valid_book_obj(data)
    return False


def save_book_to_main_file(book_dict):
    file_path = get_books_file_path()
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            arr = json.load(f)
            if not isinstance(arr, list):
                arr = []
        except Exception:
            arr = []
    arr.append(book_dict)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(arr, f, ensure_ascii=False, indent=4)
