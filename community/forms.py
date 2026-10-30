from django import forms

from .models import Comment, Post

POST_MAX_LENGTH = 1000
COMMENT_MAX_LENGTH = 500


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


class NormalizedCharField(forms.CharField):
    """Browser mengirim baris baru sebagai \\r\\n (2 karakter) padahal `maxlength` di browser
    menghitungnya 1. Disamakan dulu sebelum panjangnya divalidasi."""

    def to_python(self, value):
        return normalize_newlines(super().to_python(value))


class PostForm(forms.ModelForm):
    content = NormalizedCharField(max_length=POST_MAX_LENGTH, widget=forms.Textarea)

    class Meta:
        model = Post
        fields = ["category", "content"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Post berita boleh tanpa caption, dan kategorinya tidak bisa diubah
        if not self.instance._state.adding and self.instance.has_news:
            self.fields["content"].required = False
            self.fields["category"].disabled = True


class CommentForm(forms.ModelForm):
    content = NormalizedCharField(max_length=COMMENT_MAX_LENGTH, widget=forms.Textarea)

    class Meta:
        model = Comment
        fields = ["content"]
