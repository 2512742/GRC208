"""Display time zones users may choose (PLAN.md §2.7). Business rules always use the
organisation's zone (Africa/Lagos); this list only changes how times are shown."""

from __future__ import annotations

SYSTEM = "system"

# value -> label shown in the dropdown
DISPLAY_TIMEZONES: dict[str, str] = {
    SYSTEM: "System (this device's zone)",
    "Africa/Lagos": "WAT: Lagos, Nigeria (UTC+1)",
    "Africa/Douala": "WAT: Douala, Cameroon (UTC+1)",
    "Africa/Kampala": "EAT: Kampala, Uganda (UTC+3)",
    "Africa/Nairobi": "EAT: Nairobi, Kenya (UTC+3)",
    "Africa/Accra": "GMT: Accra, Ghana (UTC+0)",
    "UTC": "UTC",
}


def is_allowed(value: str) -> bool:
    return value in DISPLAY_TIMEZONES
