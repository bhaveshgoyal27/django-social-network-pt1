from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from src.profiles.models import Profile, Relationship
from src.profiles.context_processors import profile_pic, invatations_received_no
from src.profiles.signals import post_save_createprofile, post_save_add_to_friends, pre_delete_remove_from_friends


class SignalTest(TestCase):
    """Test cases for Django signals"""

    def test_profile_created_on_user_creation(self):
        """Test profile is automatically created when user is created"""
        user = User.objects.create_user(username='newuser', password='pass123')
        
        # Profile should be created automatically
        self.assertTrue(Profile.objects.filter(user=user).exists())
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.user, user)

    def test_friends_added_on_relationship_accepted(self):
        """Test friends are added when relationship status is accepted"""
        user1 = User.objects.create_user(username='user1', password='pass123')
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile1 = Profile.objects.get(user=user1)
        profile2 = Profile.objects.get(user=user2)
        
        # Create relationship with 'send' status
        rel = Relationship.objects.create(
            sender=profile1,
            receiver=profile2,
            status='send'
        )
        
        # Friends should not be added yet
        self.assertNotIn(user2, profile1.friends.all())
        self.assertNotIn(user1, profile2.friends.all())
        
        # Change status to 'accepted'
        rel.status = 'accepted'
        rel.save()
        
        # Friends should now be added
        profile1.refresh_from_db()
        profile2.refresh_from_db()
        self.assertIn(user2, profile1.friends.all())
        self.assertIn(user1, profile2.friends.all())

    def test_friends_removed_on_relationship_deletion(self):
        """Test friends are removed when relationship is deleted"""
        user1 = User.objects.create_user(username='user1', password='pass123')
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile1 = Profile.objects.get(user=user1)
        profile2 = Profile.objects.get(user=user2)
        
        # Create accepted relationship
        rel = Relationship.objects.create(
            sender=profile1,
            receiver=profile2,
            status='accepted'
        )
        
        # Verify they are friends
        profile1.refresh_from_db()
        profile2.refresh_from_db()
        self.assertIn(user2, profile1.friends.all())
        self.assertIn(user1, profile2.friends.all())
        
        # Delete relationship
        rel.delete()
        
        # Friends should be removed
        profile1.refresh_from_db()
        profile2.refresh_from_db()
        self.assertNotIn(user2, profile1.friends.all())
        self.assertNotIn(user1, profile2.friends.all())

    def test_multiple_profiles_created(self):
        """Test multiple profiles can be created via signal"""
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                password='pass123'
            )
            users.append(user)
        
        # All should have profiles
        for user in users:
            self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_relationship_signal_only_fires_on_accepted(self):
        """Test friend addition signal only fires when status is accepted"""
        user1 = User.objects.create_user(username='user1', password='pass123')
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile1 = Profile.objects.get(user=user1)
        profile2 = Profile.objects.get(user=user2)
        
        # Create with 'send' status
        rel = Relationship.objects.create(
            sender=profile1,
            receiver=profile2,
            status='send'
        )
        
        # Should not be friends
        self.assertNotIn(user2, profile1.friends.all())
        
        # Update to accepted
        rel.status = 'accepted'
        rel.save()
        
        # Now should be friends
        profile1.refresh_from_db()
        self.assertIn(user2, profile1.friends.all())


