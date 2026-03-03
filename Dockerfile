FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema (necessárias para psycopg2 e Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

EXPOSE 8000

# Migrations + collectstatic + gunicorn
CMD ["sh", "-c", "\
    python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
