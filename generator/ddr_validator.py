from __future__ import annotations

from typing import Any

ALLOWED_SEVERITY = {"Critical", "High", "Medium", "Low"}
ALLOWED_PRIORITY = {"Immediate", "Short-term", "Long-term"}
DEFAULT_NA = "Not Available"


def normalize_ddr(ddr: dict[str, Any] | None, structured: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize LLM JSON into the exact shape expected by downstream PDF assembly."""
    ddr = ddr or {}
    structured = structured or {}

    known_areas = [
        _clean_text(a.get("area"))
        for a in structured.get("area_data", [])
        if isinstance(a, dict) and _clean_text(a.get("area")) != DEFAULT_NA
    ]
    seen = set()
    ordered_known_areas = []
    for area in known_areas:
        key = _area_key(area)
        if key not in seen:
            seen.add(key)
            ordered_known_areas.append(area)

    by_area_struct = {
        _area_key(a.get("area")): a
        for a in structured.get("area_data", [])
        if isinstance(a, dict)
    }

    normalized = {
        "property_metadata": _normalize_property_metadata(ddr.get("property_metadata"), structured),
        "property_summary": _clean_text(ddr.get("property_summary")),
        "area_observations": _normalize_area_observations(ddr.get("area_observations"), ordered_known_areas, by_area_struct),
        "root_causes": _normalize_root_causes(ddr.get("root_causes"), ordered_known_areas),
        "severity_assessment": _normalize_severity(ddr.get("severity_assessment"), ordered_known_areas, by_area_struct),
        "recommended_actions": _normalize_actions(ddr.get("recommended_actions"), ordered_known_areas),
        "additional_notes": _clean_text(ddr.get("additional_notes")),
        "missing_information": _normalize_missing_info(ddr.get("missing_information")),
    }

    return normalized


def validate_ddr_schema(ddr: dict[str, Any], structured: dict[str, Any] | None = None) -> list[str]:
    """Return a list of schema violations; empty list means the DDR is acceptable."""
    issues: list[str] = []

    required_top_keys = [
        "property_metadata",
        "property_summary",
        "area_observations",
        "root_causes",
        "severity_assessment",
        "recommended_actions",
        "additional_notes",
        "missing_information",
    ]

    for key in required_top_keys:
        if key not in ddr:
            issues.append(f"Missing top-level key: {key}")

    if not isinstance(ddr.get("area_observations", []), list):
        issues.append("area_observations must be a list")
    if not isinstance(ddr.get("root_causes", []), list):
        issues.append("root_causes must be a list")
    if not isinstance(ddr.get("severity_assessment", []), list):
        issues.append("severity_assessment must be a list")
    if not isinstance(ddr.get("recommended_actions", []), list):
        issues.append("recommended_actions must be a list")
    if not isinstance(ddr.get("missing_information", []), list):
        issues.append("missing_information must be a list")

    seen_obs = set()
    for item in ddr.get("area_observations", []):
        area = _clean_text(item.get("area"))
        level = _clean_text(item.get("severity"))
        if level not in ALLOWED_SEVERITY:
            issues.append(f"Invalid severity in area_observations for {area}: {level}")
        k = _area_key(area)
        if k in seen_obs:
            issues.append(f"Duplicate area in area_observations: {area}")
        seen_obs.add(k)

    seen_sv = set()
    for item in ddr.get("severity_assessment", []):
        area = _clean_text(item.get("area"))
        level = _clean_text(item.get("level"))
        if level not in ALLOWED_SEVERITY:
            issues.append(f"Invalid level in severity_assessment for {area}: {level}")
        k = _area_key(area)
        if k in seen_sv:
            issues.append(f"Duplicate area in severity_assessment: {area}")
        seen_sv.add(k)

    seen_action = set()
    for item in ddr.get("recommended_actions", []):
        area = _clean_text(item.get("area"))
        priority = _clean_text(item.get("priority"))
        if priority not in ALLOWED_PRIORITY:
            issues.append(f"Invalid priority in recommended_actions for {area}: {priority}")
        k = _area_key(area)
        if k in seen_action:
            issues.append(f"Duplicate area in recommended_actions: {area}")
        seen_action.add(k)

    if structured:
        expected_areas = {
            _area_key(a.get("area"))
            for a in structured.get("area_data", [])
            if isinstance(a, dict)
        }
        reported_areas = {_area_key(a.get("area")) for a in ddr.get("area_observations", [])}
        missing = [a for a in expected_areas if a and a not in reported_areas]
        if missing:
            issues.append(f"area_observations missing areas from extracted data: {', '.join(sorted(missing))}")

    return issues


def build_repair_feedback(issues: list[str]) -> str:
    if not issues:
        return "No explicit validation issues were captured, but output still requires strict schema compliance."
    return "\n".join(f"- {i}" for i in issues)


def _normalize_property_metadata(meta: Any, structured: dict[str, Any]) -> dict[str, str]:
    meta = meta if isinstance(meta, dict) else {}
    structured_meta = structured.get("property_metadata") or {}
    return {
        "customer_name": _clean_text(meta.get("customer_name") or structured_meta.get("customer_name")),
        "inspection_date": _clean_text(meta.get("inspection_date") or structured_meta.get("inspection_date")),
        "inspector": _clean_text(meta.get("inspector") or structured_meta.get("inspector")),
        "address": _clean_text(meta.get("address") or structured_meta.get("address")),
    }


def _normalize_area_observations(raw: Any, known_areas: list[str], by_area_struct: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = raw if isinstance(raw, list) else []
    by_area: dict[str, dict[str, Any]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        area = _clean_text(row.get("area"))
        key = _area_key(area)
        if not key:
            continue

        conflicts = row.get("conflicts") if isinstance(row.get("conflicts"), list) else []
        normalized_row = {
            "area": area,
            "visual_observation": _clean_text(row.get("visual_observation")),
            "thermal_reading": _clean_text(row.get("thermal_reading")),
            "combined_finding": _clean_text(row.get("combined_finding")),
            "conflicts": _unique_texts(conflicts),
            "severity": _normalize_severity_value(row.get("severity"), fallback="Medium"),
        }

        if key in by_area:
            by_area[key] = _merge_area_obs(by_area[key], normalized_row)
        else:
            by_area[key] = normalized_row

    result = [by_area[_area_key(a)] for a in known_areas if _area_key(a) in by_area]

    for area in known_areas:
        key = _area_key(area)
        if key in by_area:
            continue
        struct_row = by_area_struct.get(key, {})
        thermal_summary = ((struct_row.get("thermal") or {}).get("summary") if isinstance(struct_row, dict) else None)
        result.append({
            "area": area,
            "visual_observation": _clean_text(struct_row.get("visual_obs")) if isinstance(struct_row, dict) else DEFAULT_NA,
            "thermal_reading": _clean_text(thermal_summary),
            "combined_finding": DEFAULT_NA,
            "conflicts": _unique_texts(struct_row.get("conflicts") if isinstance(struct_row, dict) else []),
            "severity": _severity_from_struct(struct_row),
        })

    # Keep any additional model-generated areas after expected areas.
    known_keys = {_area_key(a) for a in known_areas}
    extras = [v for k, v in by_area.items() if k not in known_keys]
    result.extend(extras)

    return result


def _normalize_root_causes(raw: Any, known_areas: list[str]) -> list[dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    by_area: dict[str, dict[str, str]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        area = _clean_text(row.get("area"))
        key = _area_key(area)
        if not key:
            continue
        if key not in by_area:
            by_area[key] = {"area": area, "cause": _clean_text(row.get("cause"))}

    result = [by_area[_area_key(a)] for a in known_areas if _area_key(a) in by_area]
    for area in known_areas:
        if _area_key(area) not in by_area:
            result.append({"area": area, "cause": DEFAULT_NA})
    return result


def _normalize_severity(raw: Any, known_areas: list[str], by_area_struct: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    by_area: dict[str, dict[str, str]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        area = _clean_text(row.get("area"))
        key = _area_key(area)
        if not key:
            continue

        by_area[key] = {
            "area": area,
            "level": _normalize_severity_value(row.get("level"), fallback=None) or _severity_from_struct(by_area_struct.get(key, {})),
            "reasoning": _clean_text(row.get("reasoning")),
        }

    result = [by_area[_area_key(a)] for a in known_areas if _area_key(a) in by_area]
    for area in known_areas:
        key = _area_key(area)
        if key in by_area:
            continue
        struct_row = by_area_struct.get(key, {})
        result.append(
            {
                "area": area,
                "level": _severity_from_struct(struct_row),
                "reasoning": DEFAULT_NA,
            }
        )
    return result


def _normalize_actions(raw: Any, known_areas: list[str]) -> list[dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    by_area: dict[str, dict[str, str]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        area = _clean_text(row.get("area"))
        key = _area_key(area)
        if not key:
            continue
        by_area[key] = {
            "area": area,
            "action": _clean_text(row.get("action")),
            "priority": _normalize_priority_value(row.get("priority"), fallback="Short-term"),
        }

    result = [by_area[_area_key(a)] for a in known_areas if _area_key(a) in by_area]
    for area in known_areas:
        if _area_key(area) not in by_area:
            result.append({"area": area, "action": DEFAULT_NA, "priority": "Short-term"})
    return result


def _normalize_missing_info(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return [DEFAULT_NA]
    items = _unique_texts(raw)
    return items or [DEFAULT_NA]


def _severity_from_struct(struct_row: dict[str, Any] | None) -> str:
    if not isinstance(struct_row, dict):
        return "Medium"
    if struct_row.get("has_moisture_flag"):
        return "High"
    conflicts = struct_row.get("conflicts") if isinstance(struct_row.get("conflicts"), list) else []
    if conflicts:
        return "High"
    return "Medium"


def _merge_area_obs(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(old)
    for key in ["visual_observation", "thermal_reading", "combined_finding"]:
        if merged.get(key) == DEFAULT_NA and new.get(key) != DEFAULT_NA:
            merged[key] = new[key]

    old_sev = merged.get("severity")
    new_sev = new.get("severity")
    merged["severity"] = _higher_severity(old_sev, new_sev)
    merged["conflicts"] = _unique_texts((merged.get("conflicts") or []) + (new.get("conflicts") or []))
    return merged


def _higher_severity(a: str, b: str) -> str:
    order = ["Low", "Medium", "High", "Critical"]
    a = a if a in order else "Medium"
    b = b if b in order else "Medium"
    return a if order.index(a) >= order.index(b) else b


def _normalize_severity_value(value: Any, fallback: str | None) -> str:
    text = _clean_text(value)
    return text if text in ALLOWED_SEVERITY else (fallback or "Medium")


def _normalize_priority_value(value: Any, fallback: str) -> str:
    text = _clean_text(value)
    return text if text in ALLOWED_PRIORITY else fallback


def _unique_texts(values: list[Any]) -> list[str]:
    seen = set()
    out = []
    for val in values:
        text = _clean_text(val)
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _clean_text(value: Any) -> str:
    if value is None:
        return DEFAULT_NA
    text = str(value).strip()
    return text if text else DEFAULT_NA


def _area_key(name: Any) -> str:
    return _clean_text(name).lower()

