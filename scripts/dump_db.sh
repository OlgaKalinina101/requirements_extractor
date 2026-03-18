#!/bin/bash
# Дамп БД для передачи заказчику.
# Запуск: ./scripts/dump_db.sh [путь_к_файлу]
# По умолчанию: dump_requirements_YYYYMMDD_HHMM.sql

OUT="${1:-dump_requirements_$(date +%Y%m%d_%H%M).sql}"

echo "Creating dump: $OUT"

docker exec requirements-extractor-db pg_dump -U requirements_user -d requirements_db \
  --no-owner --no-acl --clean --if-exists \
  -f /tmp/dump.sql

docker cp requirements-extractor-db:/tmp/dump.sql "$OUT"

echo "Done. File: $OUT"
echo ""
echo "To load on another machine:"
echo "  psql -U requirements_user -d requirements_db -f $OUT"
echo "  (or via docker exec if using Docker)"
