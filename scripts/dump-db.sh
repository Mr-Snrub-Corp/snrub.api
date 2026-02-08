#!/usr/bin/env bash
echo "Dumping database to seeds/snrub-seed.sql..."
docker compose exec -T db pg_dump -U postgres -d mot_database \
  -F p -a -w --column-inserts --disable-dollar-quoting \
  -T 'alembic*' -T 'engagement' -T 'irrelevant*' \
  > seeds/snrub-seed.sql
echo "Done."
