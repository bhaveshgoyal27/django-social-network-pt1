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


class SocialNetworkIntegrationTest(TestCase):
    """Integration tests for the entire social network"""

    def setUp(self):
        self.client = Client()
        # Create users
        self.user1 = User.objects.create_user(username='alice', password='pass123')
        self.user2 = User.objects.create_user(username='bob', password='pass123')
        self.user3 = User.objects.create_user(username='charlie', password='pass123')
        
        # Get profiles
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)
        self.profile3 = Profile.objects.get(user=self.user3)

    def test_complete_friend_workflow(self):
        """Test complete friend request workflow"""
        # Alice sends friend request to Bob
        self.client.login(username='alice', password='pass123')
        self.client.post(reverse('profiles:send-invite'), {
            'profile_pk': self.profile2.pk
        })
        
        # Verify request was sent
        self.assertTrue(
            Relationship.objects.filter(
                sender=self.profile1,
                receiver=self.profile2,
                status='send'
            ).exists()
        )
        
        # Bob accepts the request
        self.client.login(username='bob', password='pass123')
        self.client.post(reverse('profiles:accept-invite'), {
            'profile_pk': self.profile1.pk
        })
        
        # Verify they are now friends
        rel = Relationship.objects.get(sender=self.profile1, receiver=self.profile2)
        self.assertEqual(rel.status, 'accepted')
        self.assertIn(self.user2, self.profile1.friends.all())
        self.assertIn(self.user1, self.profile2.friends.all())

    def test_social_interaction_workflow(self):
        """Test complete social interaction: befriend, post, like, comment"""
        # 1. Users become friends
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='accepted'
        )
        
        # 2. Alice creates a post
        self.client.login(username='alice', password='pass123')
        self.client.post(reverse('posts:main-post-view'), {
            'submit_p_form': '',
            'content': 'Alice first post!'
        })
        post = Post.objects.get(content='Alice first post!')
        
        # 3. Bob likes the post
        self.client.login(username='bob', password='pass123')
        self.client.post(reverse('posts:like-post-view'), {
            'post_id': post.id
        })
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 1)
        
        # 4. Bob comments on the post
        self.client.post(reverse('posts:main-post-view'), {
            'submit_c_form': '',
            'body': 'Great post, Alice!',
            'post_id': post.id
        })
        self.assertEqual(post.num_comments(), 1)
        
        # 5. Charlie (not a friend) can also like and comment
        self.client.login(username='charlie', password='pass123')
        self.client.post(reverse('posts:like-post-view'), {
            'post_id': post.id
        })
        self.client.post(reverse('posts:main-post-view'), {
            'submit_c_form': '',
            'body': 'Nice!',
            'post_id': post.id
        })
        
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 2)
        self.assertEqual(post.num_comments(), 2)

    def test_unfriend_workflow(self):
        """Test unfriending workflow"""
        # Become friends
        rel = Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='accepted'
        )
        
        self.assertIn(self.user2, self.profile1.friends.all())
        
        # Alice removes Bob as friend
        self.client.login(username='alice', password='pass123')
        self.client.post(reverse('profiles:remove-friend'), {
            'profile_pk': self.profile2.pk
        })
        
        # Verify they are no longer friends
        self.assertFalse(
            Relationship.objects.filter(
                sender=self.profile1,
                receiver=self.profile2
            ).exists()
        )
        self.assertNotIn(self.user2, self.profile1.friends.all())
        self.assertNotIn(self.user1, self.profile2.friends.all())

    def test_reject_friend_request_workflow(self):
        """Test rejecting friend request"""
        # Alice sends request to Bob
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        
        # Bob rejects the request
        self.client.login(username='bob', password='pass123')
        self.client.post(reverse('profiles:reject-invite'), {
            'profile_pk': self.profile1.pk
        })
        
        # Verify relationship no longer exists
        self.assertFalse(
            Relationship.objects.filter(
                sender=self.profile1,
                receiver=self.profile2
            ).exists()
        )
        self.assertNotIn(self.user2, self.profile1.friends.all())

    def test_profile_stats_accuracy(self):
        """Test profile statistics are accurate"""
        self.client.login(username='alice', password='pass123')
        
        # Create posts
        for i in range(3):
            Post.objects.create(content=f"Post {i}", author=self.profile1)
        
        # Create likes
        post1 = Post.objects.create(content="Likeable post", author=self.profile2)
        post2 = Post.objects.create(content="Another post", author=self.profile2)
        
        Like.objects.create(user=self.profile1, post=post1, value='Like')
        Like.objects.create(user=self.profile1, post=post2, value='Like')
        
        # Get likes received
        alice_post = Post.objects.filter(author=self.profile1).first()
        alice_post.liked.add(self.profile2, self.profile3)
        
        # Add friends
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='accepted'
        )
        
        # Check stats
        self.assertEqual(self.profile1.get_posts_no(), 4)
        self.assertEqual(self.profile1.get_likes_given_no(), 2)
        self.assertEqual(self.profile1.get_likes_recieved_no(), 2)
        self.assertEqual(self.profile1.get_friends_no(), 1)

    def test_cascade_deletions(self):
        """Test that related objects are deleted properly"""
        # Create post with comments and likes
        post = Post.objects.create(content="Test post", author=self.profile1)
        Comment.objects.create(user=self.profile2, post=post, body="Comment")
        Like.objects.create(user=self.profile2, post=post, value='Like')
        
        # Delete post
        post_id = post.id
        post.delete()
        
        # Verify comments and likes are deleted
        self.assertFalse(Comment.objects.filter(post_id=post_id).exists())
        self.assertFalse(Like.objects.filter(post_id=post_id).exists())

    def test_user_deletion_cascade(self):
        """Test cascade when user is deleted"""
        # Create data
        post = Post.objects.create(content="Test", author=self.profile1)
        Comment.objects.create(user=self.profile1, post=post, body="Comment")
        
        user_id = self.user1.id
        profile_id = self.profile1.id
        
        # Delete user
        self.user1.delete()
        
        # Verify profile and related data deleted
        self.assertFalse(Profile.objects.filter(id=profile_id).exists())
        self.assertFalse(Post.objects.filter(author_id=profile_id).exists())


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


