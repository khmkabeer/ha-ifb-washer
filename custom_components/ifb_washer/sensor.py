"""Sensors for IFB Washer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import IfbWasherCoordinator
from .entity import IfbWasherEntity


@dataclass(frozen=True, kw_only=True)
class IfbSensorDescription(SensorEntityDescription):
    """IFB sensor description."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[IfbSensorDescription, ...] = (
    IfbSensorDescription(
        key="phase",
        translation_key="phase",
        value_fn=lambda data: data.get("state_name"),
    ),
    IfbSensorDescription(
        key="remaining_time",
        translation_key="remaining_time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("remaining_minutes"),
    ),
    IfbSensorDescription(
        key="program_time",
        translation_key="program_time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("program_minutes"),
    ),
    IfbSensorDescription(
        key="progress",
        translation_key="progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("progress_percent"),
    ),
    IfbSensorDescription(
        key="raw_state",
        translation_key="raw_state",
        value_fn=lambda data: data.get("state"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up IFB washer sensors."""
    coordinator: IfbWasherCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(IfbWasherSensor(coordinator, entry, description) for description in SENSORS)


class IfbWasherSensor(IfbWasherEntity, SensorEntity):
    """IFB washer sensor."""

    entity_description: IfbSensorDescription

    def __init__(self, coordinator: IfbWasherCoordinator, entry: ConfigEntry, description: IfbSensorDescription) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return native value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
