Saloboard Backend
=================

Django REST API для платформи проведення турнірів.

Стек: Django 6.0, DRF, Daphne, Channels, Celery, Redis, PostgreSQL/SQLite, uv.


Вимоги
------

  - Python 3.12+
  - uv (менеджер пакетів, встановлення нижче)
  - Git

Для повного стеку з Celery та WebSocket додатково:
  - Docker (для Redis)


Встановлення uv
---------------

Документація: https://docs.astral.sh/uv/getting-started/installation/

Windows:

    winget install astral-sh.uv

macOS / Linux:

    curl -LsSf https://astral.sh/uv/install.sh | sh

Перевірка:

    uv --version


Швидкий старт (5 кроків)
-------------------------

1. Клонувати репозиторій:

    git clone <repo-url>
    cd saloboard

2. Встановити залежності:

    uv sync --dev

3. Створити файл .env (скопіювати мінімальний варіант):

    SECRET_KEY=any-random-secret-key-for-local-dev
    DEBUG=True
    ALLOWED_HOSTS=127.0.0.1,localhost
    IS_DEV_DATABASE=True

   IS_DEV_DATABASE=True — використовується SQLite, нічого додатково не потрібно.

4. Застосувати міграції та створити суперкористувача:

    uv run python manage.py migrate
    uv run python manage.py createsuperuser

5. Запустити сервер:

    uv run python manage.py runserver

Готово. Сервер доступний за адресою http://127.0.0.1:8000


Доступні URL після запуску
--------------------------

  http://127.0.0.1:8000/admin          адмін-панель (Django Jazzmin)
  http://127.0.0.1:8000/api/docs       Swagger UI — інтерактивна документація API
  http://127.0.0.1:8000/api/redoc      ReDoc — альтернативна документація
  http://127.0.0.1:8000/api/schema     OpenAPI схема (JSON)


Перевірка роботи API
--------------------

Зареєструвати користувача:

    curl -X POST http://127.0.0.1:8000/api/register \
      -H "Content-Type: application/json" \
      -d '{"username":"jury","email":"jury@test.com","password":"TestPass123!","firstName":"Jury","lastName":"Member"}'

Або відкрити Swagger і використати кнопку "Try it out":
  http://127.0.0.1:8000/api/docs


Запуск тестів
-------------

    uv run pytest

Тести використовують SQLite in-memory, Redis і зовнішні сервіси не потрібні.

Переглянути звіт покриття:

    uv run pytest -v


Ключові ендпоінти API
---------------------

Автентифікація:
  POST /api/register              реєстрація
  POST /api/login                 отримання JWT-токенів (access + refresh)
  POST /api/token/refresh         оновлення access-токена
  POST /api/logout                вихід

Профіль:
  GET/PUT  /api/user              профіль поточного користувача
  GET      /api/user/roles        ролі у турнірах

Турніри:
  GET  /api/tournaments           список активних турнірів
  GET  /api/tournaments/<id>      деталі турніру
  GET  /api/tournaments/<id>/rounds/<id>      деталі раунду
  GET  /api/tournaments/<id>/leaderboard      таблиця результатів

Команди:
  GET/POST /api/teams             список / створення команди
  GET/PUT  /api/teams/<id>        деталі команди
  GET/POST /api/teams/<id>/participant  учасники

Адмін (для організаторів турніру):
  POST /api/admin/tournaments/<id>/start-registration
  POST /api/admin/tournaments/<id>/close-registration
  POST /api/admin/tournaments/<id>/start
  POST /api/admin/tournaments/<id>/finish
  POST /api/admin/tournaments/<id>/rounds/<id>/start

Повний список із схемами запитів/відповідей — у Swagger:
  http://127.0.0.1:8000/api/docs


WebSocket
---------

Проект підтримує WebSocket-з'єднання через Django Channels + Daphne.
Для роботи потрібен Redis. Для запуску лише через runserver — WebSocket
буде доступний без Redis (через InMemoryChannelLayer).

    ws://127.0.0.1:8000/ws/<endpoint>/

Автентифікація через JWT-токен у заголовку підключення.


Telegram Webhook (опціонально)
------------------------------

Бот приймає оновлення через webhook:

    POST /api/webhooks/telegram/

Змінні для бота в .env (якщо потрібен бот):

    TELEGRAM_BOT_TOKEN=<токен від @BotFather>
    TELEGRAM_BOT_USERNAME=<username бота>

Без цих змінних всі інші функції API працюють в штатному режимі.


Запуск Celery локально (опціонально)
-------------------------------------

Потрібен Redis. Найпростіший спосіб — через Docker:

    docker run -d -p 6379:6379 redis:7-alpine

Worker (виконання задач):

    uv run celery -A saloboard worker -l info --pool=solo

Beat (планувальник):

    uv run celery -A saloboard beat -l info

Celery Beat запускає автоматичну перевірку статусів турнірів і раундів
з інтервалом CHECKER_INTERVAL_MINUTES (за замовчуванням 15 хвилин).

Без Celery сервер і API повністю функціональні — тільки фонові задачі
(автоматична зміна статусів) не будуть виконуватись.


Запуск через Docker (повний стек)
----------------------------------

Якщо потрібен PostgreSQL + Redis + Celery в одній команді.

Додай у .env:

    IS_DEV_DATABASE=False
    DATABASE_URL=postgres://salouser:salopass@db:5432/saloboard
    CELERY_BROKER_URL=redis://redis:6379/1
    CELERY_RESULT_BACKEND=redis://redis:6379/1
    REDIS_URL=redis://redis:6379/0

Запуск:

    docker compose up --build -d

Сервіси після запуску:
  web (Django)    — http://localhost:8888
  db (PostgreSQL) — localhost:5435
  redis           — localhost:6379
  celery_worker   — фоновий воркер
  celery_beat     — планувальник задач

Логи:

    docker compose logs -f

Зупинка:

    docker compose down


Управління залежностями
-----------------------

Додати пакет:

    uv add <package>
    uv add --dev <package>

Видалити пакет:

    uv remove <package>

Оновити всі пакети:

    uv lock --upgrade
    uv sync --dev

Після будь-якої зміни фіксуй uv.lock у git.


Корисні команди
---------------

    uv run pytest                      # тести
    uv run pytest -v                   # тести з деталями
    uv run ruff check .                # лінтинг
    uv run ruff check . --fix          # лінтинг з виправленням
    uv run ruff format .               # форматування
    uv run python manage.py makemigrations
    uv run python manage.py shell


Структура проекту
-----------------

    saloboard/
    ├── saloboard/        конфігурація Django (settings, urls, celery, asgi)
    ├── salocore/         основний застосунок
    │   ├── models/
    │   ├── views/
    │   ├── serializers.py
    │   ├── services/     бізнес-логіка
    │   ├── repositories/ шар роботи з БД
    │   ├── use_cases/
    │   ├── permissions.py
    │   ├── consumers.py  WebSocket-консьюмери
    │   ├── routing.py    WebSocket-маршрути
    │   ├── tasks.py      Celery-задачі
    │   └── tests/        тести (pytest)
    ├── scripts/
    │   └── entrypoint.sh міграції + старт (Docker)
    ├── db/               SQLite (тільки dev)
    ├── pyproject.toml
    ├── uv.lock
    ├── Dockerfile
    └── docker-compose.yaml


Перевірка перед комітом
-----------------------

    uv run ruff check . && uv run pytest
