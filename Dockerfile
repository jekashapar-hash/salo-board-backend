# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS builder

# Встановлюємо uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Змінюємо робочу директорію
WORKDIR /app

# Оптимізації uv для Docker
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Встановлюємо залежності проєкту окремо від коду для оптимального кешування шарів.
# Використовуємо Docker buildkit для кешування між білдами.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Копіюємо вихідний код проєкту
COPY . /app

# Завершуємо синхронізацію проєкту
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Фінальний, легший образ
FROM python:3.12-slim-bookworm

# Забороняємо Python писати .pyc файли на диск (щоб не засмічувати контейнер)
ENV PYTHONDONTWRITEBYTECODE=1
# Вимикаємо буферизацію stdout/stderr (щоб логи одразу відображалися в терміналі)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копіюємо віртуальне середовище (залежності) з builder образу
COPY --from=builder /app/.venv /app/.venv

# Розміщуємо виконувані файли середовища на початку PATH
ENV PATH="/app/.venv/bin:$PATH"

# Копіюємо весь код додатку
COPY . /app/

EXPOSE 8000

# За замовчуванням запускаємо dev сервер (у production використовуйте gunicorn)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
