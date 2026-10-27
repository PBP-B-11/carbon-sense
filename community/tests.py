from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Comment, Like, Post


class CommunityFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user("me", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.post = Post.objects.create(author=self.me, category="tips", content="halo")

    def test_feed_renders(self):
        self.client.force_login(self.me)
        res = self.client.get(reverse("community:index"))
        self.assertContains(res, "halo")
        self.assertContains(res, "js-edit")

    def test_create_and_like_toggle(self):
        self.client.force_login(self.other)
        self.client.post(
            reverse("community:create_post"), {"content": "baru", "category": "diskusi"}
        )
        self.assertTrue(Post.objects.filter(author=self.other, content="baru").exists())
        url = reverse("community:toggle_like", args=[self.post.pk])
        self.client.post(url)
        self.assertEqual(Like.objects.count(), 1)
        self.client.post(url)
        self.assertEqual(Like.objects.count(), 0)

    def test_only_owner_can_edit_or_delete(self):
        self.client.force_login(self.other)
        res = self.client.post(
            reverse("community:edit_post", args=[self.post.pk]),
            {"content": "x", "category": "tips"},
        )
        self.assertEqual(res.status_code, 404)
        res = self.client.post(reverse("community:delete_post", args=[self.post.pk]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_detail_and_comment(self):
        self.client.force_login(self.other)
        self.client.post(
            reverse("community:add_comment", args=[self.post.pk]), {"content": "mantap"}
        )
        res = self.client.get(reverse("community:post_detail", args=[self.post.pk]))
        self.assertContains(res, "mantap")


class NewsShareTests(TestCase):
    ARTICLE = {
        "title": "Judul",
        "snippet": "Cuplikan",
        "url": "https://example.com/a",
        "source": "Media",
        "published_at": None,
    }

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        cache.set("community:gnews", [self.ARTICLE])
        self.user = get_user_model().objects.create_user("me", password="x")
        self.client.force_login(self.user)

    def test_share_uses_cached_article(self):
        self.client.post(
            reverse("community:share_news"),
            {"url": self.ARTICLE["url"], "content": "menarik"},
        )
        post = Post.objects.get()
        self.assertEqual(
            (post.category, post.news_title, post.news_source),
            ("berita", "Judul", "Media"),
        )

    def test_share_rejects_unknown_url(self):
        self.client.post(
            reverse("community:share_news"), {"url": "https://evil.test/x"}
        )
        self.assertFalse(Post.objects.exists())

    def test_feed_lists_news(self):
        res = self.client.get(reverse("community:index"))
        self.assertContains(res, "Judul")

    def test_ajax_share_returns_card_html(self):
        res = self.client.post(
            reverse("community:share_news"),
            {"url": self.ARTICLE["url"], "content": "menarik"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res.status_code, 200)
        html = res.json()["html"]
        self.assertIn("Judul", html)
        self.assertIn("menarik", html)
        self.assertEqual(Post.objects.count(), 1)

    def test_ajax_share_unknown_url_returns_400(self):
        res = self.client.post(
            reverse("community:share_news"),
            {"url": "https://evil.test/x"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())
        self.assertFalse(Post.objects.exists())

    def test_plain_share_still_redirects(self):
        res = self.client.post(
            reverse("community:share_news"), {"url": self.ARTICLE["url"]}
        )
        self.assertRedirects(res, reverse("community:index"))


class AjaxLikeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("me", password="x")
        self.post = Post.objects.create(author=self.user, content="halo")
        self.url = reverse("community:toggle_like", args=[self.post.pk])
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_ajax_like_returns_json_and_toggles(self):
        self.client.force_login(self.user)
        res = self.client.post(self.url, **self.ajax)
        self.assertEqual(res.json(), {"liked": True, "count": 1})
        res = self.client.post(self.url, **self.ajax)
        self.assertEqual(res.json(), {"liked": False, "count": 0})

    def test_plain_post_still_redirects(self):
        self.client.force_login(self.user)
        res = self.client.post(self.url)
        self.assertRedirects(res, reverse("community:index"))

    def test_anonymous_ajax_is_redirected_to_login(self):
        res = self.client.post(self.url, **self.ajax)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Like.objects.count(), 0)


class AjaxDeleteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.post = Post.objects.create(author=self.owner, content="halo")
        self.url = reverse("community:delete_post", args=[self.post.pk])
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_ajax_delete_returns_json(self):
        self.client.force_login(self.owner)
        res = self.client.post(self.url, **self.ajax)
        self.assertEqual(res.json(), {"deleted": True})
        self.assertFalse(Post.objects.exists())

    def test_ajax_delete_by_non_owner_is_404(self):
        self.client.force_login(self.other)
        res = self.client.post(self.url, **self.ajax)
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Post.objects.exists())

    def test_plain_delete_still_redirects(self):
        self.client.force_login(self.owner)
        res = self.client.post(self.url)
        self.assertRedirects(res, reverse("community:index"))


class AjaxPostTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_ajax_create_returns_card_html(self):
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:create_post"),
            {"content": "halo dunia", "category": "tips"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 200)
        html = res.json()["html"]
        self.assertIn("halo dunia", html)
        self.assertIn("js-edit", html)  # pemilik melihat tombol edit
        self.assertEqual(Post.objects.count(), 1)

    def test_ajax_create_invalid_returns_400(self):
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:create_post"),
            {"content": "", "category": "tips"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Post.objects.exists())

    def test_ajax_edit_returns_updated_card(self):
        post = Post.objects.create(author=self.owner, content="lama", category="tips")
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:edit_post", args=[post.pk]),
            {"content": "baru", "category": "diskusi"},
            **self.ajax,
        )
        self.assertIn("baru", res.json()["html"])
        post.refresh_from_db()
        self.assertEqual((post.content, post.category), ("baru", "diskusi"))

    def test_ajax_edit_by_non_owner_is_404(self):
        post = Post.objects.create(author=self.owner, content="lama")
        self.client.force_login(self.other)
        res = self.client.post(
            reverse("community:edit_post", args=[post.pk]),
            {"content": "x", "category": "tips"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 404)

    def test_plain_create_still_redirects(self):
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:create_post"), {"content": "x", "category": "tips"}
        )
        self.assertRedirects(res, reverse("community:index"))


class AjaxCommentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("me", password="x")
        self.post = Post.objects.create(author=self.user, content="halo")
        self.url = reverse("community:add_comment", args=[self.post.pk])
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_ajax_comment_returns_html_and_count(self):
        self.client.force_login(self.user)
        res = self.client.post(self.url, {"content": "mantap"}, **self.ajax)
        data = res.json()
        self.assertIn("mantap", data["html"])
        self.assertEqual(data["count"], 1)
        res = self.client.post(self.url, {"content": "lagi"}, **self.ajax)
        self.assertEqual(res.json()["count"], 2)

    def test_ajax_empty_comment_returns_400(self):
        self.client.force_login(self.user)
        res = self.client.post(self.url, {"content": ""}, **self.ajax)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(self.post.comments.exists())

    def test_plain_comment_still_redirects(self):
        self.client.force_login(self.user)
        res = self.client.post(self.url, {"content": "x"})
        self.assertRedirects(res, reverse("community:post_detail", args=[self.post.pk]))

    def test_detail_page_lists_comments(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"content": "terlihat"})
        res = self.client.get(reverse("community:post_detail", args=[self.post.pk]))
        self.assertContains(res, "terlihat")
        self.assertContains(res, 'id="comment-count"')


class ValidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("me", password="x")
        self.client.force_login(self.user)
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_post_too_long_is_rejected_with_message(self):
        from .forms import POST_MAX_LENGTH

        res = self.client.post(
            reverse("community:create_post"),
            {"content": "a" * (POST_MAX_LENGTH + 1), "category": "tips"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)
        self.assertTrue(res.json()["error"])
        self.assertFalse(Post.objects.exists())

    def test_whitespace_only_post_is_rejected(self):
        res = self.client.post(
            reverse("community:create_post"),
            {"content": "   ", "category": "tips"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)

    def test_invalid_category_is_rejected(self):
        res = self.client.post(
            reverse("community:create_post"),
            {"content": "x", "category": "hack"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)

    def test_comment_too_long_is_rejected(self):
        from .forms import COMMENT_MAX_LENGTH

        post = Post.objects.create(author=self.user, content="halo")
        res = self.client.post(
            reverse("community:add_comment", args=[post.pk]),
            {"content": "a" * (COMMENT_MAX_LENGTH + 1)},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(post.comments.exists())

    def test_share_caption_too_long_is_rejected(self):
        from django.core.cache import cache

        from .forms import POST_MAX_LENGTH

        cache.set(
            "community:gnews",
            [
                {
                    "title": "J",
                    "snippet": "",
                    "url": "https://e.com/a",
                    "source": "M",
                    "published_at": None,
                }
            ],
        )
        res = self.client.post(
            reverse("community:share_news"),
            {"url": "https://e.com/a", "content": "a" * (POST_MAX_LENGTH + 1)},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Post.objects.exists())


class NewsPostEditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("me", password="x")
        self.client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            category="berita",
            content="",
            news_title="Judul",
            news_source="Media",
            news_url="https://e.com/a",
        )
        self.url = reverse("community:edit_post", args=[self.post.pk])
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_news_post_can_be_edited_without_caption(self):
        res = self.client.post(self.url, {"content": ""}, **self.ajax)
        self.assertEqual(res.status_code, 200)

    def test_news_post_category_cannot_change(self):
        self.client.post(
            self.url, {"content": "caption baru", "category": "tips"}, **self.ajax
        )
        self.post.refresh_from_db()
        self.assertEqual(self.post.category, "berita")
        self.assertEqual(self.post.content, "caption baru")

    def test_regular_post_still_requires_content(self):
        plain = Post.objects.create(author=self.user, content="isi", category="tips")
        res = self.client.post(
            reverse("community:edit_post", args=[plain.pk]),
            {"content": "", "category": "tips"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)


class CommentCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.post = Post.objects.create(author=self.owner, content="halo")
        self.comment = Comment.objects.create(
            post=self.post, author=self.owner, content="lama"
        )
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_owner_can_edit_comment(self):
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:edit_comment", args=[self.comment.pk]),
            {"content": "baru"},
            **self.ajax,
        )
        self.assertIn("baru", res.json()["html"])
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "baru")

    def test_edit_comment_with_empty_content_is_400(self):
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:edit_comment", args=[self.comment.pk]),
            {"content": ""},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 400)

    def test_non_owner_cannot_edit_or_delete_comment(self):
        self.client.force_login(self.other)
        res = self.client.post(
            reverse("community:edit_comment", args=[self.comment.pk]),
            {"content": "x"},
            **self.ajax,
        )
        self.assertEqual(res.status_code, 404)
        res = self.client.post(
            reverse("community:delete_comment", args=[self.comment.pk]), **self.ajax
        )
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_owner_can_delete_comment_and_get_count(self):
        Comment.objects.create(post=self.post, author=self.other, content="lain")
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:delete_comment", args=[self.comment.pk]), **self.ajax
        )
        self.assertEqual(res.json(), {"deleted": True, "count": 1})

    def test_plain_delete_comment_redirects_to_detail(self):
        self.client.force_login(self.owner)
        res = self.client.post(
            reverse("community:delete_comment", args=[self.comment.pk])
        )
        self.assertRedirects(res, reverse("community:post_detail", args=[self.post.pk]))

    def test_detail_shows_actions_only_for_own_comments(self):
        edit_url = reverse("community:edit_comment", args=[self.comment.pk])
        self.client.force_login(self.other)
        res = self.client.get(reverse("community:post_detail", args=[self.post.pk]))
        self.assertNotContains(res, edit_url)
        self.client.force_login(self.owner)
        res = self.client.get(reverse("community:post_detail", args=[self.post.pk]))
        self.assertContains(res, edit_url)


class FeedFilterPaginationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("me", password="x")
        for i in range(12):
            Post.objects.create(author=self.user, category="tips", content=f"tips {i}")
        Post.objects.create(
            author=self.user, category="diskusi", content="satu diskusi"
        )
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        self.url = reverse("community:index")

    def test_first_page_has_page_size_cards_and_load_more(self):
        res = self.client.get(self.url)
        self.assertEqual(res.content.decode().count('<article class="card post"'), 10)
        self.assertContains(res, "js-load-more")

    def test_ajax_second_page_returns_remaining_and_no_next(self):
        data = self.client.get(self.url, {"page": 2}, **self.ajax).json()
        self.assertEqual(data["html"].count("<article"), 3)
        self.assertFalse(data["has_next"])

    def test_ajax_page_out_of_range_is_empty(self):
        data = self.client.get(self.url, {"page": 99}, **self.ajax).json()
        self.assertEqual(data, {"html": "", "has_next": False, "next_page": None})

    def test_category_filter(self):
        data = self.client.get(self.url, {"category": "diskusi"}, **self.ajax).json()
        self.assertEqual(data["html"].count("<article"), 1)
        self.assertIn("satu diskusi", data["html"])
        self.assertFalse(data["has_next"])

    def test_filter_with_no_results_shows_note(self):
        data = self.client.get(self.url, {"category": "berita"}, **self.ajax).json()
        self.assertIn("yang cocok", data["html"])

    def test_unknown_category_is_ignored(self):
        res = self.client.get(self.url, {"category": "hack"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode().count('<article class="card post"'), 10)


@override_settings(GNEWS_API_KEY="test-key")
class NewsClientTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    @staticmethod
    def _response(articles):
        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"articles": articles}

        return Resp()

    def test_failure_is_cached_so_api_is_not_hammered(self):
        import requests
        from unittest.mock import patch

        from .news import fetch_news

        with patch(
            "community.news.requests.get", side_effect=requests.ConnectionError
        ) as get:
            self.assertEqual(fetch_news(), [])
            self.assertEqual(fetch_news(), [])
        self.assertEqual(get.call_count, 1)

    def test_only_http_urls_are_kept(self):
        from unittest.mock import patch

        from .news import fetch_news

        good = {"title": "A", "url": "https://e.com/a", "source": {"name": "M"}}
        bad = {"title": "B", "url": "javascript:alert(1)", "source": {"name": "M"}}
        with patch(
            "community.news.requests.get", return_value=self._response([good, bad])
        ):
            urls = [a["url"] for a in fetch_news()]
        self.assertEqual(urls, ["https://e.com/a"])

    def test_find_article_refetches_when_cache_expired(self):
        from unittest.mock import patch

        from .news import find_article

        art = {"title": "A", "url": "https://e.com/a", "source": {"name": "M"}}
        with patch("community.news.requests.get", return_value=self._response([art])):
            found = find_article("https://e.com/a")
        self.assertEqual(found["title"], "A")


class LikeRedirectTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("me", password="x")
        self.client.force_login(self.user)
        self.post = Post.objects.create(author=self.user, content="halo")
        self.url = reverse("community:toggle_like", args=[self.post.pk])

    def test_external_next_is_ignored(self):
        res = self.client.post(self.url, {"next": "https://evil.test/"})
        self.assertRedirects(res, reverse("community:index"))

    def test_internal_next_is_followed(self):
        target = reverse("community:post_detail", args=[self.post.pk])
        res = self.client.post(self.url, {"next": target})
        self.assertRedirects(res, target)


class DetailLikeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("me", password="x")
        self.post = Post.objects.create(author=self.user, content="halo")
        self.url = reverse("community:post_detail", args=[self.post.pk])

    def test_detail_has_like_button_with_count_and_state(self):
        Like.objects.create(post=self.post, user=self.user)
        self.client.force_login(self.user)
        res = self.client.get(self.url)
        self.assertContains(res, "js-like-form")
        self.assertContains(res, 'aria-pressed="true"')
        self.assertContains(res, '<span class="like-count">1</span>')

    def test_detail_like_redirects_back_to_detail(self):
        self.client.force_login(self.user)
        res = self.client.post(
            reverse("community:toggle_like", args=[self.post.pk]), {"next": self.url}
        )
        self.assertRedirects(res, self.url)

    def test_anonymous_gets_login_link_instead_of_like_form(self):
        Like.objects.create(post=self.post, user=self.user)
        res = self.client.get(self.url)
        self.assertNotContains(res, "js-like-form")
        self.assertContains(res, reverse("profil:login") + "?next=")
        self.assertContains(res, "1 suka")  # jumlah tetap terlihat

    def test_anonymous_feed_has_no_like_form(self):
        res = self.client.get(reverse("community:index"))
        self.assertNotContains(res, "js-like-form")


class SearchSortCountTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.ana = User.objects.create_user("ana", password="x")
        self.budi = User.objects.create_user("budi", password="x")
        self.cici = User.objects.create_user("cici", password="x")
        self.p_old = Post.objects.create(
            author=self.ana, category="tips", content="hemat listrik rumah"
        )
        self.p_mid = Post.objects.create(
            author=self.budi, category="diskusi", content="naik kereta ke kampus"
        )
        self.p_new = Post.objects.create(
            author=self.ana,
            category="berita",
            content="",
            news_title="Hutan Kalimantan terbakar",
            news_source="M",
            news_url="https://e.com/a",
        )
        # p_mid paling populer: 2 suka dan 3 komentar (menguji hitungan tidak berlipat karena join)
        Like.objects.create(post=self.p_mid, user=self.ana)
        Like.objects.create(post=self.p_mid, user=self.budi)
        for i in range(3):
            Comment.objects.create(post=self.p_mid, author=self.cici, content=f"k{i}")
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        self.url = reverse("community:index")

    def _titles(self, **params):
        html = self.client.get(self.url, params, **self.ajax).json()["html"]
        return html

    def test_counts_are_not_multiplied_by_joins(self):
        res = self.client.get(self.url)
        by_pk = {p.pk: p for p in res.context["posts"]}
        self.assertEqual(by_pk[self.p_mid.pk].like_count, 2)
        self.assertEqual(by_pk[self.p_mid.pk].comment_count, 3)
        self.assertEqual(by_pk[self.p_old.pk].like_count, 0)

    def test_search_matches_content(self):
        html = self._titles(q="listrik")
        self.assertIn("hemat listrik", html)
        self.assertNotIn("naik kereta", html)

    def test_search_matches_username_and_news_title(self):
        self.assertIn("hemat listrik", self._titles(q="ana"))
        html = self._titles(q="kalimantan")
        self.assertIn("Hutan Kalimantan", html)
        self.assertNotIn("hemat listrik", html)

    def test_search_is_case_insensitive(self):
        self.assertIn("naik kereta", self._titles(q="KERETA"))

    def test_search_combines_with_category(self):
        html = self._titles(q="ana", category="tips")
        self.assertIn("hemat listrik", html)
        self.assertNotIn("Hutan Kalimantan", html)

    def test_no_match_shows_note(self):
        self.assertIn("yang cocok", self._titles(q="tidak-ada-yang-begini"))

    def test_default_sort_is_newest_first(self):
        html = self._titles()
        self.assertLess(html.index("Hutan Kalimantan"), html.index("naik kereta"))
        self.assertLess(html.index("naik kereta"), html.index("hemat listrik"))

    def test_popular_sort_puts_most_liked_first(self):
        html = self._titles(sort="popular")
        self.assertLess(html.index("naik kereta"), html.index("Hutan Kalimantan"))

    def test_unknown_sort_falls_back_to_newest(self):
        html = self._titles(sort="hack")
        self.assertLess(html.index("Hutan Kalimantan"), html.index("hemat listrik"))

    def test_full_page_keeps_query_in_inputs(self):
        res = self.client.get(self.url, {"q": "listrik", "sort": "popular"})
        self.assertContains(res, 'value="listrik"')
        self.assertContains(res, '<option value="popular" selected>')

    def test_very_long_query_is_truncated_not_error(self):
        res = self.client.get(self.url, {"q": "x" * 500})
        self.assertEqual(res.status_code, 200)
