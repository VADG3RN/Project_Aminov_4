from django.db import models
from django.utils import timezone

class Book(models.Model):
    author = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100, blank=True)  # ← добавить это
    pages = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('author', 'title', 'year')
        ordering = ['author']


    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('author', 'title', 'year'),)
        ordering = ['-created']

    def __str__(self):
        return f"{self.author} — {self.title} ({self.year})"
