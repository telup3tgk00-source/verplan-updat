# Gunakan Python versi ringan
FROM python:3.12-slim

WORKDIR /app

# Install dependencies sistem (untuk PostgreSQL dan compiling)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run gunicorn (menggunakan konfigurasi KVM 2 yang kita buat)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
