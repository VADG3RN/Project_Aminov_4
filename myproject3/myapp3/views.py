import os
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import BookForm, UploadJSONForm
from . import utils


def book_form_view(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.cleaned_data.copy()
            utils.save_book_to_main_file(book)
            messages.success(request, 'Книга успешно сохранена в JSON.')
            return redirect('books:books_main')
    else:
        form = BookForm()
    return render(request, 'myapp3/book_form.html', {'form': form})


def upload_json_view(request):
    if request.method == 'POST':
        form = UploadJSONForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['file']
            title = form.cleaned_data.get('title') or uploaded.name
            fname = utils.safe_filename('.json')
            folder = utils.ensure_books_dir()
            path = os.path.join(folder, fname)

            with open(path, 'wb+') as dest:
                for chunk in uploaded.chunks():
                    dest.write(chunk)

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not utils.is_valid_json_data_for_books(data):
                    raise ValueError('JSON не соответствует структуре книги.')
            except Exception as e:
                os.remove(path)
                messages.error(request, f'Файл невалидный и был удалён: {e}')
                return redirect('books:upload_json')

            messages.success(request, f'Файл «{title}» успешно загружен.')
            return redirect('books:list_files')
    else:
        form = UploadJSONForm()
    return render(request, 'myapp3/upload_json.html', {'form': form})


def list_files_view(request):
    folder = utils.ensure_books_dir()
    files = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith('.json'):
            continue
        if fn in ('books.json', 'file_metadata.json'):
            continue
        path = os.path.join(folder, fn)
        stat = os.stat(path)
        files.append({'filename': fn, 'size': stat.st_size})
    context = {'files': files}
    if not files:
        context['no_files'] = 'JSON-файлов для просмотра не найдено.'
    return render(request, 'myapp3/file_list.html', context)


def view_json_content(request, filename):
    folder = utils.ensure_books_dir()
    safe_path = os.path.join(folder, filename)
    if not os.path.exists(safe_path):
        messages.error(request, 'Файл не найден.')
        return redirect('books:list_files')
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        messages.error(request, f'Ошибка при чтении JSON: {e}')
        return redirect('books:list_files')

    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        messages.error(request, 'Файл содержит неизвестную структуру.')
        return redirect('books:list_files')

    return render(request, 'myapp3/json_content.html', {'items': items, 'filename': filename})


def main_books_view(request):
    path = utils.get_books_file_path()
    books = []
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                books = json.load(f)
                if not isinstance(books, list):
                    books = []
        except Exception:
            books = []
    return render(request, 'myapp3/books_main_list.html', {'books': books})
