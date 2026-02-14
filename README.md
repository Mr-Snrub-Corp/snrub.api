

## Project structure:
```
mot.fastapi/
├── app/
│   ├── config/
│   ├── controllers/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── routes/
│   ├── security/
│   ├── services/
│   └── main.py
├── migrations/
├── tests/
├── scripts/
├── alembic.ini
├── docker-compose.yaml
├── pyproject.toml
├── pytest.ini
└── ruff.toml
```


## Local development 

Copy .env.example -> .env.development and fill in the values

Build with docker for local development 

```shell
docker-compose up -d --build
```

### API Documentation

API documentation is available via [Scalar](https://scalar.com/) at:

[http://localhost:8000/docs](http://localhost:8000/docs)

Stop and remove the containers
```
$ docker compose down
```


### Logs

Log output from the application:
```
docker compose logs -f api

docker compose logs -f client
```

### Email in local development 

Mailhog is used for password reset flows it can be accessed on 

[http://localhost:8025/](http://localhost:8025)

### Migrations

Hit this endpoint with with token (must be super admin) 
```
GET http://localhost:8000/api/admin/migrate
```

**Or with Docker**

To generate a new migration file, run the following command:

```zsh
docker compose exec api alembic revision --autogenerate -m "Your migration message"
```

Run migrations:

```zsh
docker compose exec api alembic upgrade head
```

### Use Docker CLI to Access the Database

Connect to the PostgreSQL container: 
```
docker-compose exec db psql -U postgres -d mot_database
```

Once connected, you can run SQL commands:
```postgres=# \dt  # List tables
postgres=# SELECT * FROM users;  # View users table
```


### Testing

Docker needs to be up and running for integration tests to work.

Run all tests 
```zsh
APP_ENV=test uv run pytest
```
Just run integration tests 
```zsh
APP_ENV=test uv run pytest tests/integration
```

### Updating Seed Data

Export current dev DB state (new users + incident reports) to seed-friendly format:
```zsh
docker compose exec api python scripts/export_seed_data.py
```
- New users are printed as dicts to append to `seeds/data/users.py`, photos written to `seeds/data/photos/`
- Incident reports are printed as the full `INCIDENT_REPORTS` list for `seeds/data/incident_reports.py`

Seeds run automatically on `docker compose up`. To re-seed manually:
```zsh
docker compose exec api python -m seeds.seed_runner
```

### Ruff Linting / formating
```zsh
uv run ruff check . --fix
uv run ruff format .
```





Delete a test user fails cos of some password reset relationship