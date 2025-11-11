from django.db import models
from django.utils import timezone

class Book(models.Model):
    author = models.CharField(max_length=200)
    title = models.CharField(max_length=300)
    genre = models.CharField(max_length=100, blank=True, default='') 
    pages = models.PositiveIntegerField(default=0)
    year = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('author', 'title', 'year')
        ordering = ['author', 'title']

    def __str__(self):
        return f"{self.author} — {self.title} ({self.year})"
