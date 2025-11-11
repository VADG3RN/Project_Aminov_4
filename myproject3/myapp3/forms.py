from django import forms
import json

class BookForm(forms.Form):
    author = forms.CharField(label='Автор', max_length=200)
    title = forms.CharField(label='Название', max_length=300)
    genre = forms.CharField(label='Жанр', max_length=100, required=False)
    pages = forms.IntegerField(label='Количество страниц', min_value=1, required=False)
    year = forms.IntegerField(label='Год издания', min_value=1, required=False)
    save_to = forms.ChoiceField(
        label='Куда сохранить',
        choices=(('file', 'Файл (JSON)'), ('db', 'База данных (SQLite)')),
        widget=forms.RadioSelect,
        initial='file'
    )

class UploadJSONForm(forms.Form):
    file = forms.FileField(label='JSON-файл')

    def clean_file(self):
        f = self.cleaned_data['file']
        name = f.name.lower()
        if not name.endswith('.json'):
            raise forms.ValidationError('Только файлы с расширением .json разрешены.')
        sample = f.read(4096)
        f.seek(0)
        try:
            s = sample.decode('utf-8', errors='ignore').strip()
            if not (s.startswith('{') or s.startswith('[')):
                raise ValueError('Не похоже на JSON')
            # частичная parse для валидации
            json.loads(s if len(s) < 2000 else s[:2000])
        except Exception:
            raise forms.ValidationError('Файл не является корректным JSON (проверка по первым байтам).')
        return f
