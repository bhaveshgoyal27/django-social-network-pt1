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
