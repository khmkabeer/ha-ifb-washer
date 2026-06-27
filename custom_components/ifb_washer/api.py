"""API client for IFB Washer."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse
from typing import Any

from aiohttp import ClientError, ClientResponseError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    APPLIANCE_BASE,
    AUTH_BASE,
    CONF_OAUTH_CONSUMER_KEY,
    CONF_OAUTH_CONSUMER_SECRET,
    CONF_OAUTH_TOKEN,
    CONF_OAUTH_TOKEN_SECRET,
    DEFAULT_APP_CLIENT_ID,
    DEFAULT_MQTT_HOST,
    DEFAULT_MQTT_PORT,
    LOGIN_BASE,
    STATE_NAMES,
)

_LOGGER = logging.getLogger(__name__)


class IfbApiError(Exception):
    """Raised when IFB API calls fail."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def new_pkce() -> dict[str, str]:
    """Create a PKCE verifier/challenge pair."""
    verifier = _b64url(os.urandom(64))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return {"code_verifier": verifier, "code_challenge": challenge}


def _oauth_quote(value: Any) -> str:
    return urllib.parse.quote(str(value), safe="~-._")


def _oauth1_header(method: str, url: str, credentials: dict[str, Any]) -> str:
    consumer_key = credentials.get(CONF_OAUTH_CONSUMER_KEY)
    consumer_secret = credentials.get(CONF_OAUTH_CONSUMER_SECRET)
    oauth_token = credentials.get(CONF_OAUTH_TOKEN)
    oauth_token_secret = credentials.get(CONF_OAUTH_TOKEN_SECRET)
    if not all((consumer_key, consumer_secret, oauth_token, oauth_token_secret)):
        raise IfbApiError("Missing IFB OAuth credentials.")
    parsed = urllib.parse.urlsplit(url)
    base_url = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", "", ""))
    params: dict[str, str] = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": str(int.from_bytes(os.urandom(8), "big", signed=False)),
        "oauth_signature_method": "HMAC-SHA256",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": oauth_token,
        "oauth_version": "1.0",
    }
    signing_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    signing_pairs.extend(params.items())
    signing_pairs.sort(key=lambda item: (_oauth_quote(item[0]), _oauth_quote(item[1])))
    param_string = "&".join(f"{_oauth_quote(key)}={_oauth_quote(value)}" for key, value in signing_pairs)
    base_string = "&".join([method.upper(), _oauth_quote(base_url), _oauth_quote(param_string)])
    key = f"{_oauth_quote(consumer_secret)}&{_oauth_quote(oauth_token_secret)}"
    digest = hmac.new(key.encode(), base_string.encode(), hashlib.sha256).digest()
    params["oauth_signature"] = base64.b64encode(digest).decode("ascii").strip()
    return "OAuth " + ", ".join(f'{_oauth_quote(key)}="{_oauth_quote(value)}"' for key, value in sorted(params.items()))


def find_first_key(data: Any, keys: tuple[str, ...]) -> str | None:
    """Find the first matching key recursively."""
    lowered = {key.lower() for key in keys}
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys or key.lower() in lowered:
                if value not in (None, ""):
                    return str(value)
        for value in data.values():
            found = find_first_key(value, keys)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_first_key(value, keys)
            if found:
                return found
    return None


def decode_progress(response: Any) -> dict[str, Any]:
    """Decode IFB progress response into entity-friendly data."""
    item: dict[str, Any] | None = None
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            item = data[0]
        elif isinstance(data, dict):
            item = data
    if not item:
        return {"available": False}

    state = item.get("state")
    balance_high = int(item.get("balanceTimeHighByte") or 0)
    balance_low = int(item.get("balanceTimeLowByte") or 0)
    program_high = int(item.get("programTimeHighByte") or 0)
    program_low = int(item.get("programTimeLowByte") or 0)
    remaining = balance_high * 256 + balance_low
    program = program_high * 256 + program_low
    return {
        "available": True,
        "source": "rest",
        "serial": item.get("serial"),
        "status": item.get("status"),
        "online": item.get("status") == "Online",
        "state": state,
        "state_name": STATE_NAMES.get(state, f"unknown_{state}"),
        "remaining_minutes": remaining,
        "program_minutes": program,
        "progress_percent": round(((program - remaining) / program) * 100) if program > 0 else (100 if state == 13 else 0),
        "childlock": item.get("childlockWasher"),
        "last_updated_at": item.get("lastUpdatedAt"),
        "raw": item,
    }


