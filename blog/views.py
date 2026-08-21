from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView

from .forms import CommentForm, PostForm, RegistrationForm, UserForm
from .models import Category, Comment, Post

POSTS_PER_PAGE = 10
User = get_user_model()


def public_posts():
    return (Post.objects.select_related('author', 'category', 'location')
            .filter(is_published=True,
                    category__is_published=True,
                    pub_date__lte=timezone.now())
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date'))


def paginate(request, queryset):
    return Paginator(
        queryset,
        POSTS_PER_PAGE,
    ).get_page(request.GET.get('page'))


def index(request):
    return render(request, 'blog/index.html', {
        'page_obj': paginate(request, public_posts()),
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )
    posts = public_posts().filter(category=category)
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': paginate(request, posts),
    })


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = (Post.objects.select_related('author', 'category', 'location')
             .filter(author=profile_user)
             .annotate(comment_count=Count('comments'))
             .order_by('-pub_date'))
    if request.user != profile_user:
        posts = posts.filter(is_published=True,
                             category__is_published=True,
                             pub_date__lte=timezone.now())
    return render(request, 'blog/profile.html', {
        'profile': profile_user,
        'page_obj': paginate(request, posts),
    })


def get_post_for_view(request, post_id):
    queryset = Post.objects.select_related('author', 'category', 'location')
    post = get_object_or_404(queryset, pk=post_id)
    if request.user != post.author and (
        not post.is_published
        or not post.category.is_published
        or post.pub_date > timezone.now()
    ):
        post = get_object_or_404(public_posts(), pk=post_id)
    return post


def post_detail(request, post_id):
    post = get_post_for_view(request, post_id)
    comments = post.comments.select_related('author').order_by('created_at')
    return render(request, 'blog/detail.html', {
        'post': post,
        'comments': comments,
        'form': CommentForm(),
    })


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post.pk)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post.pk)
    form = PostForm(instance=post)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(public_posts(), pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect('blog:post_detail', post_id=post.pk)


def get_comment_or_404(post_id, comment_id):
    return get_object_or_404(
        Comment.objects.select_related('post', 'author'),
        pk=comment_id,
        post_id=post_id,
    )


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_comment_or_404(post_id, comment_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'form': form,
        'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_comment_or_404(post_id, comment_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})


@login_required
def edit_profile(request):
    form = UserForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/user.html', {'form': form})


class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/registration_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('blog:index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.object.username},
        )
