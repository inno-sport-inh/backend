# Миграция API на REST архитектуру

## Обзор

Данный проект содержит план и инструменты для миграции API с текущей function-based архитектуры на REST-compliant ViewSet-based архитектуру.

## Основные проблемы старого API

1. **Неконсистентные URL-ы**
   - Смешение существительных и глаголов: `enrollment/enroll`
   - Непоследовательные конвенции именования: `QR/toggle`, `change_gender`
   - Отсутствие четкой иерархии ресурсов

2. **Нарушение REST принципов**
   - Использование POST для операций, которые должны быть GET
   - Отсутствие стандартных HTTP методов для CRUD операций
   - Смешение различных типов операций в одном эндпоинте

3. **Сложность поддержки**
   - Function-based views вместо классов
   - Дублирование кода между похожими операциями
   - Отсутствие централизованной логики для валидации

## Новая архитектура

### Принципы REST API v2

1. **Ресурсо-ориентированные URL-ы**
   ```
   /api/v2/profile/           # Ресурс профиля
   /api/v2/enrollment/        # Ресурс записи на курсы
   /api/v2/training/123/      # Конкретная тренировка
   ```

2. **Правильное использование HTTP методов**
   - `GET` - получение данных
   - `POST` - создание ресурсов или выполнение действий
   - `PUT/PATCH` - обновление ресурсов
   - `DELETE` - удаление ресурсов

3. **ViewSet-based архитектура**
   - Централизованная логика для каждого ресурса
   - Автоматическая генерация URL-ов
   - Встроенная поддержка пагинации и фильтрации

## Использование

### 1. Запуск нового API

Новое API доступно по адресу `/api/v2/` и использует ViewSet-based архитектуру.

```python
# Добавьте в urls.py
path("api/v2/", include("api-v2.urls")),
```

### 2. Настройка middleware для отслеживания deprecation

```python
# settings.py
MIDDLEWARE = [
    # ... существующие middleware ...
    'api.middleware.APIDeprecationMiddleware',
    'api.middleware.APIMetricsMiddleware',
]
```

### 3. Миграция URL-ов в клиентском коде

Используйте скрипт автоматической миграции:

```bash
# Сухой прогон (просмотр изменений без применения)
python scripts/migrate_api_urls.py /path/to/your/frontend --dry-run

# Выполнение миграции
python scripts/migrate_api_urls.py /path/to/your/frontend --execute

# Генерация отчета
python scripts/migrate_api_urls.py /path/to/your/frontend --report migration_report.txt

# Сохранение JSON с маппингами
python scripts/migrate_api_urls.py /path/to/your/frontend --mappings url_mappings.json
```

### 4. Мониторинг использования старого API

После настройки middleware вы можете отслеживать использование старого API:

```bash
# Просмотр логов deprecation
tail -f logs/api_deprecation.log

# Просмотр метрик API
tail -f logs/api_metrics.log
```

## Маппинг URL-ов

### Profile
- `GET /api/profile/student` → `GET /api/v2/profile/student/`
- `POST /api/profile/change_gender` → `POST /api/v2/profile/change-gender/`
- `POST /api/profile/QR/toggle` → `POST /api/v2/profile/toggle-qr/`

### Enrollment
- `POST /api/enrollment/enroll` → `POST /api/v2/enrollment/enroll/`
- `POST /api/enrollment/unenroll` → `POST /api/v2/enrollment/unenroll/`

### Groups
- `GET /api/group/123` → `GET /api/v2/group/123/`
- `GET /api/sports` → `GET /api/v2/group/sports/`

### Training
- `GET /api/training/123` → `GET /api/v2/training/123/`
- `POST /api/training/123/check_in` → `POST /api/v2/training/123/check-in/`

[Полный список маппингов см. в MIGRATION_PLAN.md]

## Примеры использования нового API

### Получение информации о студенте
```javascript
// Старый API
fetch('/api/profile/student')

// Новый API
fetch('/api/v2/profile/student/')
```

### Запись на курс
```javascript
// Старый API
fetch('/api/enrollment/enroll', {
  method: 'POST',
  body: JSON.stringify({group_id: 123})
})

// Новый API
fetch('/api/v2/enrollment/enroll/', {
  method: 'POST',
  body: JSON.stringify({group_id: 123})
})
```

## Заголовки Deprecation

Старое API возвращает следующие заголовки для уведомления о deprecation:

```http
Deprecation: true
Sunset: 2025-12-31
Link: </api/v2/profile/student/>; rel="successor-version"
Warning: 299 - "This API version is deprecated. Please migrate to v2."
X-API-Deprecated: This endpoint is deprecated
X-API-Migration-Guide: https://docs.example.com/api-migration
X-API-New-Endpoint: /api/v2/profile/student/
```

## Этапы миграции

### Этап 1: Подготовка (Выполнено)
- [x] Создание ViewSet-based архитектуры
- [x] Настройка URL маршрутизации
- [x] Создание middleware для отслеживания

### Этап 2: Имплементация
- [ ] Перенос логики из function-based views
- [ ] Тестирование новых эндпоинтов
- [ ] Обновление документации

### Этап 3: Постепенная миграция
- [ ] Добавление deprecation заголовков
- [ ] Уведомление пользователей API
- [ ] Мониторинг использования

### Этап 4: Полное удаление
- [ ] Удаление старых эндпоинтов
- [ ] Очистка кода
- [ ] Финальное тестирование

## Преимущества новой архитектуры

1. **Лучшая организация кода**
   - ViewSet-based структура
   - Централизованная логика валидации
   - Простота тестирования

2. **REST-compliant API**
   - Стандартные HTTP методы
   - Консистентные URL-ы
   - Предсказуемое поведение

3. **Автоматическая документация**
   - OpenAPI/Swagger генерация
   - Интерактивная документация
   - Автоматические тесты API

4. **Лучшая производительность**
   - Оптимизированные запросы к БД
   - Встроенная пагинация
   - Кэширование ответов

## Поддержка

Если у вас есть вопросы по миграции:

1. Ознакомьтесь с [MIGRATION_PLAN.md](MIGRATION_PLAN.md)
2. Проверьте логи deprecation
3. Используйте автоматический скрипт миграции
4. Обратитесь к документации Django REST Framework

## Полезные ссылки

- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [HTTP Status Codes](https://httpstatuses.com/)
- [REST API Best Practices](https://restfulapi.net/)
