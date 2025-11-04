from django.db import models

class Book(models.Model):
    # поля должны соответствовать BOOK_FIELDS или их расширению
    author = models.CharField(max_length=200)
    title = models.CharField(max_length=300)
    pages = models.PositiveIntegerField()
    year = models.PositiveIntegerField()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        # уникальность: не позволяем точные дубли по основным полям
        unique_together = (('author', 'title', 'year'),)
        ordering = ['-created']

    def __str__(self):
        return f"{self.author} — {self.title} ({self.year})"
