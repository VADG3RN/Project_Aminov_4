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
from django.urls import reverse

def book_form_view(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book_data = {
                'author': form.cleaned_data['author'].strip(),
                'title': form.cleaned_data['title'].strip(),
                'genre': (form.cleaned_data.get('genre') or '').strip(),
                'pages': form.cleaned_data.get('pages') or 0,
                'year': form.cleaned_data.get('year') or 0,
            }
            save_to = form.cleaned_data.get('save_to', 'file')
            if save_to == 'file':
                utils.save_book_to_main_file(book_data)
                messages.success(request, 'Книга успешно сохранена в JSON-файл.')
                return redirect('books:books_main')  # JSON — оставляем без параметра (по умолчанию = file)
            else:
                exists = Book.objects.filter(
                    author=book_data['author'],
                    title=book_data['title'],
                    year=book_data['year']
                ).exists()
                if exists:
                    messages.warning(request, 'Такая запись уже есть в базе данных — не добавлено.')
                else:
                    try:
                        Book.objects.create(**book_data)
                        messages.success(request, 'Книга успешно сохранена в базу данных.')
                    except IntegrityError:
                        messages.warning(request, 'Ошибка при сохранении (возможно дубликат).')
                return redirect(f"{reverse('books:books_main')}?source=db")
    else:
        form = BookForm()
    return render(request, 'myapp3/book_form.html', {'form': form})

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

def list_files_view(request):
    BOOKS_DIR = utils.BOOKS_DIR
    files = []
    try:
        for fn in sorted(os.listdir(BOOKS_DIR)):
            if fn.lower().endswith('.json'):
                path = os.path.join(BOOKS_DIR, fn)
                try:
                    size = os.path.getsize(path)
                except Exception:
                    size = 0
                files.append({'filename': fn, 'size': size})
    except FileNotFoundError:
        files = []
    if not files:
        return render(request, 'myapp3/file_list.html', {'no_files': 'Нет загруженных файлов.'})
    return render(request, 'myapp3/file_list.html', {'files': files})

def view_json_content(request, filename):
    if '/' in filename or '\\' in filename or '..' in filename:
        return HttpResponseBadRequest('Некорректное имя файла')
    path = os.path.join(utils.BOOKS_DIR, filename)
    if not os.path.exists(path):
        return HttpResponseBadRequest('Файл не найден')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except Exception:
        items = []
    return render(request, 'myapp3/json_content.html', {'items': items, 'filename': filename})

def upload_json_view(request):
    if request.method == 'POST':
        form = UploadJSONForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            name = utils.save_uploaded_file(f)
            messages.success(request, f'Файл загружен как {name}')
            return redirect('books:list_files')
    else:
        form = UploadJSONForm()
    return render(request, 'myapp3/upload_json.html', {'form': form})

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
            'genre': b.genre,
        })
    return JsonResponse({'results': data})

@require_POST
def ajax_delete_book(request, pk):
    try:
        b = get_object_or_404(Book, pk=pk)
        b.delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)

@require_POST
def ajax_update_book(request, pk):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    b = get_object_or_404(Book, pk=pk)
    author = payload.get('author', '').strip()
    title = payload.get('title', '').strip()
    genre = (payload.get('genre') or '').strip()
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
    b.genre = genre
    b.pages = pages
    b.year = year
    try:
        b.save()
    except IntegrityError:
        return JsonResponse({'status': 'error', 'error': 'Ошибка при сохранении (уникальность)'}, status=400)

    return JsonResponse({'status': 'ok'})
