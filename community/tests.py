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
        self.client.post(reverse("community:create_post"), {"content": "baru", "category": "diskusi"})
        self.assertTrue(Post.objects.filter(author=self.other, content="baru").exists())
        url = reverse("community:toggle_like", args=[self.post.pk])
        self.client.post(url)
        self.assertEqual(Like.objects.count(), 1)
        self.client.post(url)
        self.assertEqual(Like.objects.count(), 0)

    def test_only_owner_can_edit_or_delete(self):
        self.client.force_login(self.other)
        res = self.client.post(reverse("community:edit_post", args=[self.post.pk]), {"content": "x", "category": "tips"})
        self.assertEqual(res.status_code, 404)
        res = self.client.post(reverse("community:delete_post", args=[self.post.pk]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_detail_and_comment(self):
        self.client.force_login(self.other)
        self.client.post(reverse("community:add_comment", args=[self.post.pk]), {"content": "mantap"})
        res = self.client.get(reverse("community:post_detail", args=[self.post.pk]))
        self.assertContains(res, "mantap")
