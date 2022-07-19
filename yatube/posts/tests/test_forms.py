from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=Group.objects.get(slug='test_slug'),
        )

    def setUp(self):
        self.user = User.objects.get(username='Author')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_form(self):
        """Валидная форма создает запись и редиректит"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост длиной более 15 символов',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': 'Author'})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        context = {
            post.text: 'Тестовый пост длиной более 15 символов',
            post.author.username: 'Author',
            post.group.slug: 'test_slug',
        }
        for field, expected in context.items():
            self.assertEqual(field, expected)

    def test_edit_post_form(self):
        """Валидная форма редактирует запись и редиректит"""
        form_data = {
            'text': 'Тестовый пост отредактирован',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': '1'}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': '1'})
        )
        post = Post.objects.first()
        context = {
            post.text: 'Тестовый пост отредактирован',
            post.author.username: 'Author',
            post.group.slug: 'test_slug',
        }
        for field, expected in context.items():
            self.assertEqual(field, expected)