class EdgeCaseTest(TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_post_with_very_long_content(self):
        """Test post with very long content"""
        long_content = "a" * 10000
        post = Post.objects.create(content=long_content, author=self.profile)
        self.assertEqual(len(post.content), 10000)

    def test_empty_post_list(self):
        """Test viewing posts when none exist"""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('posts:main-post-view'))
        self.assertEqual(response.context['qs'].count(), 0)

    def test_post_str_with_short_content(self):
        """Test post string with content shorter than 20 chars"""
        post = Post.objects.create(content="Short", author=self.profile)
        self.assertEqual(str(post), "Short")

    def test_like_toggle_multiple_times(self):
        """Test toggling like multiple times"""
        post = Post.objects.create(content="Test", author=self.profile)
        
        self.client.login(username='testuser', password='pass123')
        
        # Like
        self.client.post(reverse('posts:like-post-view'), {'post_id': post.id})
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 1)
        
        # Unlike
        self.client.post(reverse('posts:like-post-view'), {'post_id': post.id})
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 0)
        
        # Like again
        self.client.post(reverse('posts:like-post-view'), {'post_id': post.id})
        post.refresh_from_db()
        self.assertEqual(post.num_likes(), 1)

    def test_profile_with_no_name(self):
        """Test profile slug generation with no first/last name"""
        profile = self.profile
        profile.first_name = ""
        profile.last_name = ""
        profile.save()
        
        self.assertEqual(profile.slug, str(self.user))

    def test_duplicate_friend_request(self):
        """Test sending duplicate friend requests"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        
        # Send first request
        Relationship.objects.create(
            sender=self.profile,
            receiver=profile2,
            status='send'
        )
        
        # Verify only one relationship exists
        count = Relationship.objects.filter(
            sender=self.profile,
            receiver=profile2
        ).count()
        self.assertEqual(count, 1)

    def test_get_all_profiles_to_invite_bidirectional(self):
        """Test profile invitation list with bidirectional relationships"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        user3 = User.objects.create_user(username='user3', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        profile3 = Profile.objects.get(user=user3)
        
        # Profile1 sends to Profile2, they accept
        Relationship.objects.create(
            sender=self.profile,
            receiver=profile2,
            status='accepted'
        )
        
        # Profile3 sends to Profile1 (pending)
        Relationship.objects.create(
            sender=profile3,
            receiver=self.profile,
            status='send'
        )
        
        available = Profile.objects.get_all_profiles_to_invite(self.user)
        
        # Should not include profile2 (already friends)
        self.assertNotIn(profile2, available)
        # Should include profile3 (only pending)
        self.assertIn(profile3, available)


class ModelMethodTest(TestCase):
    """Additional tests for model methods"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_get_all_authors_posts(self):
        """Test get_all_authors_posts method"""
        Post.objects.create(content="Post 1", author=self.profile)
        Post.objects.create(content="Post 2", author=self.profile)
        Post.objects.create(content="Post 3", author=self.profile)
        
        posts = self.profile.get_all_authors_posts()
        self.assertEqual(posts.count(), 3)

    def test_profile_initial_values(self):
        """Test profile stores initial first and last name"""
        profile = self.profile
        self.assertEqual(profile._Profile__initial_first_name, profile.first_name)
        self.assertEqual(profile._Profile__initial_last_name, profile.last_name)

    def test_like_value_toggle(self):
        """Test like value can be toggled"""
        post = Post.objects.create(content="Test", author=self.profile)
        like = Like.objects.create(user=self.profile, post=post, value='Like')
        
        like.value = 'Unlike'
        like.save()
        
        like.refresh_from_db()
        self.assertEqual(like.value, 'Unlike')
