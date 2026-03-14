def detect_conflicts(visual_obs: str, thermal_readings: list) -> list:
    """
    Compare visual observations against thermal data.
    Returns a list of conflict descriptions if any are found.
    """
    conflicts = []
    obs_lower = visual_obs.lower()

    for reading in thermal_readings:
        # Conflict 1: Inspector says no leakage but thermal shows cold anomaly
        if "no leakage" in obs_lower and reading.get("moisture_flag"):
            conflicts.append(
                f"Inspector noted no leakage but thermal reading "
                f"shows coldspot at {reading['coldspot']}°C — "
                f"possible hidden moisture not visible during inspection."
            )

        # Conflict 2: Inspector notes dampness but thermal is normal range
        if "dampness" in obs_lower or "seepage" in obs_lower:
            try:
                coldspot = float(reading["coldspot"])
                if coldspot > 23.0:
                    conflicts.append(
                        f"Inspector noted dampness but thermal coldspot "
                        f"({coldspot}°C) is within normal range — "
                        f"moisture may be intermittent or dried at time of thermal scan."
                    )
            except (ValueError, KeyError):
                pass

    return conflicts