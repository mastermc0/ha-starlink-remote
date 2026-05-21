"""Select platform for Starlink Remote - Snow Melt Mode."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Callable
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DATA_DEVICES, DOMAIN
from .entity_base import StarlinkEntity
from .spacex.api.device.device_pb2 import DishSetConfigRequest
from .spacex.api.device.dish_config_pb2 import DishConfig

_LOGGER = logging.getLogger(__name__)

SNOW_MELT_MODES = {
    "auto": DishConfig.SnowMeltMode.AUTO,
    "preheat": DishConfig.SnowMeltMode.ALWAYS_ON,
    "off": DishConfig.SnowMeltMode.ALWAYS_OFF,
}
SNOW_MELT_MODES_INV = {v: k for k, v in SNOW_MELT_MODES.items()}


@dataclass(frozen=True)
class StarlinkSelectEntityDescription(SelectEntityDescription):
    value_fn: Callable[[dict[str, Any]], str | None] = lambda x: None
    dev_types: list[str] = None


SELECT_DESCRIPTIONS = (
    StarlinkSelectEntityDescription(
        key="snow_melt_mode",
        name="Snow Melt Mode",
        options=list(SNOW_MELT_MODES.keys()),
        value_fn=lambda d: SNOW_MELT_MODES_INV.get(
            d.get("status", {}).get("dish_get_config", {}).get("dish_config", {}).get("snow_melt_mode", 0)
        ),
        dev_types=["dish"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for tid, dev_data in coordinator.data.get(DATA_DEVICES, {}).items():
        dev_type = dev_data["type"]
        for desc in SELECT_DESCRIPTIONS:
            if dev_type in desc.dev_types:
                entities.append(StarlinkSelectEntity(coordinator, desc, tid))

    async_add_entities(entities)


class StarlinkSelectEntity(StarlinkEntity, SelectEntity):
    entity_description: StarlinkSelectEntityDescription

    @property
    def current_option(self) -> str | None:
        dev_data = self.coordinator.data.get(DATA_DEVICES, {}).get(self.target_id, {})
        return self.entity_description.value_fn(dev_data)

    async def async_select_option(self, option: str) -> None:
        mode = SNOW_MELT_MODES[option]
        config = DishConfig(snow_melt_mode=mode, apply_snow_melt_mode=True)
        request_data = DishSetConfigRequest(dish_config=config)

        success = await self.coordinator.async_send_command(
            self.target_id, "dish_set_config", request_data
        )
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set snow melt mode to %s", option)
