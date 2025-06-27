"""
Тесты для нового API v2
"""

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User

from sport.models import Student, Semester, Group, Sport, MedicalGroup
from api.viewsets import ProfileViewSet, EnrollmentViewSet


class APIv2BaseTestCase(APITestCase):
    """
    Базовый класс для тестов API v2
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Создаем тестового пользователя и студента
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Создаем медицинскую группу
        self.medical_group = MedicalGroup.objects.create(
            name='Основная группа',
            allowed_load=100
        )
        
        # Создаем спорт
        self.sport = Sport.objects.create(name='Футбол')
        
        # Создаем студента
        self.student = Student.objects.create(
            user=self.user,
            gender='M',
            medical_group=self.medical_group,
            sport=self.sport,
            has_QR=True
        )
        
        # Создаем семестр
        self.semester = Semester.objects.create(
            name='Осень 2025',
            year=2025,
            is_active=True
        )
        
        # Создаем группу
        self.group = Group.objects.create(
            sport=self.sport,
            semester=self.semester,
            name='Футбол-1',
            capacity=20
        )
        self.group.allowed_medical_groups.add(self.medical_group)
        
        # Аутентифицируем пользователя
        self.client.force_authenticate(user=self.user)


class ProfileViewSetTestCase(APIv2BaseTestCase):
    """
    Тесты для ProfileViewSet
    """
    
    def test_get_student_info(self):
        """
        Тест получения информации о студенте
        """
        url = reverse('profile-student-info')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['gender'], 'M')
        self.assertTrue(response.data['has_QR'])
    
    def test_toggle_qr_presence(self):
        """
        Тест переключения QR статуса
        """
        url = reverse('profile-toggle-qr-presence')
        initial_qr_status = self.student.has_QR
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Обновляем студента из БД
        self.student.refresh_from_db()
        self.assertNotEqual(self.student.has_QR, initial_qr_status)
    
    def test_get_history(self):
        """
        Тест получения истории тренировок
        """
        url = reverse('profile-history', kwargs={'semester_id': self.semester.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class EnrollmentViewSetTestCase(APIv2BaseTestCase):
    """
    Тесты для EnrollmentViewSet
    """
    
    def test_successful_enrollment(self):
        """
        Тест успешной записи на курс
        """
        url = reverse('enrollment-enroll')
        data = {'group_id': self.group.id}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что запись создалась
        from sport.models import Enroll
        self.assertTrue(
            Enroll.objects.filter(
                student=self.student,
                group=self.group
            ).exists()
        )
    
    def test_double_enrollment_error(self):
        """
        Тест ошибки при повторной записи
        """
        # Сначала записываемся
        from sport.models import Enroll
        Enroll.objects.create(student=self.student, group=self.group)
        
        url = reverse('enrollment-enroll')
        data = {'group_id': self.group.id}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_code'], 4)  # DOUBLE_ENROLL
    
    def test_sport_mismatch_error(self):
        """
        Тест ошибки при несоответствии спорта
        """
        # Создаем другой спорт и группу
        other_sport = Sport.objects.create(name='Баскетбол')
        other_group = Group.objects.create(
            sport=other_sport,
            semester=self.semester,
            name='Баскетбол-1',
            capacity=20
        )
        other_group.allowed_medical_groups.add(self.medical_group)
        
        url = reverse('enrollment-enroll')
        data = {'group_id': other_group.id}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_code'], 8)  # SPORT_ERROR


class APIDeprecationTestCase(APITestCase):
    """
    Тесты для middleware deprecation
    """
    
    def setUp(self):
        self.client = APIClient()
    
    def test_old_api_deprecation_headers(self):
        """
        Тест добавления заголовков deprecation для старого API
        """
        # Предполагаем, что у нас есть старый эндпоинт
        response = self.client.get('/api/profile/student')
        
        # Проверяем наличие заголовков deprecation
        self.assertIn('Deprecation', response)
        self.assertIn('Sunset', response)
        self.assertIn('X-API-Deprecated', response)
        self.assertEqual(response['Deprecation'], 'true')
    
    def test_new_api_no_deprecation_headers(self):
        """
        Тест отсутствия заголовков deprecation для нового API
        """
        response = self.client.get('/api/v2/profile/student/')
        
        # Проверяем отсутствие заголовков deprecation
        self.assertNotIn('Deprecation', response)
        self.assertNotIn('X-API-Deprecated', response)


class URLMappingTestCase(TestCase):
    """
    Тесты для корректности маппинга URL-ов
    """
    
    def test_url_patterns_exist(self):
        """
        Тест существования всех новых URL паттернов
        """
        from django.urls import reverse, NoReverseMatch
        
        # Список основных URL паттернов, которые должны существовать
        url_patterns = [
            'profile-student-info',
            'profile-toggle-qr-presence',
            'enrollment-enroll',
            'enrollment-unenroll',
        ]
        
        for pattern_name in url_patterns:
            try:
                url = reverse(pattern_name)
                self.assertIsNotNone(url)
            except NoReverseMatch:
                self.fail(f"URL pattern '{pattern_name}' not found")


@pytest.mark.integration
class APIIntegrationTestCase(APIv2BaseTestCase):
    """
    Интеграционные тесты для API v2
    """
    
    def test_full_enrollment_workflow(self):
        """
        Тест полного флоу записи на курс
        """
        # 1. Получаем информацию о студенте
        profile_url = reverse('profile-student-info')
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        
        # 2. Получаем список доступных групп
        groups_url = reverse('group-sports')
        groups_response = self.client.get(groups_url)
        self.assertEqual(groups_response.status_code, status.HTTP_200_OK)
        
        # 3. Записываемся на курс
        enroll_url = reverse('enrollment-enroll')
        enroll_data = {'group_id': self.group.id}
        enroll_response = self.client.post(enroll_url, enroll_data, format='json')
        self.assertEqual(enroll_response.status_code, status.HTTP_200_OK)
        
        # 4. Проверяем, что запись создалась
        from sport.models import Enroll
        self.assertTrue(
            Enroll.objects.filter(
                student=self.student,
                group=self.group
            ).exists()
        )
        
        # 5. Получаем историю тренировок
        history_url = reverse('profile-history', kwargs={'semester_id': self.semester.id})
        history_response = self.client.get(history_url)
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)


# Примеры для pytest
@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(api_client):
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    return user


@pytest.mark.django_db
def test_profile_endpoint(api_client, authenticated_user):
    """
    Pytest тест для профиля
    """
    url = reverse('profile-student-info')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['user']['username'] == 'testuser'


@pytest.mark.django_db
def test_enrollment_endpoint(api_client, authenticated_user):
    """
    Pytest тест для записи на курс
    """
    # Создаем необходимые объекты
    medical_group = MedicalGroup.objects.create(name='Основная', allowed_load=100)
    sport = Sport.objects.create(name='Футбол')
    student = Student.objects.create(
        user=authenticated_user,
        gender='M',
        medical_group=medical_group,
        sport=sport
    )
    semester = Semester.objects.create(name='Осень 2025', year=2025, is_active=True)
    group = Group.objects.create(
        sport=sport,
        semester=semester,
        name='Футбол-1',
        capacity=20
    )
    group.allowed_medical_groups.add(medical_group)
    
    url = reverse('enrollment-enroll')
    data = {'group_id': group.id}
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_200_OK


if __name__ == '__main__':
    # Запуск тестов
    pytest.main([__file__, '-v'])
