import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db import IntegrityError, models
from .forms import BookForm, UploadJSONForm
from . import utils
from .models import Book

# Добавление книги (в файл или БД)
def book_form_view(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book_data = {k: v for k, v in form.cleaned_data.items() if k not in ('save_to',)}
            save_to = form.cleaned_data.get('save_to', 'file')

            if save_to == 'file':
                utils.save_book_to_main_file(book_data)
                messages.success(request, 'Книга успешно сохранена в JSON.')
            else:
                author = book_data.get('author')
                title = book_data.get('title')
                year = book_data.get('year')
                try:
                    exists = Book.objects.filter(author=author, title=title, year=year).exists()
                    if exists:
                        messages.warning(request, 'Такая запись уже существует в базе данных — не добавлено.')
                    else:
                        Book.objects.create(
                            author=author,
                            title=title,
                            pages=book_data.get('pages') or 0,
                            year=book_data.get('year') or 0,
                        )
                        messages.success(request, 'Книга успешно сохранена в базе данных.')
                except IntegrityError:
                    messages.warning(request, 'Такая запись уже существует (нарушение уникальности).')

            return redirect('books:books_main')
    else:
        form = BookForm()

    return render(request, 'myapp3/book_form.html', {'form': form})

# Загрузка JSON файла
def upload_json_view(request):
    if request.method == 'POST':
        form = UploadJSONForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['file']
            title = form.cleaned_data.get('title') or uploaded.name
            fname = utils.safe_filename('.json')
            folder = utils.ensure_books_dir()
            path = os.path.join(folder, fname)

            # сохраняем файл на сервер
            with open(path, 'wb+') as dest:
                for chunk in uploaded.chunks():
                    dest.write(chunk)

            # проверяем, что это правильный JSON
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

# Просмотр всех книг (из файла или из БД)
def main_books_view(request):
    source = request.GET.get('source', 'file')
    context = {'source': source}

    if source == 'db':
        books = Book.objects.all()
        context['books'] = books
    else:
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
        context['books'] = books

    return render(request, 'myapp3/books_main_list.html', context)

# Отображает список всех JSON-файлов с книгами
def list_files_view(request):
    folder = utils.ensure_books_dir()
    files = [f for f in os.listdir(folder) if f.endswith('.json')]

    if not files:
        messages.info(request, 'На сервере нет JSON-файлов.')
        return render(request, 'myapp3/list_files.html', {'files': []})

    file_info = []
    for filename in files:
        path = os.path.join(folder, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else 1
        except Exception:
            count = 0
        file_info.append({'name': filename, 'count': count})

    return render(request, 'myapp3/list_files.html', {'files': file_info})

# Открывает и показывает содержимое выбранного JSON-файла
def view_json_content(request, filename):
    folder = utils.ensure_books_dir()
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        messages.error(request, f'Файл {filename} не найден.')
        return redirect('books:list_files')

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        messages.error(request, f'Ошибка при чтении файла: {e}')
        return redirect('books:list_files')

    # Проверяем структуру
    if not isinstance(data, list):
        messages.warning(request, f'Файл {filename} не содержит список книг.')
        data = [data]

    return render(request, 'myapp3/view_json.html', {
        'filename': filename,
        'books': data
    })


# AJAX-поиск по БД
def ajax_search_books(request):
    """Возвращает JSON-список книг из БД, по фильтру q (поиск по author/title)."""
    q = request.GET.get('q', '').strip()
    qs = Book.objects.all()

    if q:
        qs = qs.filter(
            models.Q(author__icontains=q) |
            models.Q(title__icontains=q)
        )

    data = []
    for b in qs:
        data.append({
            'id': b.id,
            'author': b.author,
            'title': b.title,
            'pages': b.pages,
            'year': b.year,
        })

    return JsonResponse({'results': data})

# AJAX-удаление книги
@require_POST
def ajax_delete_book(request, pk):
    try:
        b = get_object_or_404(Book, pk=pk)
        b.delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)

# AJAX-редактирование книги
@require_POST
def ajax_update_book(request, pk):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    b = get_object_or_404(Book, pk=pk)

    author = payload.get('author', '').strip()
    title = payload.get('title', '').strip()
    try:
        pages = int(payload.get('pages', 0))
        year = int(payload.get('year', 0))
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'error': 'pages и year должны быть числами'}, status=400)

    if not author or not title:
        return JsonResponse({'status': 'error', 'error': 'author и title обязательны'}, status=400)

    dup = Book.objects.filter(author=author, title=title, year=year).exclude(pk=b.pk).exists()
    if dup:
        return JsonResponse({'status': 'error', 'error': 'Дублирующая запись уже существует'}, status=400)

    b.author = author
    b.title = title
    b.pages = pages
    b.year = year

    try:
        b.save()
    except IntegrityError:
        return JsonResponse({'status': 'error', 'error': 'Ошибка при сохранении (уникальность)'}, status=400)

    return JsonResponse({'status': 'ok'})
