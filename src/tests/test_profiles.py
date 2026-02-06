from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from src.profiles.models import Profile, Relationship
from src.profiles.forms import ProfileModelForm
from src.profiles.utils import get_random_code


class ProfileModelTest(TestCase):
    """Test cases for Profile model"""

    def setUp(self):
        self.user1 = User.objects.create_user(username='testuser1', password='testpass123')
        self.user2 = User.objects.create_user(username='testuser2', password='testpass123')
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)

    def test_profile_creation(self):
        """Test that profile is created automatically when user is created"""
        self.assertIsNotNone(self.profile1)
        self.assertEqual(self.profile1.user, self.user1)

    def test_profile_str_method(self):
        """Test profile string representation"""
        expected = f"{self.user1.username}-{self.profile1.created}"
        self.assertEqual(str(self.profile1), expected)

    def test_profile_default_bio(self):
        """Test default bio is set"""
        self.assertEqual(self.profile1.bio, "no bio..")

    def test_profile_slug_generation(self):
        """Test slug is generated correctly"""
        self.profile1.first_name = "John"
        self.profile1.last_name = "Doe"
        self.profile1.save()
        self.assertEqual(self.profile1.slug, "john-doe")

    def test_profile_slug_uniqueness(self):
        """Test slug uniqueness when duplicate names exist"""
        self.profile1.first_name = "John"
        self.profile1.last_name = "Doe"
        self.profile1.save()
        
        self.profile2.first_name = "John"
        self.profile2.last_name = "Doe"
        self.profile2.save()
        
        self.assertNotEqual(self.profile1.slug, self.profile2.slug)

    def test_get_friends(self):
        """Test get_friends method"""
        self.profile1.friends.add(self.user2)
        friends = self.profile1.get_friends()
        self.assertIn(self.user2, friends)

    def test_get_friends_no(self):
        """Test get_friends_no method"""
        self.assertEqual(self.profile1.get_friends_no(), 0)
        self.profile1.friends.add(self.user2)
        self.assertEqual(self.profile1.get_friends_no(), 1)

    def test_get_posts_no(self):
        """Test get_posts_no method"""
        from src.posts.models import Post
        self.assertEqual(self.profile1.get_posts_no(), 0)
        Post.objects.create(content="Test post", author=self.profile1)
        self.assertEqual(self.profile1.get_posts_no(), 1)

    def test_get_absolute_url(self):
        """Test get_absolute_url method"""
        self.profile1.first_name = "John"
        self.profile1.last_name = "Doe"
        self.profile1.save()
        expected_url = reverse("profiles:profile-detail-view", kwargs={"slug": self.profile1.slug})
        self.assertEqual(self.profile1.get_absolute_url(), expected_url)

    def test_get_likes_given_no(self):
        """Test get_likes_given_no method"""
        from src.posts.models import Post, Like
        post = Post.objects.create(content="Test post", author=self.profile2)
        
        self.assertEqual(self.profile1.get_likes_given_no(), 0)
        
        Like.objects.create(user=self.profile1, post=post, value='Like')
        self.assertEqual(self.profile1.get_likes_given_no(), 1)

    def test_get_likes_received_no(self):
        """Test get_likes_received_no method"""
        from src.posts.models import Post
        post = Post.objects.create(content="Test post", author=self.profile1)
        
        self.assertEqual(self.profile1.get_likes_recieved_no(), 0)
        
        post.liked.add(self.profile2)
        self.assertEqual(self.profile1.get_likes_recieved_no(), 1)
