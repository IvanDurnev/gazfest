# MAX bot для «Газ!Феста»

Бот принимает текстовые сообщения через webhook, ставит их в очередь Celery
и отвечает через OpenAI на основании базы знаний о фестивале.

## Запуск

Redis уже должен быть запущен и отвечать на `redis-cli ping`.

Для AI-ответов в `.env` должны быть заданы:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-terra
```

В первом терминале запустите веб-приложение:

```bash
venv/bin/flask --app wsgi:app run --port 5000
```

Во втором терминале запустите worker:

```bash
venv/bin/celery -A app.celery_app.celery worker --loglevel=info
```

В третьем терминале откройте HTTPS-туннель:

```bash
tuna http 5000
```

Запишите выданный Tuna HTTPS URL в `PUBLIC_BASE_URL` внутри `.env`, затем
зарегистрируйте webhook:

```bash
venv/bin/flask --app wsgi:app register-max-webhook
```

MAX будет отправлять события на:

```text
PUBLIC_BASE_URL/max/webhook
```

Клиент MAX использует дополнительный корневой сертификат Минцифры из
`certs/russian_trusted_root_ca.pem`. Путь можно переопределить переменной
`MAX_CA_CERT_PATH`.

Мини-приложение будет доступно по:

```text
PUBLIC_BASE_URL/max/miniapp
```

## Проверки

```bash
venv/bin/ruff check .
venv/bin/ruff format --check .
venv/bin/pytest -q
```
