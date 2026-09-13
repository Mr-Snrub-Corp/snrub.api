from app.core.config import Settings


def test_mqtt_role_api_copies_api_password():
    settings = Settings(
        MQTT_ROLE="api",
        MQTT_API_PASSWORD="api-secret",
        MQTT_USERNAME="ignored",
        MQTT_PASSWORD="ignored",
    )
    assert settings.MQTT_USERNAME == "snrub_api"
    assert settings.MQTT_PASSWORD == "api-secret"


def test_mqtt_role_simulator_copies_sim_password():
    settings = Settings(MQTT_ROLE="simulator", MQTT_SIM_PASSWORD="sim-secret")
    assert settings.MQTT_USERNAME == "snrub_sim"
    assert settings.MQTT_PASSWORD == "sim-secret"


def test_mqtt_role_absent_keeps_explicit_creds():
    settings = Settings(MQTT_USERNAME="host", MQTT_PASSWORD="host-secret")
    assert settings.MQTT_USERNAME == "host"
    assert settings.MQTT_PASSWORD == "host-secret"
