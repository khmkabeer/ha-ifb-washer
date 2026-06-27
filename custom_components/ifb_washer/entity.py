"""Base entities for IFB Washer."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IfbWasherCoordinator


class IfbWasherEntity(CoordinatorEntity[IfbWasherCoordinator]):
    """Base IFB washer entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IfbWasherCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.key = key
        washer = entry.data["washer"]
        serial = washer.get("serial") or entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            manufacturer="IFB",
            model=washer.get("model"),
            name=washer.get("deviceName") or washer.get("model") or "IFB Washer",
            serial_number=str(serial),
            sw_version=washer.get("firmwareVersion"),
            hw_version=washer.get("firmwareVersionWifi"),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return bool(self.coordinator.data and self.coordinator.data.get("available", True))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return shared debug attributes."""
        data = self.coordinator.data or {}
        return {
            "source": data.get("source"),
            "updated_at": data.get("updated_at"),
            "last_updated_at": data.get("last_updated_at"),
        }
