# Дамп БД для передачи заказчику (PowerShell).
# Запуск: .\scripts\dump_db.ps1
# Или: .\scripts\dump_db.ps1 -OutFile "my_dump.sql"

param(
    [string]$OutFile = "dump_requirements_$(Get-Date -Format 'yyyyMMdd_HHmm').sql"
)

Write-Host "Creating dump: $OutFile"

docker exec requirements-extractor-db pg_dump -U requirements_user -d requirements_db --no-owner --no-acl --clean --if-exists -f /tmp/dump.sql
docker cp requirements-extractor-db:/tmp/dump.sql $OutFile

Write-Host "Done. File: $OutFile"
Write-Host ""
Write-Host "To load on another machine:"
Write-Host "  psql -U requirements_user -d requirements_db -f $OutFile"
Write-Host "  (or via docker exec if using Docker)"
