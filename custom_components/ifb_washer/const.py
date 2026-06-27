"""Constants for the IFB Washer integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ifb_washer"

AUTH_BASE = "https://myifb.ifbcloud.in/api/v5/"
LOGIN_BASE = "https://mcprod.ifbappliances.com/"
APPLIANCE_BASE = "https://myifb.ifbcloud.in/api/v5/"

CONF_IDENTIFIER = "identifier"
CONF_LOGIN_TYPE = "login_type"
CONF_CALLING_CODE = "calling_code"
CONF_OAUTH_CONSUMER_KEY = "oauth_consumer_key"
CONF_OAUTH_CONSUMER_SECRET = "oauth_consumer_secret"
CONF_OAUTH_TOKEN = "oauth_token"
CONF_OAUTH_TOKEN_SECRET = "oauth_token_secret"

DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
DATA_MQTT = "mqtt"

DEFAULT_CALLING_CODE = "+91"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_MQTT_HOST = "mqtt2.ifbcloud.in"
DEFAULT_MQTT_PORT = 8883
DEFAULT_APP_CLIENT_ID = "aK9uNoA8QS"

PLATFORMS = ["sensor", "binary_sensor"]

STATE_NAMES = {
    0: "selected",
    1: "standby",
    4: "main_wash",
    8: "first_rinse",
    9: "second_rinse",
    10: "final_rinse",
    11: "final_spin",
    13: "complete",
    14: "paused",
    17: "heating",
    18: "draining",
}
