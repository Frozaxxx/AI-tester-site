FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/services/runs

COPY services/runs/pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

COPY services/runs/alembic.ini .
COPY services/runs/migrations migrations
COPY services/runs/app app

RUN useradd --system --no-create-home app
USER app

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
