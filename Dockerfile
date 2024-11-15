FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5000

CMD ["python", "app.py"]