def decode_mqtt_payload(payload: bytes) -> dict[str, Any]:
    """Decode observed washer MQTT status frame."""
    data: dict[str, Any] = {
        "available": True,
        "source": "mqtt",
        "payload_hex": " ".join(f"{byte:02X}" for byte in payload),
        "length": len(payload),
    }
    if len(payload) < 36:
        data["state_name"] = "unknown"
        return data
    state = payload[30]
    remaining = (payload[17] << 8) + payload[18]
    program = (payload[32] << 8) + payload[33]
    data.update(
        {
            "frame_counter": payload[3],
            "state": state,
            "state_name": STATE_NAMES.get(state, f"unknown_{state}"),
            "remaining_minutes": remaining,
            "program_minutes": program,
            "progress_percent": round(((program - remaining) / program) * 100)
            if program > 0
            else (100 if state == 13 else 0),
            "active_session": payload[35],
            "online": True,
            "status": "Online",
        }
    )
    return data


def choose_washer(devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the best Wi-Fi washer from device/all."""
    washers = [device for device in devices if device.get("applianceType") == "WASHING_MACHINE"]
    if not washers:
        return None

    def score(device: dict[str, Any]) -> tuple[int, int, int, int]:
        return (
            1 if device.get("connectivity") == "WiFi" else 0,
            1 if device.get("status") == "Online" else 0,
            1 if device.get("isPrimary") else 0,
            1 if device.get("mac") else 0,
        )

    return sorted(washers, key=score, reverse=True)[0]


class IfbApiClient:
    """Small async client for the IFB cloud APIs."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self.data = data
        self._session = async_get_clientsession(hass)

    async def _post(
        self,
        base_url: str,
        path: str,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = base_url.rstrip("/") + "/" + path.lstrip("/")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "x-channel-key": "mobile",
            "User-Agent": "okhttp/4.12.0 HomeAssistant-IFBWasher/0.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)
        try:
            async with self._session.post(url, json=body or {}, headers=headers, timeout=30) as response:
                text = await response.text()
                if response.status >= 400:
                    raise IfbApiError(f"{response.status}: {text[:300]}")
                if not text:
                    return {}
                return await response.json(content_type=None)
        except (ClientError, ClientResponseError) as err:
            raise IfbApiError(str(err)) from err

    async def _signed_post(self, path: str, body: dict[str, Any]) -> Any:
        url = LOGIN_BASE.rstrip("/") + "/" + path.lstrip("/")
        return await self._post(LOGIN_BASE, path, body, extra_headers={"Authorization": _oauth1_header("POST", url, self.data)})

    async def request_otp(self, identifier: str, login_type: str, calling_code: str) -> dict[str, Any]:
        """Request an OTP."""
        body = {"method": "mailotp" if login_type == "email" else "phone", "calling_code": calling_code}
        if login_type == "email":
            body["username"] = identifier
        else:
            body["phonenumber"] = identifier
        pkce = new_pkce()
        response = await self._signed_post("rest/V1/restapi/login", body)
        return {"response": response, **pkce}

    async def verify_otp(
        self,
        identifier: str,
        login_type: str,
        calling_code: str,
        otp: str,
        code_challenge: str,
    ) -> Any:
        """Verify OTP and receive cloud authorization data."""
        body = {
            "method": "mail" if login_type == "email" else "phone",
            "otp": otp,
            "calling_code": calling_code,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "base_version": 2,
        }
        if login_type == "email":
            body["username"] = identifier
        else:
            body["phonenumber"] = identifier
        return await self._signed_post("rest/V1/restapi/otpverify", body)

    async def exchange_token(self, verify_response: Any, code_verifier: str) -> dict[str, Any]:
        """Exchange cloud authorization code for access and refresh tokens."""
        code = find_first_key(verify_response, ("code", "authorization_code"))
        client_id = find_first_key(verify_response, ("clientId", "client_id")) or DEFAULT_APP_CLIENT_ID
        if not code or not client_id:
            raise IfbApiError("OTP verified, but no authorization code/client_id was returned.")
        body = {
            "code_verifier": code_verifier,
            "code": code,
            "client_id": client_id,
            "grant_type": "authorization_code",
        }
        token_response = await self._post(AUTH_BASE, "auth/token", body)
        access_token = find_first_key(token_response, ("accessToken", "access_token", "token_val"))
        refresh_token = find_first_key(token_response, ("refreshToken", "refresh_token"))
        expires_in = find_first_key(token_response, ("expiresIn", "expires_in"))
        if not access_token:
            raise IfbApiError("Token exchange succeeded, but no access token was returned.")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": int(expires_in or 0),
            "client_id": client_id,
            "token_response": token_response,
        }

    async def refresh_access_token(self) -> dict[str, Any] | None:
        """Refresh the access token when possible."""
        refresh_token = self.data.get("refresh_token")
        client_id = self.data.get("client_id") or DEFAULT_APP_CLIENT_ID
        if not refresh_token:
            return None
        body = {"refresh_token": refresh_token, "client_id": client_id, "grant_type": "refresh_token"}
        response = await self._post(AUTH_BASE, "auth/token", body)
        access_token = find_first_key(response, ("accessToken", "access_token", "token_val"))
        new_refresh = find_first_key(response, ("refreshToken", "refresh_token")) or refresh_token
        expires_in = find_first_key(response, ("expiresIn", "expires_in"))
        if not access_token:
            return None
        self.data.update({"access_token": access_token, "refresh_token": new_refresh, "expires_in": int(expires_in or 0)})
        return dict(self.data)

    async def cloud_post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        """Call IFB appliance API with current bearer token."""
        token = self.data.get("access_token")
        if not token:
            raise IfbApiError("No access token available.")
        try:
            return await self._post(APPLIANCE_BASE, path, body, token=token)
        except IfbApiError as err:
            if not str(err).startswith("401"):
                raise
            if await self.refresh_access_token():
                return await self._post(APPLIANCE_BASE, path, body, token=self.data["access_token"])
            raise

    async def discover(self) -> dict[str, Any]:
        """Discover washer and MQTT settings."""
        device_all = await self.cloud_post("device/all")
        devices = device_all.get("data", []) if isinstance(device_all, dict) else []
        washer = choose_washer([device for device in devices if isinstance(device, dict)])
        if not washer:
            raise IfbApiError("No Wi-Fi washing machine found on this IFB account.")
        mqtt_response = await self.cloud_post("config/update/mqttClient")
        mqtt_client_id = find_first_key(mqtt_response, ("clientID", "clientId", "client_id"))
        if not mqtt_client_id:
            raise IfbApiError("No MQTT client ID returned.")
        progress = await self.cloud_post("device/smart/progress")
        return {
            "washer": washer,
            "mqtt_client_id": mqtt_client_id,
            "mqtt_host": DEFAULT_MQTT_HOST,
            "mqtt_port": DEFAULT_MQTT_PORT,
            "progress": decode_progress(progress),
        }

    async def get_progress(self) -> dict[str, Any]:
        """Read washer progress via REST."""
        return decode_progress(await self.cloud_post("device/smart/progress"))
