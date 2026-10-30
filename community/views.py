from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_headers

from .assets import community_assets
from .forms import (
    COMMENT_MAX_LENGTH,
    POST_MAX_LENGTH,
    CommentForm,
    PostForm,
    ShareNewsForm,
)
from .models import Comment, Like, Post
from .news import fetch_news, find_article


PAGE_SIZE = 10
COMMENT_PAGE_SIZE = 20
CATEGORIES = {value for value, _ in Post.CATEGORY_CHOICES}
SORTS = {"new", "old", "popular", "komen"}
SEARCH_MAX_LENGTH = 100


def _is_ajax(request):
    """Request dari fetch() di JavaScript; dijawab JSON, bukan redirect."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _fail(request, message, to="community:index", **kwargs):
    """Respons gagal: JSON 400 untuk AJAX, atau pesan flash lalu redirect."""
    if _is_ajax(request):
        return JsonResponse({"error": message}, status=400)
    messages.error(request, message)
    return redirect(to, **kwargs)


def _page_json(request, paginator, render_page):
    """Satu halaman hasil paginasi sebagai JSON; halaman di luar jangkauan dikembalikan kosong."""
    try:
        page = paginator.page(request.GET.get("page", 1))
    except (EmptyPage, PageNotAnInteger):
        return JsonResponse({"html": "", "has_next": False, "next_page": None})
    return JsonResponse(
        {
            "html": render_page(page),
            "has_next": page.has_next(),
            "next_page": page.next_page_number() if page.has_next() else None,
        }
    )


def _form_error(form, default):
    """Pesan error pertama dari form, atau `default` jika tidak ada."""
    errors = [e for field_errors in form.errors.values() for e in field_errors]
    return errors[0] if errors else default


def _count_of(model):
    """Subquery penghitung baris per post; menghindari join ganda dan GROUP BY besar."""
    counts = (
        model.objects.filter(post=OuterRef("pk"))
        .order_by()
        .values("post")
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def _feed_posts(user):
    """Queryset post lengkap dengan jumlah suka/komentar dan status suka milik `user`."""
    posts = Post.objects.select_related("author").annotate(
        like_count=_count_of(Like),
        comment_count=_count_of(Comment),
    )
    if user.is_authenticated:
        posts = posts.annotate(
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user))
        )
    return posts


def _post_card_json(request, post):
    """Kartu post hasil render ulang, dikirim ke JS untuk disisipkan atau menggantikan kartu lama."""
    post = _feed_posts(request.user).get(pk=post.pk)
    html = render_to_string(
        "community/_post_card.html", {"post": post}, request=request
    )
    return JsonResponse({"html": html})


@vary_on_headers("X-Requested-With")
def index(request):
    """Feed komunitas dengan filter kategori, pencarian, urutan, dan paginasi.

    AJAX hanya mendapat satu halaman potongan HTML; request biasa mendapat halaman penuh."""
    category = request.GET.get("category", "")
    if category not in CATEGORIES:
        category = ""
    query = request.GET.get("q", "").strip()[:SEARCH_MAX_LENGTH]
    sort = request.GET.get("sort", "")
    if sort not in SORTS:
        sort = "new"

    posts = _feed_posts(request.user)
    if category:
        posts = posts.filter(category=category)
    if query:
        posts = posts.filter(
            Q(content__icontains=query)
            | Q(news_title__icontains=query)
            | Q(author__username__icontains=query)
        )
    if sort == "old":
        posts = posts.order_by("created_at", "pk")
    elif sort == "popular":
        posts = posts.order_by("-like_count", "pk")
    elif sort == "komen":
        posts = posts.order_by("-comment_count", "pk")
    else:
        posts = posts.order_by("-created_at", "-pk")
    paginator = Paginator(posts, PAGE_SIZE)

    if _is_ajax(request):
        return _page_json(
            request,
            paginator,
            lambda page: render_to_string(
                "community/_post_list.html",
                {"posts": page, "category": category, "q": query},
                request=request,
            ),
        )

    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "community/community.html",
        {
            "posts": page,
            "page": page,
            "category": category,
            "q": query,
            "sort": sort,
            "base_qs": urlencode(
                {
                    k: v
                    for k, v in (("q", query), ("sort", "" if sort == "new" else sort))
                    if v
                }
            ),
            "categories": Post.CATEGORY_CHOICES,
            "form": PostForm(),
            "news": fetch_news(),
            "post_max": POST_MAX_LENGTH,
            **community_assets(),
        },
    )


@login_required
@require_POST
def create_post(request):
    """Buat postingan baru atas nama user yang login."""
    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        if _is_ajax(request):
            return _post_card_json(request, post)
        return redirect("community:index")
    return _fail(request, _form_error(form, "Postingan tidak valid."))


@login_required
@require_POST
def edit_post(request, pk):
    """Ubah postingan; hanya author yang bisa (selain itu 404)."""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    form = PostForm(request.POST, instance=post)
    if form.is_valid():
        form.save()
        if _is_ajax(request):
            return _post_card_json(request, post)
        return redirect("community:index")
    return _fail(request, _form_error(form, "Perubahan tidak valid."))


@login_required
@require_POST
def delete_post(request, pk):
    """Hapus postingan beserta suka dan komentarnya; hanya author yang bisa."""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()

    if _is_ajax(request):
        return JsonResponse({"deleted": True})
    return redirect("community:index")


@login_required
@require_POST
def toggle_like(request, pk):
    """Suka jika belum, batal suka jika sudah. Redirect `next` hanya ke host yang sama."""
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()

    if _is_ajax(request):
        return JsonResponse({"liked": created, "count": post.likes.count()})
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("community:index")


@vary_on_headers("X-Requested-With")
def post_detail(request, pk):
    """Halaman satu postingan dengan komentarnya (terbaru dulu, dipaginasi)."""
    post = get_object_or_404(_feed_posts(request.user), pk=pk)
    comments = post.comments.select_related("author").order_by("-created_at", "-pk")
    paginator = Paginator(comments, COMMENT_PAGE_SIZE)

    if _is_ajax(request):
        return _page_json(
            request,
            paginator,
            lambda page: "".join(
                render_to_string(
                    "community/_comment.html", {"comment": c}, request=request
                )
                for c in page
            ),
        )

    return render(
        request,
        "community/post_detail.html",
        {
            "post": post,
            "comments": paginator.get_page(request.GET.get("page")),
            "comment_total": paginator.count,
            "comment_max": COMMENT_MAX_LENGTH,
            **community_assets(),
        },
    )


@login_required
@require_POST
def add_comment(request, pk):
    """Tambah komentar pada postingan; AJAX mendapat HTML komentar dan jumlah terbaru."""
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
        return redirect("community:post_detail", pk=post.pk)
    return _fail(
        request,
        _form_error(form, "Komentar tidak valid."),
        "community:post_detail",
        pk=post.pk,
    )


@login_required
@require_POST
def edit_comment(request, pk):
    """Ubah komentar; hanya author yang bisa."""
    comment = get_object_or_404(Comment, pk=pk, author=request.user)
    form = CommentForm(request.POST, instance=comment)
    if not form.is_valid():
        return _fail(
            request,
            _form_error(form, "Komentar tidak valid."),
            "community:post_detail",
            pk=comment.post_id,
        )
    form.save()
    if _is_ajax(request):
        html = render_to_string(
            "community/_comment.html", {"comment": comment}, request=request
        )
        return JsonResponse({"html": html})
    return redirect("community:post_detail", pk=comment.post_id)


@login_required
@require_POST
def delete_comment(request, pk):
    """Hapus komentar; hanya author yang bisa. AJAX mendapat jumlah komentar terbaru."""
    comment = get_object_or_404(Comment, pk=pk, author=request.user)
    post_id = comment.post_id
    comment.delete()
    if _is_ajax(request):
        count = Comment.objects.filter(post_id=post_id).count()
        return JsonResponse({"deleted": True, "count": count})
    return redirect("community:post_detail", pk=post_id)


@login_required
@require_POST
def share_news(request):
    """Bagikan berita GNews sebagai post kategori berita.

    Data berita diambil dari cache server berdasarkan URL, bukan dari kiriman klien."""
    article = find_article(request.POST.get("url", ""))
    if article is None:
        return _fail(request, "Berita tidak ditemukan atau sudah kedaluwarsa.")

    form = ShareNewsForm(request.POST)
    if not form.is_valid():
        return _fail(request, _form_error(form, "Caption tidak valid."))

    post = Post.objects.create(
        author=request.user,
        category="berita",
        content=form.cleaned_data["content"],
        news_title=article["title"][:255],
        news_source=article["source"][:100],
        news_url=article["url"],
        news_snippet=article["snippet"],
    )

    if _is_ajax(request):
        return _post_card_json(request, post)
    return redirect("community:index")
