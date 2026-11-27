
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Task


class TodoApplicationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPassword123'
        )

        self.other_user = User.objects.create_user(
            username='otheruser',
            password='TestPassword123'
        )

        self.task = Task.objects.create(
            user=self.user,
            title='Test Task',
            description='Testing task functionality',
            priority='High',
            category='Work'
        )

    def test_user_registration_page(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_user_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'TestPassword123'
        })

        self.assertEqual(response.status_code, 302)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_only_user_tasks(self):
        self.client.login(
            username='testuser',
            password='TestPassword123'
        )

        Task.objects.create(
            user=self.other_user,
            title='Other User Task'
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task')
        self.assertNotContains(response, 'Other User Task')

    def test_task_edit_requires_ownership(self):
        self.client.login(
            username='otheruser',
            password='TestPassword123'
        )

        response = self.client.get(
            reverse('edit_task', args=[self.task.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_task_delete_requires_ownership(self):
        self.client.login(
            username='otheruser',
            password='TestPassword123'
        )

        response = self.client.post(
            reverse('delete_task', args=[self.task.id])
        )

        self.assertTrue(
            Task.objects.filter(id=self.task.id).exists()
        )

    def test_task_toggle_requires_ownership(self):
        self.client.login(
            username='otheruser',
            password='TestPassword123'
        )

        response = self.client.post(
            reverse('toggle_task_status', args=[self.task.id])
        )

        self.task.refresh_from_db()

        self.assertFalse(self.task.status)

    def test_user_can_access_own_task(self):
        self.client.login(
            username='testuser',
            password='TestPassword123'
        )

        response = self.client.get(
            reverse('edit_task', args=[self.task.id])
        )

        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('edit_profile'))
        self.assertEqual(response.status_code, 302)

    def test_password_change_requires_login(self):
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 302)