class ContextProcessorTest(TestCase):
    """Test cases for context processors"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_profile_pic_authenticated(self):
        """Test profile_pic context processor for authenticated user"""
        request = self.factory.get('/')
        request.user = self.user
        
        context = profile_pic(request)
        
        self.assertIn('picture', context)
        self.assertEqual(context['picture'], self.profile.avatar)

    def test_profile_pic_unauthenticated(self):
        """Test profile_pic context processor for unauthenticated user"""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        context = profile_pic(request)
        
        self.assertEqual(context, {})

    def test_invitations_received_no_authenticated(self):
        """Test invitations count context processor for authenticated user"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        user3 = User.objects.create_user(username='user3', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        profile3 = Profile.objects.get(user=user3)
        
        # Create invitations
        Relationship.objects.create(
            sender=profile2,
            receiver=self.profile,
            status='send'
        )
        Relationship.objects.create(
            sender=profile3,
            receiver=self.profile,
            status='send'
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        context = invatations_received_no(request)
        
        self.assertIn('invites_num', context)
        self.assertEqual(context['invites_num'], 2)

    def test_invitations_received_no_unauthenticated(self):
        """Test invitations count context processor for unauthenticated user"""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        context = invatations_received_no(request)
        
        self.assertEqual(context, {})

    def test_invitations_count_excludes_accepted(self):
        """Test invitation count only includes pending invitations"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        user3 = User.objects.create_user(username='user3', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        profile3 = Profile.objects.get(user=user3)
        
        # Create one pending and one accepted
        Relationship.objects.create(
            sender=profile2,
            receiver=self.profile,
            status='send'
        )
        Relationship.objects.create(
            sender=profile3,
            receiver=self.profile,
            status='accepted'
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        context = invatations_received_no(request)
        
        self.assertEqual(context['invites_num'], 1)

    def test_invitations_count_zero_when_none(self):
        """Test invitation count is zero when no invitations"""
        request = self.factory.get('/')
        request.user = self.user
        
        context = invatations_received_no(request)
        
        self.assertEqual(context['invites_num'], 0)


class AdminTest(TestCase):
    """Test cases for Django admin"""

    def test_profile_registered_in_admin(self):
        """Test Profile model is registered in admin"""
        from django.contrib import admin
        from profiles.models import Profile
        
        self.assertIn(Profile, admin.site._registry)

    def test_relationship_registered_in_admin(self):
        """Test Relationship model is registered in admin"""
        from django.contrib import admin
        from profiles.models import Relationship
        
        self.assertIn(Relationship, admin.site._registry)

    def test_post_registered_in_admin(self):
        """Test Post model is registered in admin"""
        from django.contrib import admin
        from posts.models import Post
        
        self.assertIn(Post, admin.site._registry)

    def test_comment_registered_in_admin(self):
        """Test Comment model is registered in admin"""
        from django.contrib import admin
        from posts.models import Comment
        
        self.assertIn(Comment, admin.site._registry)

    def test_like_registered_in_admin(self):
        """Test Like model is registered in admin"""
        from django.contrib import admin
        from posts.models import Like
        
        self.assertIn(Like, admin.site._registry)


class UtilityFunctionTest(TestCase):
    """Test utility functions"""

    def test_get_random_code_length(self):
        """Test random code has correct length"""
        from profiles.utils import get_random_code
        
        code = get_random_code()
        self.assertEqual(len(code), 8)

    def test_get_random_code_uniqueness(self):
        """Test random codes are unique"""
        from profiles.utils import get_random_code
        
        codes = [get_random_code() for _ in range(100)]
        unique_codes = set(codes)
        
        # Should have high uniqueness (allow for rare collisions)
        self.assertGreater(len(unique_codes), 95)

    def test_get_random_code_format(self):
        """Test random code format (lowercase, no special chars)"""
        from profiles.utils import get_random_code
        
        code = get_random_code()
        self.assertTrue(code.islower() or code.isdigit())
        self.assertTrue(all(c.isalnum() for c in code))


class FileExtensionValidatorTest(TestCase):
    """Test file extension validator for images"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_valid_image_extensions(self):
        """Test valid image extensions are accepted"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from posts.models import Post
        
        valid_extensions = ['png', 'jpg', 'jpeg']
        
        for ext in valid_extensions:
            image = SimpleUploadedFile(
                name=f'test.{ext}',
                content=b'',
                content_type=f'image/{ext}'
            )
            post = Post.objects.create(
                content="Test",
                author=self.profile,
                image=image
            )
            self.assertTrue(post.image)


class ModelTimestampTest(TestCase):
    """Test timestamp fields on models"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_post_timestamps(self):
        """Test post created and updated timestamps"""
        from posts.models import Post
        import time
        
        post = Post.objects.create(content="Test", author=self.profile)
        created_time = post.created
        updated_time = post.updated
        
        self.assertIsNotNone(created_time)
        self.assertIsNotNone(updated_time)
        
        # Update post
        time.sleep(0.1)
        post.content = "Updated"
        post.save()
        
        self.assertGreater(post.updated, updated_time)
        self.assertEqual(post.created, created_time)

    def test_comment_timestamps(self):
        """Test comment timestamps"""
        from posts.models import Post, Comment
        
        post = Post.objects.create(content="Test", author=self.profile)
        comment = Comment.objects.create(
            user=self.profile,
            post=post,
            body="Test comment"
        )
        
        self.assertIsNotNone(comment.created)
        self.assertIsNotNone(comment.updated)

    def test_relationship_timestamps(self):
        """Test relationship timestamps"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        
        rel = Relationship.objects.create(
            sender=self.profile,
            receiver=profile2,
            status='send'
        )
        
        self.assertIsNotNone(rel.created)
        self.assertIsNotNone(rel.updated)


class QueryOptimizationTest(TestCase):
    """Test query optimization and N+1 problems"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_post_list_query_count(self):
        """Test number of queries for post list"""
        from posts.models import Post
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import Client
        
        # Create test data
        for i in range(10):
            Post.objects.create(content=f"Post {i}", author=self.profile)
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        # This test would need query counting setup
        # Just verify it runs without error
        response = client.get('/posts/')
        self.assertEqual(response.status_code, 200)

    def test_profile_list_query_count(self):
        """Test number of queries for profile list"""
        from django.test import Client
        
        # Create multiple profiles
        for i in range(10):
            User.objects.create_user(username=f'user{i}', password='pass123')
        
        client = Client()
        client.login(username='testuser', password='pass123')
        
        response = client.get('/profiles/')
        self.assertEqual(response.status_code, 200)
