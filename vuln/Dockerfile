FROM python:3.10-slim

WORKDIR /app

# Install sistem dependencies dulu (tambahkan libdbus-dev dan python3-dev)
RUN apt-get update && apt-get install -y \
    gcc \
    libdbus-1-dev \
    libglib2.0-dev \
    python3-dev \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install dependencies Python
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy kode aplikasi terakhir
COPY . .

EXPOSE 5001

CMD ["python", "run.py"]
