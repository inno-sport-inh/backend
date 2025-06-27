# Пример конфигурации для settings.py

# Добавьте в MIDDLEWARE после существующих middleware
MIDDLEWARE = [
    # ... существующие middleware ...
    'api.middleware.APIDeprecationMiddleware',
    'api.middleware.APIMetricsMiddleware',
]

# Настройка логирования для отслеживания deprecation
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'api_deprecation': {
            'format': '[API DEPRECATION] {asctime} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_api_deprecation': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/api_deprecation.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'api_deprecation',
        },
        'file_api_metrics': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/api_metrics.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'api_deprecation': {
            'handlers': ['file_api_deprecation', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'api.middleware': {
            'handlers': ['file_api_metrics'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# API настройки
API_SETTINGS = {
    # Дата планируемого удаления старого API (RFC 3339)
    'SUNSET_DATE': '2025-12-31T23:59:59Z',
    
    # URL документации по миграции
    'MIGRATION_GUIDE_URL': 'https://docs.example.com/api-migration',
    
    # Включить/выключить deprecation headers
    'ENABLE_DEPRECATION_HEADERS': True,
    
    # Включить/выключить логирование
    'ENABLE_DEPRECATION_LOGGING': True,
    
    # Включить/выключить метрики
    'ENABLE_API_METRICS': True,
}

# Настройки DRF для нового API
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# Настройки для drf-spectacular (OpenAPI документация)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Sport Management API',
    'DESCRIPTION': 'API for managing sports activities, enrollments, and training sessions',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v2/',
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'filter': True,
    },
    'TAGS': [
        {'name': 'Profile', 'description': 'User profile operations'},
        {'name': 'Enrollment', 'description': 'Group enrollment operations'},
        {'name': 'Groups', 'description': 'Group management'},
        {'name': 'Training', 'description': 'Training session operations'},
        {'name': 'Attendance', 'description': 'Attendance tracking'},
        {'name': 'Calendar', 'description': 'Calendar and scheduling'},
        {'name': 'References', 'description': 'Reference document management'},
        {'name': 'Self Sport', 'description': 'Self sport reporting'},
        {'name': 'Fitness Test', 'description': 'Fitness testing'},
        {'name': 'Measurement', 'description': 'Body measurements'},
        {'name': 'Semester', 'description': 'Semester management'},
        {'name': 'Analytics', 'description': 'Analytics and reporting'},
        {'name': 'Medical Groups', 'description': 'Medical group management'},
    ],
}
