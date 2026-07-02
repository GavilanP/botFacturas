FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy and install python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# app
COPY . /app

# runtime: expect env vars via docker run --env-file or CI
CMD ["python", "src/bot.py"]
