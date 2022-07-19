import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
            id=1,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа номер два',
            slug='test_slug_2',
            description='Группа для проверки поста другой группы',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        Post.objects.bulk_create(
            [Post(
                author=cls.user,
                text='Тестовый пост длиной более 15 символов',
                group=Group.objects.get(slug='test_slug'),
                image=uploaded,
            ) for _ in range(13)]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.get(username='Author')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_context(self, page_object):
        post = Post.objects.first()
        post_data = [
            post.text,
            post.id,
            post.group.slug,
            post.author.username,
            post.image,
        ]
        context_data = [
            page_object.text,
            page_object.id,
            page_object.group.slug,
            page_object.author.username,
            page_object.image,
        ]
        if post_data != context_data:
            return False
        return True

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом + паджинатор
        на 10 постов"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertTrue(
            self.check_context(first_object),
            'Словари контекста не совпадают'
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом + паджинатор
        на 10 постов"""
        response = (self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}))
        )
        first_object = response.context['page_obj'][0]
        self.assertTrue(
            self.check_context(first_object),
            'Словари контекста не совпадают'
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом + паджинатор
        на 10 постов"""
        response = (self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'Author'}))
        )
        first_object = response.context['page_obj'][0]
        self.assertTrue(
            self.check_context(first_object),
            'Словари контекста не совпадают'
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': Post.objects.first().id},
            ))
        )
        page_object = response.context['post']
        self.assertTrue(
            self.check_context(page_object),
            'Словари контекста не совпадают'
        )

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:post_create')))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'}))
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        page_object = response.context['post']
        post_id_0 = page_object.id
        self.assertEqual(post_id_0, 1)

    def test_created_post_not_in_another_group(self):
        """Проверяем, что пост не попал в другую группу"""
        response = (self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': Group.objects.last().slug}
            ))
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_picture_uploaded(self):
        """Пост с картинкой создаётся"""
        post = Post.objects.last()
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_add_comment(self):
        """Авторизированный пользователь создаёт комментарий"""
        post = Post.objects.last()
        form_data = {
            'text': 'test comment',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=False,
        )
        self.assertEqual(response.status_code, 302)

        response1 = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id}
            )
        )
        self.assertEqual(len(response1.context['comments']), 1)

    def test_cache_index(self):
        """Проверяем работу кеша главной страницы"""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(text='test cashe', author=self.user)
        response_old = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        posts_new = response_new.content
        self.assertNotEqual(old_posts, posts_new)

    def test_authorized_client_subscribes_and_unsubscribes(self):
        """Проверка работоспособности подписок"""
        user = User.objects.create_user(username='Not_Author')
        follower = Client()
        follower.force_login(user)
        response = follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user.username}
        ))
        response = follower.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['posts_list']), 13)

        user2 = User.objects.create_user(username='not_subscriber')
        not_subscriber = Client()
        not_subscriber.force_login(user2)
        response = not_subscriber.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['posts_list']), 0)

        response = follower.post(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user.username}
        ))
        response = follower.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['posts_list']), 0)
