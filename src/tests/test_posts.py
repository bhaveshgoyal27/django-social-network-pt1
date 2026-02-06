from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from src.posts.models import Post, Comment, Like
from src.posts.forms import PostModelForm, CommentModelForm
from src.profiles.models import Profile


class PostModelTest(TestCase):
    """Test cases for Post model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_post_creation(self):
        """Test post creation"""
        post = Post.objects.create(
            content="Test post content",
            author=self.profile
        )
        self.assertIsNotNone(post)
        self.assertEqual(post.content, "Test post content")
        self.assertEqual(post.author, self.profile)

    def test_post_str_method(self):
        """Test post string representation"""
        post = Post.objects.create(
            content="This is a long test post content",
            author=self.profile
        )
        self.assertEqual(str(post), "This is a long test ")

    def test_post_ordering(self):
        """Test posts are ordered by creation date (newest first)"""
        post1 = Post.objects.create(content="First post", author=self.profile)
        post2 = Post.objects.create(content="Second post", author=self.profile)
        
        posts = Post.objects.all()
        self.assertEqual(posts[0], post2)
        self.assertEqual(posts[1], post1)

    def test_num_likes(self):
        """Test num_likes method"""
        post = Post.objects.create(content="Test post", author=self.profile)
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        
        self.assertEqual(post.num_likes(), 0)
        
        post.liked.add(profile2)
        self.assertEqual(post.num_likes(), 1)

    def test_num_comments(self):
        """Test num_comments method"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.assertEqual(post.num_comments(), 0)
        
        Comment.objects.create(
            user=self.profile,
            post=post,
            body="Test comment"
        )
        self.assertEqual(post.num_comments(), 1)

    def test_post_with_image(self):
        """Test post creation with image"""
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'',
            content_type='image/jpeg'
        )
        post = Post.objects.create(
            content="Post with image",
            author=self.profile,
            image=image
        )
        self.assertTrue(post.image)

    def test_liked_many_to_many(self):
        """Test liked ManyToMany relationship"""
        post = Post.objects.create(content="Test post", author=self.profile)
        user2 = User.objects.create_user(username='user2', password='pass123')
        user3 = User.objects.create_user(username='user3', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        profile3 = Profile.objects.get(user=user3)
        
        post.liked.add(profile2, profile3)
        self.assertEqual(post.liked.count(), 2)
        self.assertIn(profile2, post.liked.all())
        self.assertIn(profile3, post.liked.all())


class CommentModelTest(TestCase):
    """Test cases for Comment model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)
        self.post = Post.objects.create(content="Test post", author=self.profile)

    def test_comment_creation(self):
        """Test comment creation"""
        comment = Comment.objects.create(
            user=self.profile,
            post=self.post,
            body="Test comment"
        )
        self.assertIsNotNone(comment)
        self.assertEqual(comment.body, "Test comment")
        self.assertEqual(comment.user, self.profile)
        self.assertEqual(comment.post, self.post)

    def test_comment_str_method(self):
        """Test comment string representation"""
        comment = Comment.objects.create(
            user=self.profile,
            post=self.post,
            body="Test comment"
        )
        self.assertEqual(str(comment), str(comment.pk))

    def test_comment_on_delete_cascade(self):
        """Test comment is deleted when post is deleted"""
        comment = Comment.objects.create(
            user=self.profile,
            post=self.post,
            body="Test comment"
        )
        comment_id = comment.id
        
        self.post.delete()
        
        self.assertFalse(Comment.objects.filter(id=comment_id).exists())

    def test_multiple_comments_on_post(self):
        """Test multiple comments on a single post"""
        Comment.objects.create(user=self.profile, post=self.post, body="Comment 1")
        Comment.objects.create(user=self.profile, post=self.post, body="Comment 2")
        Comment.objects.create(user=self.profile, post=self.post, body="Comment 3")
        
        self.assertEqual(self.post.comment_set.count(), 3)


class LikeModelTest(TestCase):
    """Test cases for Like model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)
        self.post = Post.objects.create(content="Test post", author=self.profile)

    def test_like_creation(self):
        """Test like creation"""
        like = Like.objects.create(
            user=self.profile,
            post=self.post,
            value='Like'
        )
        self.assertIsNotNone(like)
        self.assertEqual(like.value, 'Like')

    def test_like_str_method(self):
        """Test like string representation"""
        like = Like.objects.create(
            user=self.profile,
            post=self.post,
            value='Like'
        )
        expected = f"{self.profile}-{self.post}-Like"
        self.assertEqual(str(like), expected)

    def test_like_choices(self):
        """Test like value choices"""
        like = Like.objects.create(user=self.profile, post=self.post, value='Like')
        self.assertIn(like.value, ['Like', 'Unlike'])

    def test_unlike_value(self):
        """Test unlike value"""
        like = Like.objects.create(
            user=self.profile,
            post=self.post,
            value='Unlike'
        )
        self.assertEqual(like.value, 'Unlike')

    def test_like_on_delete_cascade(self):
        """Test like is deleted when post is deleted"""
        like = Like.objects.create(user=self.profile, post=self.post, value='Like')
        like_id = like.id
        
        self.post.delete()
        
        self.assertFalse(Like.objects.filter(id=like_id).exists())


