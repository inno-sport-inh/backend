import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

logger = logging.getLogger('api_deprecation')


class APIDeprecationMiddleware(MiddlewareMixin):
    """
    Middleware для отслеживания использования устаревшего API и добавления 
    заголовков о deprecation
    """
    
    # URL паттерны старого API, которые нужно помечать как deprecated
    DEPRECATED_PATTERNS = [
        '/api/profile/',
        '/api/enrollment/',
        '/api/group/',
        '/api/training/',
        '/api/attendance/',
        '/api/calendar/',
        '/api/reference/',
        '/api/selfsport/',
        '/api/fitnesstest/',
        '/api/measurement/',
        '/api/semester',
        '/api/analytics/',
        '/api/medical_groups/',
    ]
    
    # Новые URL для миграции
    URL_MAPPING = {
        '/api/profile/student': '/api/v2/profile/student/',
        '/api/profile/change_gender': '/api/v2/profile/change-gender/',
        '/api/profile/QR/toggle': '/api/v2/profile/toggle-qr/',
        '/api/enrollment/enroll': '/api/v2/enrollment/enroll/',
        '/api/enrollment/unenroll': '/api/v2/enrollment/unenroll/',
        '/api/enrollment/unenroll_by_trainer': '/api/v2/enrollment/unenroll-by-trainer/',
        '/api/select_sport': '/api/v2/group/select-sport/',
        '/api/sports': '/api/v2/group/sports/',
        '/api/calendar/trainings': '/api/v2/calendar/trainings/',
        '/api/reference/upload': '/api/v2/reference/upload/',
        '/api/selfsport/upload': '/api/v2/selfsport/upload/',
        '/api/selfsport/types': '/api/v2/selfsport/types/',
        '/api/selfsport/strava_parsing': '/api/v2/selfsport/strava-parsing/',
        '/api/fitnesstest/result': '/api/v2/fitnesstest/result/',
        '/api/fitnesstest/upload': '/api/v2/fitnesstest/upload/',
        '/api/fitnesstest/exercises': '/api/v2/fitnesstest/exercises/',
        '/api/fitnesstest/sessions': '/api/v2/fitnesstest/sessions/',
        '/api/measurement/student_measurement': '/api/v2/measurement/student-measurement/',
        '/api/measurement/get_results': '/api/v2/measurement/results/',
        '/api/measurement/get_measurements': '/api/v2/measurement/measurements/',
        '/api/semester': '/api/v2/semester/',
        '/api/analytics/attendance': '/api/v2/analytics/attendance/',
        '/api/medical_groups/': '/api/v2/medical_groups/',
    }

    def process_request(self, request):
        """
        Обрабатывает входящие запросы и логирует использование устаревшего API
        """
        path = request.path
        
        # Проверяем, является ли запрос к устаревшему API
        if self._is_deprecated_api(path):
            # Логируем использование устаревшего API
            self._log_deprecated_usage(request)
            
            # Добавляем информацию о deprecation в request для дальнейшего использования
            request.is_deprecated_api = True
            request.suggested_url = self._get_suggested_url(path)
        else:
            request.is_deprecated_api = False
            
        return None
    
    def process_response(self, request, response):
        """
        Добавляет заголовки deprecation к ответам устаревшего API
        """
        if hasattr(request, 'is_deprecated_api') and request.is_deprecated_api:
            # Добавляем заголовки deprecation
            response['Deprecation'] = 'true'
            response['Sunset'] = '2025-12-31'  # Дата планируемого удаления API
            response['Link'] = f'<{request.suggested_url}>; rel="successor-version"'
            response['Warning'] = '299 - "This API version is deprecated. Please migrate to v2."'
            
            # Добавляем custom заголовки
            response['X-API-Deprecated'] = 'This endpoint is deprecated'
            response['X-API-Migration-Guide'] = 'https://docs.example.com/api-migration'
            
            if request.suggested_url:
                response['X-API-New-Endpoint'] = request.suggested_url
        
        return response
    
    def _is_deprecated_api(self, path):
        """
        Проверяет, является ли путь частью устаревшего API
        """
        # Исключаем новое API v2 и документацию
        if path.startswith('/api/v2/') or path.startswith('/api/docs') or path.startswith('/api/openapi'):
            return False
            
        # Проверяем паттерны устаревшего API
        return any(path.startswith(pattern) for pattern in self.DEPRECATED_PATTERNS)
    
    def _get_suggested_url(self, path):
        """
        Возвращает предлагаемый новый URL для миграции
        """
        # Прямое соответствие
        if path in self.URL_MAPPING:
            return self.URL_MAPPING[path]
        
        # Динамические URL с параметрами
        for old_pattern, new_pattern in self.URL_MAPPING.items():
            if old_pattern in path:
                # Простая замена для базовых случаев
                return path.replace('/api/', '/api/v2/', 1)
        
        # Общая замена для неизвестных URL
        return path.replace('/api/', '/api/v2/', 1)
    
    def _log_deprecated_usage(self, request):
        """
        Логирует использование устаревшего API
        """
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        ip_address = self._get_client_ip(request)
        user = getattr(request, 'user', None)
        user_id = user.id if user and user.is_authenticated else 'anonymous'
        
        logger.warning(
            f"Deprecated API usage: {request.method} {request.path} | "
            f"User: {user_id} | IP: {ip_address} | UA: {user_agent} | "
            f"Suggested: {self._get_suggested_url(request.path)}"
        )
    
    def _get_client_ip(self, request):
        """
        Получает IP адрес клиента
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class APIMetricsMiddleware(MiddlewareMixin):
    """
    Middleware для сбора метрик использования API
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Логируем метрики
            api_version = 'v2' if request.path.startswith('/api/v2/') else 'v1'
            is_deprecated = getattr(request, 'is_deprecated_api', False)
            
            logger.info(
                f"API Request: {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration:.3f}s | "
                f"Version: {api_version} | "
                f"Deprecated: {is_deprecated}"
            )
        
        return response
