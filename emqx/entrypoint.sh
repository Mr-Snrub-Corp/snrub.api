#!/bin/sh
# Write the EMQX auth bootstrap from env (passwords are not in git) and hand
# off to the image entrypoint. ACL usernames default to snrub_api / snrub_sim.
set -eu

api_user="${MQTT_API_USERNAME:-snrub_api}"
sim_user="${MQTT_SIM_USERNAME:-snrub_sim}"
api_pass="${MQTT_API_PASSWORD:?MQTT_API_PASSWORD is required (set it in .env.development)}"
sim_pass="${MQTT_SIM_PASSWORD:?MQTT_SIM_PASSWORD is required (set it in .env.development)}"
dashboard_pass="${EMQX_DASHBOARD_PASSWORD:?EMQX_DASHBOARD_PASSWORD is required (set it in .env.development)}"

bootstrap="${EMQX_AUTHENTICATION__1__BOOTSTRAP_FILE:-/tmp/auth-bootstrap.csv}"
umask 077
cat > "$bootstrap" <<EOF
user_id,password,is_superuser
${api_user},${api_pass},false
${sim_user},${sim_pass},false
EOF

export EMQX_DASHBOARD__DEFAULT_PASSWORD="$dashboard_pass"
export EMQX_AUTHENTICATION__1__BOOTSTRAP_FILE="$bootstrap"

exec /usr/bin/docker-entrypoint.sh "$@"
