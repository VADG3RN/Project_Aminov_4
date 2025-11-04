import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from .forms import BookForm, UploadJSONForm
from . import utils
from .models import Book

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
                        book_obj = Book.objects.create(
                            author=author,
                            title=title,
                            pages=book_data.get('pages') or 0,
                            year=book_data.get('year') or 0,
                            genre=book_data.get('genre', '')
                        )
                        messages.success(request, 'Книга успешно сохранена в базе данных.')
                except IntegrityError:
                    messages.warning(request, 'Такая запись уже существует (нарушение уникальности).')
            return redirect('books:books_main')
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

    from django.views.decorators.csrf import csrf_exempt

def ajax_search_books(request):
    """Возвращает JSON-список книг из БД, по фильтру q (поиск по author/title)."""
    q = request.GET.get('q', '').strip()
    qs = Book.objects.all()
    if q:
        qs = qs.filter(
            models.Q(author__icontains=q) |
            models.Q(title__icontains=q) |
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
    # Ожидаем JSON в теле запроса с новыми полями
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    b = get_object_or_404(Book, pk=pk)
    # простая валидация: проверяем текстовые поля не пустые и числа положительные
    author = payload.get('author', '').strip()
    title = payload.get('title', '').strip()
    try:
        pages = int(payload.get('pages', 0))
        year = int(payload.get('year', 0))
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'error': 'pages и year должны быть числами'}, status=400)

    if not author or not title:
        return JsonResponse({'status': 'error', 'error': 'author и title обязательны'}, status=400)

    # проверка дубликата: если меняем на данные, которые уже есть у другой записи
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
    

