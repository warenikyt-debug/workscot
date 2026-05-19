cd /workspaces/workscot/backend

# 1. Запускаем Docker (база данных)
docker compose up -d
sleep 5

# 2. Проверяем что Docker работает
docker compose ps

# 3. Запускаем сервер
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 3

# 4. Проверяем
echo "=== Health ==="
curl -s http://localhost:8000/health

echo ""
echo "=== Login ==="
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login

echo ""
echo "=== API ==="
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin99@t.com","password":"12345678"}' | head -c 100

echo ""
echo "=== ГОТОВО ==="