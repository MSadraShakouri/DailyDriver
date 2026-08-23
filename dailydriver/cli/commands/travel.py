"""Travel command — toggle location-dependent features."""

from dailydriver.core.state import is_travel_mode, set_travel_mode


def travel_command(cmd: str) -> str:
    """Handle travel command: travel, travel on, travel off, travel status."""
    parts = cmd.strip().split()

    if len(parts) == 1:
        new_state = not is_travel_mode()
        set_travel_mode(new_state)
        return "Travel mode " + ("enabled" if new_state else "disabled")

    sub = parts[1].lower()

    if sub == "on":
        set_travel_mode(True)
        return "Travel mode enabled"
    elif sub == "off":
        set_travel_mode(False)
        return "Travel mode disabled"
    elif sub == "status":
        return "Travel mode: " + ("enabled" if is_travel_mode() else "disabled")
    else:
        return "Usage: travel [on|off|status]"


__all__ = ["travel_command"]
