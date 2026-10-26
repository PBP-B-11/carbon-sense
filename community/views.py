from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Like, Post
from .news import fetch_news, find_article


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _feed_posts(user):
    posts = Post.objects.select_related("author").annotate(
        like_count=Count("likes", distinct=True),
        comment_count=Count("comments", distinct=True),
    )
    if user.is_authenticated:
        posts = posts.annotate(
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user))
        )
    return posts


def _post_card_json(request, post):
    post = _feed_posts(request.user).get(pk=post.pk)
    html = render_to_string("community/_post_card.html", {"post": post}, request=request)
    return JsonResponse({"html": html})


def index(request):
    posts = _feed_posts(request.user)

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
        if _is_ajax(request):
            return _post_card_json(request, post)
    elif _is_ajax(request):
        return JsonResponse({"error": "Postingan tidak valid."}, status=400)
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
        if _is_ajax(request):
            return _post_card_json(request, post)
    elif _is_ajax(request):
        return JsonResponse({"error": "Perubahan tidak valid."}, status=400)
    else:
        messages.error(request, "Perubahan tidak valid.")
    return redirect("community:index")


@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()

    if _is_ajax(request):
        return JsonResponse({"deleted": True})
    return redirect("community:index")


@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()

    if _is_ajax(request):
        return JsonResponse({"liked": created, "count": post.likes.count()})
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
        if _is_ajax(request):
            html = render_to_string(
                "community/_comment.html", {"comment": comment}, request=request
            )
            return JsonResponse({"html": html, "count": post.comments.count()})
    elif _is_ajax(request):
        return JsonResponse({"error": "Komentar tidak valid."}, status=400)
    return redirect("community:post_detail", pk=post.pk)


@login_required
@require_POST
def share_news(request):
    article = find_article(request.POST.get("url", ""))
    if article is None:
        if _is_ajax(request):
            return JsonResponse({"error": "Berita tidak ditemukan atau sudah kedaluwarsa."}, status=400)
        messages.error(request, "Berita tidak ditemukan atau sudah kedaluwarsa.")
        return redirect("community:index")

    post = Post.objects.create(
        author=request.user,
        category="berita",
        content=request.POST.get("content", "").strip(),
        news_title=article["title"][:255],
        news_source=article["source"][:100],
        news_url=article["url"],
        news_snippet=article["snippet"],
    )

    if _is_ajax(request):
        return _post_card_json(request, post)
    return redirect("community:index")
