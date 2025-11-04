from django import forms
from .utils import BOOK_FIELDS
import datetime

CURRENT_YEAR = datetime.date.today().year


def create_dynamic_book_form():
    fields = {}
    for f in BOOK_FIELDS:
        name = f["name"]
        label = f["label"]

        # создаём подходящее поле в зависимости от имени
        if name == "pages":
            field = forms.IntegerField(label=label, min_value=1)
        elif name == "year":
            field = forms.IntegerField(label=label, min_value=1, max_value=CURRENT_YEAR)
        else:
            field = forms.CharField(label=label, max_length=200)

        fields[name] = field

    return type("BookForm", (forms.Form,), fields)


BookForm = create_dynamic_book_form()


class UploadJSONForm(forms.Form):
    title = forms.CharField(label='Название файла (для списка)', required=False, max_length=200)
    file = forms.FileField(label='JSON-файл')

    def clean_file(self):
        f = self.cleaned_data['file']
        name = f.name.lower()
        if not name.endswith('.json'):
            raise forms.ValidationError('Разрешены только файлы .json')
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Файл слишком большой (макс 5 MB).')
        return f
