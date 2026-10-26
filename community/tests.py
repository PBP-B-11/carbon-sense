from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Like, Post


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
