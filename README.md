docker compose run --rm app alembic revision --autogenerate -m "Initial migration"
docker compose run --rm app alembic upgrade head
