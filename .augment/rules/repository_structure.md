---
type: "always_apply"
---

# mot.fastapi Repository Overview

This is an API service that pairs with a Vue frontend (mot.frontend)

## 🏗️ Core Architecture

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

### Key Directories

- **`app/`** - Main application code following MVC pattern
  - **`routes/`** - FastAPI route definitions
  - **`controllers/`** - Business logic controllers (Controllers in MVC)
  - **`db/`** - Database connection and session management
  - **`models/`** - Pydantic data models and database schemas
  - **`core/`** - Core configuration and utilities
  - **`security/`** - Authentication and authorization utilities
  - **`services/`** - Business service layer
- **`tests/`** - Test suite using pytest
- **`migrations/`** - Database migration management
- **`scripts/`** - Utility scripts for development/deployment