class PostViewsTest(TestCase):
    """Test cases for Post views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_main_post_view_requires_login(self):
        """Test main post view requires authentication"""
        response = self.client.get(reverse('posts:main-post-view'))
        self.assertEqual(response.status_code, 302)

    def test_main_post_view_authenticated(self):
        """Test main post view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('posts:main-post-view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/main.html')

    def test_create_post(self):
        """Test creating a post"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('posts:main-post-view'), {
            'submit_p_form': '',
            'content': 'New test post'
        })
        
        self.assertTrue(Post.objects.filter(content='New test post').exists())

    def test_create_comment(self):
        """Test creating a comment"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('posts:main-post-view'), {
            'submit_c_form': '',
            'body': 'Test comment',
            'post_id': post.id
        })
        
        self.assertTrue(Comment.objects.filter(body='Test comment').exists())

    def test_like_unlike_post(self):
        """Test liking and unliking a post"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.client.login(username='testuser', password='testpass123')
        
        # Like the post
        response = self.client.post(reverse('posts:like-post-view'), {
            'post_id': post.id
        })
        post.refresh_from_db()
        self.assertIn(self.profile, post.liked.all())
        
        # Unlike the post
        response = self.client.post(reverse('posts:like-post-view'), {
            'post_id': post.id
        })
        post.refresh_from_db()
        self.assertNotIn(self.profile, post.liked.all())

    def test_like_creates_like_object(self):
        """Test that liking creates a Like object"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('posts:like-post-view'), {
            'post_id': post.id
        })
        
        self.assertTrue(
            Like.objects.filter(user=self.profile, post=post).exists()
        )

    def test_post_delete_view_requires_login(self):
        """Test post delete view requires authentication"""
        post = Post.objects.create(content="Test post", author=self.profile)
        response = self.client.get(
            reverse('posts:post-delete', kwargs={'pk': post.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_post_delete_view_authenticated(self):
        """Test post delete view for authenticated user"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('posts:post-delete', kwargs={'pk': post.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/confirm_del.html')

    def test_post_delete_post_method(self):
        """Test deleting a post"""
        post = Post.objects.create(content="Test post", author=self.profile)
        post_id = post.id
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('posts:post-delete', kwargs={'pk': post.pk})
        )
        
        self.assertFalse(Post.objects.filter(id=post_id).exists())

    def test_post_delete_only_author(self):
        """Test only author can delete post"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        post = Post.objects.create(content="Test post", author=profile2)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('posts:post-delete', kwargs={'pk': post.pk})
        )
        
        # Should show warning message
        messages = list(response.context['messages'])
        self.assertTrue(any('author' in str(m) for m in messages))

    def test_post_update_view_requires_login(self):
        """Test post update view requires authentication"""
        post = Post.objects.create(content="Test post", author=self.profile)
        response = self.client.get(
            reverse('posts:post-update', kwargs={'pk': post.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_post_update_view_authenticated(self):
        """Test post update view for authenticated user"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('posts:post-update', kwargs={'pk': post.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/update.html')

    def test_post_update_post_method(self):
        """Test updating a post"""
        post = Post.objects.create(content="Test post", author=self.profile)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('posts:post-update', kwargs={'pk': post.pk}),
            {'content': 'Updated content'}
        )
        
        post.refresh_from_db()
        self.assertEqual(post.content, 'Updated content')

    def test_post_update_only_author(self):
        """Test only author can update post"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        post = Post.objects.create(content="Test post", author=profile2)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('posts:post-update', kwargs={'pk': post.pk}),
            {'content': 'Updated content'}
        )
        
        post.refresh_from_db()
        self.assertNotEqual(post.content, 'Updated content')


class PostFormTest(TestCase):
    """Test cases for Post forms"""

    def test_post_form_valid(self):
        """Test post form with valid data"""
        form = PostModelForm(data={'content': 'Test post content'})
        self.assertTrue(form.is_valid())

    def test_post_form_empty_content(self):
        """Test post form with empty content"""
        form = PostModelForm(data={'content': ''})
        self.assertFalse(form.is_valid())

    def test_post_form_fields(self):
        """Test post form has correct fields"""
        form = PostModelForm()
        self.assertIn('content', form.fields)
        self.assertIn('image', form.fields)

    def test_post_form_content_widget(self):
        """Test post form content widget is textarea"""
        form = PostModelForm()
        self.assertEqual(form.fields['content'].widget.attrs['rows'], 2)


class CommentFormTest(TestCase):
    """Test cases for Comment forms"""

    def test_comment_form_valid(self):
        """Test comment form with valid data"""
        form = CommentModelForm(data={'body': 'Test comment'})
        self.assertTrue(form.is_valid())

    def test_comment_form_empty_body(self):
        """Test comment form with empty body"""
        form = CommentModelForm(data={'body': ''})
        self.assertFalse(form.is_valid())

    def test_comment_form_fields(self):
        """Test comment form has correct fields"""
        form = CommentModelForm()
        self.assertIn('body', form.fields)

    def test_comment_form_placeholder(self):
        """Test comment form has correct placeholder"""
        form = CommentModelForm()
        self.assertEqual(
            form.fields['body'].widget.attrs['placeholder'],
            'Add a comment...'
        )

    def test_comment_form_no_label(self):
        """Test comment form has no label"""
        form = CommentModelForm()
        self.assertEqual(form.fields['body'].label, '')


class PostIntegrationTest(TestCase):
    """Integration tests for Posts functionality"""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)

    def test_post_workflow(self):
        """Test complete post workflow: create, like, comment, delete"""
        self.client.login(username='user1', password='pass123')
        
        # Create post
        response = self.client.post(reverse('posts:main-post-view'), {
            'submit_p_form': '',
            'content': 'Integration test post'
        })
        post = Post.objects.get(content='Integration test post')
        
        # Add comment
        response = self.client.post(reverse('posts:main-post-view'), {
            'submit_c_form': '',
            'body': 'Test comment',
            'post_id': post.id
        })
        self.assertEqual(post.comment_set.count(), 1)
        
        # Like post
        self.client.login(username='user2', password='pass123')
        response = self.client.post(reverse('posts:like-post-view'), {
            'post_id': post.id
        })
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 1)
        
        # Delete post
        self.client.login(username='user1', password='pass123')
        response = self.client.post(
            reverse('posts:post-delete', kwargs={'pk': post.pk})
        )
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_multiple_users_liking_post(self):
        """Test multiple users can like the same post"""
        post = Post.objects.create(content="Popular post", author=self.profile1)
        
        # User 1 likes
        self.client.login(username='user1', password='pass123')
        self.client.post(reverse('posts:like-post-view'), {'post_id': post.id})
        
        # User 2 likes
        self.client.login(username='user2', password='pass123')
        self.client.post(reverse('posts:like-post-view'), {'post_id': post.id})
        
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 2)

    def test_post_feed_shows_all_posts(self):
        """Test post feed shows all posts in correct order"""
        Post.objects.create(content="First post", author=self.profile1)
        Post.objects.create(content="Second post", author=self.profile2)
        Post.objects.create(content="Third post", author=self.profile1)
        
        self.client.login(username='user1', password='pass123')
        response = self.client.get(reverse('posts:main-post-view'))
        
        posts = response.context['qs']
        self.assertEqual(posts.count(), 3)
        self.assertEqual(posts[0].content, "Third post")
        self.assertEqual(posts[2].content, "First post")
