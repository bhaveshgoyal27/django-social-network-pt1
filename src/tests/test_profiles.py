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
        from posts.models import Post
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
        from posts.models import Post, Like
        post = Post.objects.create(content="Test post", author=self.profile2)
        
        self.assertEqual(self.profile1.get_likes_given_no(), 0)
        
        Like.objects.create(user=self.profile1, post=post, value='Like')
        self.assertEqual(self.profile1.get_likes_given_no(), 1)

    def test_get_likes_received_no(self):
        """Test get_likes_received_no method"""
        from posts.models import Post
        post = Post.objects.create(content="Test post", author=self.profile1)
        
        self.assertEqual(self.profile1.get_likes_recieved_no(), 0)
        
        post.liked.add(self.profile2)
        self.assertEqual(self.profile1.get_likes_recieved_no(), 1)


class RelationshipModelTest(TestCase):
    """Test cases for Relationship model"""

    def setUp(self):
        self.user1 = User.objects.create_user(username='testuser1', password='testpass123')
        self.user2 = User.objects.create_user(username='testuser2', password='testpass123')
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)

    def test_relationship_creation(self):
        """Test relationship creation"""
        rel = Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        self.assertIsNotNone(rel)
        self.assertEqual(rel.sender, self.profile1)
        self.assertEqual(rel.receiver, self.profile2)
        self.assertEqual(rel.status, 'send')

    def test_relationship_str_method(self):
        """Test relationship string representation"""
        rel = Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        expected = f"{self.profile1}-{self.profile2}-send"
        self.assertEqual(str(rel), expected)

    def test_invitations_received_manager(self):
        """Test invitations_received manager method"""
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        invitations = Relationship.objects.invatations_received(self.profile2)
        self.assertEqual(invitations.count(), 1)
        self.assertEqual(invitations.first().sender, self.profile1)

    def test_accepted_relationship_adds_friends(self):
        """Test that accepting relationship adds users to friends"""
        rel = Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        self.assertNotIn(self.user2, self.profile1.friends.all())
        
        rel.status = 'accepted'
        rel.save()
        
        self.assertIn(self.user2, self.profile1.friends.all())
        self.assertIn(self.user1, self.profile2.friends.all())

    def test_relationship_deletion_removes_friends(self):
        """Test that deleting relationship removes friends"""
        rel = Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='accepted'
        )
        
        self.assertIn(self.user2, self.profile1.friends.all())
        
        rel.delete()
        
        self.assertNotIn(self.user2, self.profile1.friends.all())
        self.assertNotIn(self.user1, self.profile2.friends.all())


class ProfileManagerTest(TestCase):
    """Test cases for Profile Manager"""

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.user3 = User.objects.create_user(username='user3', password='pass123')
        self.user4 = User.objects.create_user(username='user4', password='pass123')
        
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)
        self.profile3 = Profile.objects.get(user=self.user3)
        self.profile4 = Profile.objects.get(user=self.user4)

    def test_get_all_profiles(self):
        """Test get_all_profiles manager method"""
        profiles = Profile.objects.get_all_profiles(self.user1)
        self.assertEqual(profiles.count(), 3)
        self.assertNotIn(self.profile1, profiles)

    def test_get_all_profiles_to_invite(self):
        """Test get_all_profiles_to_invite excludes accepted friends"""
        # User1 and User2 are friends
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='accepted'
        )
        
        available = Profile.objects.get_all_profiles_to_invite(self.user1)
        
        self.assertNotIn(self.profile1, available)
        self.assertNotIn(self.profile2, available)
        self.assertIn(self.profile3, available)
        self.assertIn(self.profile4, available)

    def test_get_all_profiles_to_invite_pending_included(self):
        """Test pending invitations are still available to invite"""
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        
        available = Profile.objects.get_all_profiles_to_invite(self.user1)
        self.assertIn(self.profile2, available)


