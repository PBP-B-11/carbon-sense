import uuid

from django.conf import settings
from django.db import models


class Post(models.Model):
    CATEGORY_CHOICES = [
        ("tips", "Tips"),
        ("diskusi", "Diskusi"),
        ("berita", "Berita"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="tips")
    content = models.TextField()

    # Gnews
    news_title = models.CharField(max_length=255, blank=True)
    news_source = models.CharField(max_length=100, blank=True)
    news_url = models.URLField(blank=True)
    news_snippet = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author} ({self.category}): {self.content[:40]}"

    @property
    def has_news(self):
        return bool(self.news_title)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.post_id}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user} likes {self.post_id}"
