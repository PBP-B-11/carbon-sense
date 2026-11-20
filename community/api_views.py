from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from carbon_sense.api import form_data, paginate, validate_form

from .forms import CommentForm, PostForm, ShareNewsForm
from .models import Comment, Like, Post
from .news import fetch_news, find_article
from .views import (
    COMMENT_COOLDOWN,
    COMMENT_PAGE_SIZE,
    PAGE_SIZE,
    POST_COOLDOWN,
    _feed_posts,
    cooldown_wait,
    create_news_post,
    filter_feed,
)


class PostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username")
    like_count = serializers.IntegerField()
    comment_count = serializers.IntegerField()
    is_liked = serializers.BooleanField(default=False)

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "category",
            "content",
            "news_title",
            "news_source",
            "news_url",
            "news_snippet",
            "created_at",
            "updated_at",
            "like_count",
            "comment_count",
            "is_liked",
        )


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username")

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "content", "created_at")


def enforce_cooldown(user, model, cooldown):
    wait = cooldown_wait(user, model, cooldown)
    if wait:
        raise Throttled(wait=wait)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def posts(request):
    if request.method == "POST":
        enforce_cooldown(request.user, Post, POST_COOLDOWN)
        form = PostForm(form_data(request))
        validate_form(form)
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return Response(
            PostSerializer(_feed_posts(request.user).get(pk=post.pk)).data, status=201
        )
    feed, _, _, _ = filter_feed(request.user, request.query_params)
    return paginate(request, feed, PostSerializer, PAGE_SIZE)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_detail(request, pk):
    posts = _feed_posts(request.user)
    if request.method != "GET":
        posts = posts.filter(author=request.user)
    post = get_object_or_404(posts, pk=pk)
    if request.method == "DELETE":
        post.delete()
        return Response(status=204)
    if request.method == "PUT":
        form = PostForm(form_data(request), instance=post)
        validate_form(form)
        form.save()
    return Response(PostSerializer(post).data)


@api_view(["PUT", "DELETE"])
def like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    likes = Like.objects.filter(post=post, user=request.user)
    liked = request.method == "PUT"
    if liked:
        likes.get_or_create(post=post, user=request.user)
    else:
        likes.delete()
    return Response({"liked": liked, "count": post.likes.count()})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def comments(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        enforce_cooldown(request.user, Comment, COMMENT_COOLDOWN)
        form = CommentForm(form_data(request))
        validate_form(form)
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return Response(CommentSerializer(comment).data, status=201)
    queryset = post.comments.select_related("author").order_by("-created_at", "-pk")
    return paginate(request, queryset, CommentSerializer, COMMENT_PAGE_SIZE)


@api_view(["PUT", "DELETE"])
def comment_detail(request, pk):
    comment = get_object_or_404(Comment, pk=pk, author=request.user)
    if request.method == "DELETE":
        comment.delete()
        return Response(status=204)
    form = CommentForm(form_data(request), instance=comment)
    validate_form(form)
    return Response(CommentSerializer(form.save()).data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def news(request):
    return Response({"results": fetch_news()})


@api_view(["POST"])
def share_news(request):
    enforce_cooldown(request.user, Post, POST_COOLDOWN)
    data = form_data(request)
    article = find_article(data.get("url", ""))
    if article is None:
        raise ValidationError(
            {"url": ["Berita tidak ditemukan atau sudah kedaluwarsa."]}
        )
    fields = validate_form(ShareNewsForm(data))
    post = create_news_post(request.user, article, fields["content"])
    return Response(
        PostSerializer(_feed_posts(request.user).get(pk=post.pk)).data, status=201
    )