class ProfileViewsTest(TestCase):
    """Test cases for Profile views"""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='testuser1', password='testpass123')
        self.user2 = User.objects.create_user(username='testuser2', password='testpass123')
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)

    def test_my_profile_view_requires_login(self):
        """Test my profile view requires authentication"""
        response = self.client.get(reverse('profiles:my-profile-view'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_my_profile_view_authenticated(self):
        """Test my profile view for authenticated user"""
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(reverse('profiles:my-profile-view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/myprofile.html')

    def test_my_profile_view_update(self):
        """Test profile update functionality"""
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.post(reverse('profiles:my-profile-view'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'bio': 'Updated bio',
        })
        self.profile1.refresh_from_db()
        self.assertEqual(self.profile1.first_name, 'John')
        self.assertEqual(self.profile1.last_name, 'Doe')
        self.assertEqual(self.profile1.bio, 'Updated bio')

    def test_profile_list_view_requires_login(self):
        """Test profile list view requires authentication"""
        response = self.client.get(reverse('profiles:all-profiles-view'))
        self.assertEqual(response.status_code, 302)

    def test_profile_list_view_authenticated(self):
        """Test profile list view for authenticated user"""
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(reverse('profiles:all-profiles-view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile_list.html')

    def test_profile_detail_view(self):
        """Test profile detail view"""
        self.client.login(username='testuser1', password='testpass123')
        self.profile2.first_name = "Jane"
        self.profile2.last_name = "Smith"
        self.profile2.save()
        
        response = self.client.get(
            reverse('profiles:profile-detail-view', kwargs={'slug': self.profile2.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/detail.html')

    def test_send_invitation(self):
        """Test sending friend invitation"""
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.post(reverse('profiles:send-invite'), {
            'profile_pk': self.profile2.pk
        })
        
        rel_exists = Relationship.objects.filter(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        ).exists()
        self.assertTrue(rel_exists)

    def test_accept_invitation(self):
        """Test accepting friend invitation"""
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        
        self.client.login(username='testuser2', password='testpass123')
        response = self.client.post(reverse('profiles:accept-invite'), {
            'profile_pk': self.profile1.pk
        })
        
        rel = Relationship.objects.get(sender=self.profile1, receiver=self.profile2)
        self.assertEqual(rel.status, 'accepted')

    def test_reject_invitation(self):
        """Test rejecting friend invitation"""
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        
        self.client.login(username='testuser2', password='testpass123')
        response = self.client.post(reverse('profiles:reject-invite'), {
            'profile_pk': self.profile1.pk
        })
        
        rel_exists = Relationship.objects.filter(
            sender=self.profile1,
            receiver=self.profile2
        ).exists()
        self.assertFalse(rel_exists)

    def test_remove_from_friends(self):
        """Test removing friend"""
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='accepted'
        )
        
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.post(reverse('profiles:remove-friend'), {
            'profile_pk': self.profile2.pk
        })
        
        rel_exists = Relationship.objects.filter(
            sender=self.profile1,
            receiver=self.profile2
        ).exists()
        self.assertFalse(rel_exists)

    def test_invites_received_view(self):
        """Test invites received view"""
        Relationship.objects.create(
            sender=self.profile1,
            receiver=self.profile2,
            status='send'
        )
        
        self.client.login(username='testuser2', password='testpass123')
        response = self.client.get(reverse('profiles:my-invites-view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.profile1, response.context['qs'])


class ProfileFormTest(TestCase):
    """Test cases for Profile forms"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_profile_form_valid(self):
        """Test profile form with valid data"""
        form = ProfileModelForm(data={
            'first_name': 'John',
            'last_name': 'Doe',
            'bio': 'Test bio',
        })
        self.assertTrue(form.is_valid())

    def test_profile_form_fields(self):
        """Test profile form has correct fields"""
        form = ProfileModelForm()
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)
        self.assertIn('bio', form.fields)
        self.assertIn('avatar', form.fields)


class UtilsTest(TestCase):
    """Test cases for utility functions"""

    def test_get_random_code(self):
        """Test random code generation"""
        code1 = get_random_code()
        code2 = get_random_code()
        
        self.assertEqual(len(code1), 8)
        self.assertEqual(len(code2), 8)
        self.assertNotEqual(code1, code2)
        self.assertTrue(code1.islower())


class ProfileContextProcessorTest(TestCase):
    """Test cases for context processors"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)

    def test_profile_pic_context_authenticated(self):
        """Test profile pic context processor for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profiles:my-profile-view'))
        self.assertIn('picture', response.context)

    def test_invitations_received_count_context(self):
        """Test invitations count context processor"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        profile2 = Profile.objects.get(user=user2)
        
        Relationship.objects.create(
            sender=profile2,
            receiver=self.profile,
            status='send'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profiles:my-profile-view'))
        self.assertEqual(response.context['invites_num'], 1)
