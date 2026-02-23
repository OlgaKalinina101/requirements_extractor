# Scripts Directory

Utility scripts for database management, testing, and maintenance.

## Database Management

### check_db.py
Check database contents and structure.

```bash
python scripts/check_db.py
```

**Output:**
- List of documents
- Total sections
- Total requirements
- Coverage metrics

---

### init_db_docker.py
Initialize database tables using Docker PostgreSQL.

```bash
python scripts/init_db_docker.py
```

**Use when:**
- First time setup
- Database schema changed
- Need to recreate tables

---

### recalculate_metrics.py
Recalculate coverage metrics for all documents.

```bash
python scripts/recalculate_metrics.py
```

**Use when:**
- Metrics calculation logic changed
- Need to fix incorrect metrics
- After manual database edits

---

## Other Utility Scripts

### check_db_docker.py
Check Docker PostgreSQL connection.

### check_docs.py
List all documents in database.

### check_tables.py
Verify database table structure.

### check_types.py
Check requirement types in database.

### init_db.py, init_db_direct_sql.py, init_db_simple.py
Alternative database initialization scripts.

---

## Usage

All scripts can be run from the project root:

```bash
cd c:\Users\Alien\PycharmProjects\test2
.venv\Scripts\python.exe scripts/<script_name>.py
```

---

## Notes

- Scripts require `.venv` to be activated or use full path to Python
- Database connection uses `DATABASE_URL` from `.env`
- Default: `postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db`
