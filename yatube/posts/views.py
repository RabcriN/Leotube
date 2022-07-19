from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def get_paginator(request, post_list):
    paginator = Paginator(post_list, settings.DEFAULT_PAGINATE_BY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    """Главная страница + паджинатор на 10 постов"""
    post_list = Post.objects.select_related('group', 'author')
    page_obj = get_paginator(request, post_list)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница группы + паджинатор на 10 постов"""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_obj = get_paginator(request, post_list)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Профайл пользователя + паджинатор на 10 постов"""
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    following = False
    if request.user.is_authenticated:
        if (Follow.objects.filter(user=request.user, author=author).exists()):
            following = True
    page_obj = get_paginator(request, post_list)
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Просмотр записи"""
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Создание нового поста"""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method != 'POST' or form.is_valid() is False:
        return render(request, 'posts/post_create.html', {'form': form})
    new_post = form.save(commit=False)
    new_post.author = request.user
    new_post.save()
    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    """Редактирование поста"""
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {'form': form, 'is_edit': True, 'post': post}
    return render(request, 'posts/post_create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    cache.clear()
    user = request.user
    authors = user.follower.values_list('author', flat=True)
    posts_list = Post.objects.filter(author__following__user=request.user)
    page_obj = get_paginator(request, posts_list)
    context = {
        'user': user,
        'authors': authors,
        'posts_list': posts_list,
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    already_followed = Follow.objects.filter(
        user=request.user,
        author=author
    ).exists()
    if user == author or already_followed:
        return redirect('posts:profile', username=username)
    Follow.objects.create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=user, author=author).delete()
    return redirect('posts:profile', username=username)
