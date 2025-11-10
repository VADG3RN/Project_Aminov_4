from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('author', 'title', 'genre', 'pages', 'year', 'created')
    search_fields = ('author', 'title', 'genre')
