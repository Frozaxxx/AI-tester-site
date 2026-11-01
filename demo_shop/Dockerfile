FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

COPY demo_shop demo_shop

RUN useradd --system --no-create-home app
USER app

EXPOSE 8001
CMD ["python", "-m", "demo_shop", "--host", "0.0.0.0", "--port", "8001"]
