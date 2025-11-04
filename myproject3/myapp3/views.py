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

# 1. Форма: сохранить в файл или БД
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
                year = book_data.get('year') or 0
                # проверка дубликата до создания
                exists = Book.objects.filter(author=author, title=title, year=year).exists()
                if exists:
                    messages.warning(request, 'Такая запись уже существует в базе данных — не добавлено.')
                else:
                    try:
                        Book.objects.create(
                            author=author,
                            title=title,
                            pages=book_data.get('pages') or 0,
                            year=year,
                            genre=book_data.get('genre', '')
                        )
                        messages.success(request, 'Книга успешно сохранена в базе данных.')
                    except IntegrityError:
                        messages.warning(request, 'Такая запись уже существует (нарушение уникальности).')

            return redirect('books:books_main')
    else:
        form = BookForm()
    return render(request, 'myapp3/book_form.html', {'form': form})


# 2. Просмотр: источник — file или db
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


# 3. upload JSON (как было)
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


# 4. list files (как было в старом проекте)
def list_files_view(request):
    folder = utils.ensure_books_dir()
    files = []
    try:
        files = [fn for fn in sorted(os.listdir(folder)) if fn.lower().endswith('.json')]
    except Exception:
        files = []
    # не показывать основной файл books.json в списке загруженных (опционально)
    files = [fn for fn in files if fn != 'books.json']
    if not files:
        return render(request, 'myapp3/file_list.html', {'files': [], 'no_files': 'JSON-файлов для просмотра не найдено.'})
    file_info = []
    for fn in files:
        path = os.path.join(folder, fn)
        try:
            stat = os.stat(path)
            file_info.append({'filename': fn, 'size': stat.st_size})
        except Exception:
            file_info.append({'filename': fn, 'size': 0})
    return render(request, 'myapp3/file_list.html', {'files': file_info})


# 5. view json content (open specific uploaded file)
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
        messages.error(request, f'Ошибка чтения файла: {e}')
        return redirect('books:list_files')
    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        messages.error(request, 'Формат файла не распознан.')
        return redirect('books:list_files')
    return render(request, 'myapp3/view_json.html', {'items': items, 'filename': filename})


# 6. AJAX: поиск (DB)
def ajax_search_books(request):
    q = request.GET.get('q', '').strip()
    qs = Book.objects.all()
    if q:
        qs = qs.filter(
            models.Q(author__icontains=q) |
            models.Q(title__icontains=q) |
            models.Q(genre__icontains=q)
        )
    data = []
    for b in qs:
        data.append({
            'id': b.id,
            'author': b.author,
            'title': b.title,
            'pages': b.pages,
            'year': b.year,
            'genre': b.genre or '',
        })
    return JsonResponse({'results': data})


# 7. AJAX: delete
@require_POST
def ajax_delete_book(request, pk):
    try:
        b = get_object_or_404(Book, pk=pk)
        b.delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


# 8. AJAX: update
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
    b.genre = payload.get('genre', '')
    try:
        b.save()
    except IntegrityError:
        return JsonResponse({'status': 'error', 'error': 'Ошибка при сохранении (уникальность)'}, status=400)
    return JsonResponse({'status': 'ok'})
