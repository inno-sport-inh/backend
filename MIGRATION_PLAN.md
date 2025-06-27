# План миграции API на REST архитектуру

## Текущее состояние

### Проблемы старого API (`/api/`)
- Неконсистентные URL-ы:
  - `profile/student` (должно быть `profile/`)
  - `enrollment/enroll` (должно быть `enrollment/` POST)
  - `training/<id>/check_in` (должно быть `training/<id>/check-in/` POST)
- Смешение HTTP методов без следования REST принципам
- Function-based views вместо ViewSet'ов
- Отсутствие четкой ресурсной модели

### Новое API (`/api/v2/`)
- ViewSet-based архитектура ✅
- REST-compliant URL структура ✅
- Консистентное использование HTTP методов ✅
- Лучшая организация кода ✅

## План реорганизации

### 1. Ресурсы и их эндпоинты

#### Profile
**Старые эндпоинты:**
- `GET /api/profile/student` → `GET /api/v2/profile/student/`
- `POST /api/profile/change_gender` → `POST /api/v2/profile/change-gender/`
- `POST /api/profile/QR/toggle` → `POST /api/v2/profile/toggle-qr/`
- `GET /api/profile/history/<semester_id>` → `GET /api/v2/profile/history/<semester_id>/`
- `GET /api/profile/history_with_self/<semester_id>` → `GET /api/v2/profile/history-with-self/<semester_id>/`

#### Enrollment
**Старые эндпоинты:**
- `POST /api/enrollment/enroll` → `POST /api/v2/enrollment/enroll/`
- `POST /api/enrollment/unenroll` → `POST /api/v2/enrollment/unenroll/`
- `POST /api/enrollment/unenroll_by_trainer` → `POST /api/v2/enrollment/unenroll-by-trainer/`

#### Groups
**Старые эндпоинты:**
- `GET /api/group/<group_id>` → `GET /api/v2/group/<id>/`
- `POST /api/select_sport` → `POST /api/v2/group/select-sport/`
- `GET /api/sports` → `GET /api/v2/group/sports/`

#### Training  
**Старые эндпоинты:**
- `GET /api/training/<training_id>` → `GET /api/v2/training/<id>/`
- `POST /api/training/<training_id>/check_in` → `POST /api/v2/training/<id>/check-in/`
- `POST /api/training/<training_id>/cancel_check_in` → `POST /api/v2/training/<id>/cancel-check-in/`

#### Attendance
**Старые эндпоинты:**
- `POST /api/attendance/mark` → `POST /api/v2/attendance/mark/`
- `GET /api/attendance/suggest_student` → `GET /api/v2/attendance/suggest-student/`
- `GET /api/attendance/<training_id>/grades` → `GET /api/v2/attendance/training/<training_id>/grades/`
- `GET /api/attendance/<student_id>/hours` → `GET /api/v2/attendance/student/<student_id>/hours/`

#### Calendar
**Старые эндпоинты:**
- `GET /api/calendar/<sport_id>/schedule` → `GET /api/v2/calendar/sport/<sport_id>/schedule/`
- `GET /api/calendar/trainings` → `GET /api/v2/calendar/trainings/`

#### References
**Старые эндпоинты:**
- `POST /api/reference/upload` → `POST /api/v2/reference/upload/`

#### Self Sport
**Старые эндпоинты:**
- `POST /api/selfsport/upload` → `POST /api/v2/selfsport/upload/`
- `GET /api/selfsport/types` → `GET /api/v2/selfsport/types/`
- `GET /api/selfsport/strava_parsing` → `GET /api/v2/selfsport/strava-parsing/`

#### Fitness Test
**Старые эндпоинты:**
- `GET /api/fitnesstest/result` → `GET /api/v2/fitnesstest/result/`
- `POST /api/fitnesstest/upload` → `POST /api/v2/fitnesstest/upload/`
- `GET /api/fitnesstest/exercises` → `GET /api/v2/fitnesstest/exercises/`
- `GET /api/fitnesstest/sessions` → `GET /api/v2/fitnesstest/sessions/`

#### Measurement
**Старые эндпоинты:**
- `POST /api/measurement/student_measurement` → `POST /api/v2/measurement/student-measurement/`
- `GET /api/measurement/get_results` → `GET /api/v2/measurement/results/`
- `GET /api/measurement/get_measurements` → `GET /api/v2/measurement/measurements/`

#### Semester
**Старые эндпоинты:**
- `GET /api/semester` → `GET /api/v2/semester/`

#### Analytics
**Старые эндпоинты:**
- `GET /api/analytics/attendance` → `GET /api/v2/analytics/attendance/`

#### Medical Groups
**Старые эндпоинты:**
- `GET /api/medical_groups/` → `GET /api/v2/medical_groups/`

### 2. Этапы миграции

#### Этап 1: Создание ViewSet'ов (✅ Выполнено)
- [x] Создан файл `api/viewsets.py`
- [x] Реализованы базовые ViewSet'ы для всех ресурсов
- [x] Добавлены custom actions для специфических операций
- [x] Настроена документация с drf-spectacular

#### Этап 2: Имплементация логики
- [ ] Перенести логику из function-based views в ViewSet'ы
- [ ] Обновить сериализаторы под новую структуру
- [ ] Добавить валидацию и обработку ошибок
- [ ] Протестировать каждый эндпоинт

#### Этап 3: Deprecation старого API
- [ ] Добавить HTTP заголовки deprecation в старые эндпоинты
- [ ] Создать middleware для логирования использования старых эндпоинтов
- [ ] Обновить документацию и уведомить пользователей

#### Этап 4: Полное удаление старого API
- [ ] Удалить старые view функции
- [ ] Удалить старые URL маршруты
- [ ] Очистить неиспользуемый код

### 3. Преимущества новой архитектуры

#### REST-compliant URLs
```python
# Старый подход
GET /api/profile/student
POST /api/enrollment/enroll
GET /api/group/123

# Новый подход  
GET /api/v2/profile/student/
POST /api/v2/enrollment/enroll/
GET /api/v2/group/123/
```

#### Консистентное использование HTTP методов
- `GET` - получение данных
- `POST` - создание ресурсов/выполнение действий
- `PUT/PATCH` - обновление ресурсов
- `DELETE` - удаление ресурсов

#### ViewSet-based архитектура
- Лучшая организация кода
- Автоматическая генерация URL'ов
- Встроенная поддержка пагинации, фильтрации
- Более простое тестирование

#### Улучшенная документация
- Автоматическая генерация OpenAPI схемы
- Интерактивная документация через Swagger UI
- Консистентные описания эндпоинтов

### 4. Следующие шаги

1. **Имплементация логики** - перенести код из старых views
2. **Тестирование** - написать тесты для новых эндпоинтов
3. **Документация** - обновить API документацию
4. **Мониторинг** - настроить отслеживание миграции
5. **Постепенный переход** - начать использовать новые эндпоинты в клиентских приложениях
