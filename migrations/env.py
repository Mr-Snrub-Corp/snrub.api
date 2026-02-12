from logging.config import fileConfig
from alembic import context
from app.db.database import engine
from sqlmodel import SQLModel
# Import all models that need to be included in migrations
from app.models.user import User
from app.models.incident_category import IncidentCategory  # noqa: F401
from app.models.incident_type import IncidentType  # noqa: F401
from app.models.password_reset import PasswordReset

# Add this function to handle SQLModel types properly
def process_revision_directives(context, revision, directives):
    if directives[0].upgrade_ops.ops:
        # Add sqlmodel import to the migration script
        directives[0].imports.append("import sqlmodel")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# Add this line to register the custom function
context.configure(
    connection=engine.connect(),
    target_metadata=target_metadata,
    process_revision_directives=process_revision_directives
)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use the URL from the app's engine
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the engine from the app instead of creating a new one
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
