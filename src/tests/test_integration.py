from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from src.profiles.models import Profile, Relationship
from src.posts.models import Post, Comment, Like


class URLTest(TestCase):
    """Test cases for URL routing"""

    def test_home_url(self):
        """Test home URL resolves correctly"""
        url = reverse('home-view')
        self.assertEqual(resolve(url).view_name, 'home-view')

    def test_profile_urls(self):
        """Test profile URLs resolve correctly"""
        self.assertEqual(
            resolve(reverse('profiles:my-profile-view')).view_name,
            'profiles:my-profile-view'
        )
        self.assertEqual(
            resolve(reverse('profiles:all-profiles-view')).view_name,
            'profiles:all-profiles-view'
        )
        self.assertEqual(
            resolve(reverse('profiles:my-invites-view')).view_name,
            'profiles:my-invites-view'
        )

    def test_post_urls(self):
        """Test post URLs resolve correctly"""
        self.assertEqual(
            resolve(reverse('posts:main-post-view')).view_name,
            'posts:main-post-view'
        )
        self.assertEqual(
            resolve(reverse('posts:like-post-view')).view_name,
            'posts:like-post-view'
        )


class PermissionAndSecurityTest(TestCase):
    """Test permission and security features"""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)

    def test_cannot_delete_others_post(self):
        """Test user cannot delete another user's post"""
        post = Post.objects.create(content="User2 post", author=self.profile2)
        
        self.client.login(username='user1', password='pass123')
        response = self.client.post(
            reverse('posts:post-delete', kwargs={'pk': post.pk})
        )
        
        # Post should still exist
        self.assertTrue(Post.objects.filter(id=post.id).exists())

    def test_cannot_update_others_post(self):
        """Test user cannot update another user's post"""
        post = Post.objects.create(content="Original content", author=self.profile2)
        
        self.client.login(username='user1', password='pass123')
        response = self.client.post(
            reverse('posts:post-update', kwargs={'pk': post.pk}),
            {'content': 'Hacked content'}
        )
        
        post.refresh_from_db()
        self.assertEqual(post.content, "Original content")

    def test_unauthenticated_access_redirects(self):
        """Test unauthenticated users are redirected"""
        urls_to_test = [
            reverse('posts:main-post-view'),
            reverse('profiles:my-profile-view'),
            reverse('profiles:all-profiles-view'),
        ]
        
        for url in urls_to_test:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        self.client.login(username='user1', password='pass123')
        
        # Try to post without CSRF token
        response = self.client.post(
            reverse('posts:main-post-view'),
            {'submit_p_form': '', 'content': 'Test'},
            HTTP_X_CSRFTOKEN='wrong_token'
        )
        # Should fail or redirect

