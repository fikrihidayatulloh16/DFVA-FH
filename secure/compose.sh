#!/bin/bash

echo ">> Cek status Redis bawaan sistem..."
if systemctl is-active --quiet redis; then
  echo ">> 🔌 Redis system aktif, menghentikan..."
  sudo systemctl stop redis
else
  echo ">> ✅ Redis system sudah tidak aktif"
fi

echo ">> 🐳 Menjalankan Docker Compose..."
docker compose up -d