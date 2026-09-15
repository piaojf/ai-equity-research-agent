# Alembic migrations

Run from the repository root:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

The migration environment imports the canonical SQLAlchemy models and
`Base.metadata`; business code never executes SQL from an API route.
