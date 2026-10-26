from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Like, Post
from .news import fetch_news, find_article


def index(request):
    posts = Post.objects.select_related("author").annotate(
        like_count=Count("likes", distinct=True),
        comment_count=Count("comments", distinct=True),
    )
    if request.user.is_authenticated:
        posts = posts.annotate(
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=request.user))
        )

    return render(
        request,
        "community/community.html",
        {"posts": posts, "form": PostForm(), "news": fetch_news()},
    )


@login_required
@require_POST
def create_post(request):
    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
    else:
        messages.error(request, "Postingan tidak valid.")
    return redirect("community:index")


@login_required
@require_POST
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    form = PostForm(request.POST, instance=post)
    if form.is_valid():
        form.save()
    else:
        messages.error(request, "Perubahan tidak valid.")
    return redirect("community:index")


@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    return redirect("community:index")


@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return redirect(request.POST.get("next") or "community:index")


def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author").annotate(like_count=Count("likes")),
        pk=pk,
    )
    comments = post.comments.select_related("author")
    return render(
        request,
        "community/post_detail.html",
        {"post": post, "comments": comments, "form": CommentForm()},
    )


@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect("community:post_detail", pk=post.pk)


@login_required
@require_POST
def share_news(request):
    article = find_article(request.POST.get("url", ""))
    if article is None:
        messages.error(request, "Berita tidak ditemukan atau sudah kedaluwarsa.")
        return redirect("community:index")

    Post.objects.create(
        author=request.user,
        category="berita",
        content=request.POST.get("content", "").strip(),
        news_title=article["title"][:255],
        news_source=article["source"][:100],
        news_url=article["url"],
        news_snippet=article["snippet"],
    )
    return redirect("community:index")
