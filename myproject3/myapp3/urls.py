from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('add/', views.book_form_view, name='book_form'),
    path('books/', views.main_books_view, name='books_main'),
    path('upload/', views.upload_json_view, name='upload_json'),
    path('files/', views.list_files_view, name='list_files'),
    path('files/<str:filename>/', views.view_json_content, name='view_json'),
]
