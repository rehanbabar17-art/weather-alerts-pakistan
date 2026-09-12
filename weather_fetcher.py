import requests
import os
import json
from datetime import datetime, timezone, timedelta

PKT = timezone(timedelta(hours=5))

try:
    from zoneinfo import ZoneInfo
    PK_TZ = ZoneInfo("Asia/Karachi")
except ImportError:
    PK_TZ = None

from locations.config import LOCATIONS

STORM_CODES = {95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82}

ICONS = {
    0: "\u2600\ufe0f Clear", 1: "\U0001f324\ufe0f Clear", 2: "\u26c5 Partly Cloudy", 3: "\u2601\ufe0f Overcast",
    45: "\U0001f32b\ufe0f Fog", 48: "\U0001f32b\ufe0f Fog",
    51: "\U0001f326\ufe0f Drizzle", 53: "\U0001f327\ufe0f Drizzle", 55: "\U0001f327\ufe0f Heavy Drizzle",
    61: "\U0001f327\ufe0f Light Rain", 63: "\U0001f327\ufe0f Rain", 65: "\U0001f327\ufe0f Heavy Rain",
    71: "\U0001f328\ufe0f Light Snow", 73: "\U0001f328\ufe0f Snow", 75: "\U0001f328\ufe0f Heavy Snow", 77: "\U0001f328\ufe0f Snow",
    80: "\U0001f326\ufe0f Light Rain", 81: "\U0001f327\ufe0f Rain", 82: "\u26c8\ufe0f Heavy Rain",
    85: "\U0001f328\ufe0f Snow", 86: "\U0001f328\ufe0f Heavy Snow",
    95: "\u26c8\ufe0f Thunderstorm", 96: "\u26c8\ufe0f Thunderstorm", 99: "\u26c8\ufe0f Thunderstorm"
}

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_state.json")

# Hourly change thresholds
HR_TEMP_CHANGE = 5.0     # C
HR_RAIN_CHANGE = 10.0    # mm (total over forecast window)
HR_STORM_NEW = True      # storm appeared
HR_SNOW_NEW = True       # snow appeared
HR_WIND_CHANGE = 25.0    # km/h


def get_pk_now():
    if PK_TZ:
        return datetime.now(PK_TZ)
    return datetime.now(PKT)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_daily_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code,wind_speed_10m_max",
        "timezone": "Asia/Karachi", "forecast_days": 3
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("daily", {})
    except Exception as e:
        return {"error": str(e)}


def fetch_hourly_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m",
        "timezone": "Asia/Karachi", "forecast_days": 2
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("hourly", {})
    except Exception as e:
        return {"error": str(e)}


def format_location_compact(location, daily):
    if "error" in daily:
        return f"\u2753 {location['name']} - Failed to fetch\n"
    dates = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    prec = daily.get("precipitation_sum", [])
    prob = daily.get("precipitation_probability_max", [])
    wc = daily.get("weather_code", [])
    lines = [f"\U0001f4cd {location['name']} ({location['city']})"]
    for i, date in enumerate(dates):
        code = wc[i] if i < len(wc) else 0
        icon = ICONS.get(code, "\U0001f321\ufe0f Unknown")
        t_max = tmax[i] if i < len(tmax) else "?"
        t_min = tmin[i] if i < len(tmin) else "?"
        rain = prec[i] if i < len(prec) else 0
        rain_prob = prob[i] if i < len(prob) else 0
        day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%a %d")
        rain_str = f" | Rain: {rain}mm ({rain_prob}%)" if rain > 0 else ""
        lines.append(f"  {icon} {day_name}: {t_min}\u00b0C - {t_max}\u00b0C{rain_str}")
    return "\n".join(lines)


def detect_major_daily_changes(location_name, old_daily, new_daily):
    changes = []
    if not old_daily or "error" in new_daily or "error" in old_daily:
        return changes

    old_dates = old_daily.get("time", [])
    new_dates = new_daily.get("time", [])
    old_codes = old_daily.get("weather_code", [])
    new_codes = new_daily.get("weather_code", [])
    old_prec = old_daily.get("precipitation_sum", [])
    new_prec = new_daily.get("precipitation_sum", [])
    old_tmax = old_daily.get("temperature_2m_max", [])
    new_tmax = new_daily.get("temperature_2m_max", [])
    old_tmin = old_daily.get("temperature_2m_min", [])
    new_tmin = new_daily.get("temperature_2m_min", [])
    old_wind = old_daily.get("wind_speed_10m_max", [])
    new_wind = new_daily.get("wind_speed_10m_max", [])

    old_map = {}
    for i, d in enumerate(old_dates):
        old_map[d] = {
            "code": old_codes[i] if i < len(old_codes) else 0,
            "precip": old_prec[i] if i < len(old_prec) else 0,
            "tmax": old_tmax[i] if i < len(old_tmax) else None,
            "tmin": old_tmin[i] if i < len(old_tmin) else None,
            "wind": old_wind[i] if i < len(old_wind) else 0,
        }

    for i, date in enumerate(new_dates):
        new_code = new_codes[i] if i < len(new_codes) else 0
        new_rain = new_prec[i] if i < len(new_prec) else 0
        new_tm = new_tmax[i] if i < len(new_tmax) else None
        new_tn = new_tmin[i] if i < len(new_tmin) else None
        new_w = new_wind[i] if i < len(new_wind) else 0
        day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%a %d")

        old = old_map.get(date)
        if not old:
            if new_code in STORM_CODES | SNOW_CODES or new_rain >= 5:
                changes.append(f"\U0001f4c5 {day_name}: Severe weather now expected")
            continue

        old_code = old["code"]
        old_rain = old["precip"]
        old_w = old["wind"]

        if new_code in STORM_CODES and old_code not in STORM_CODES:
            changes.append(f"\U0001f4c5 {day_name}: Storm now expected")
        if new_code in SNOW_CODES and old_code not in SNOW_CODES:
            changes.append(f"\U0001f4c5 {day_name}: Snow now expected")
        if old_rain < 1 and new_rain >= 5:
            changes.append(f"\U0001f4c5 {day_name}: Rain now expected ({new_rain}mm)")
        if new_rain >= 15 and old_rain < 5:
            changes.append(f"\U0001f4c5 {day_name}: Heavy rain now expected ({new_rain}mm)")
        if isinstance(new_w, (int, float)) and isinstance(old_w, (int, float)):
            if new_w >= 60 and old_w < 40:
                changes.append(f"\U0001f4c5 {day_name}: High winds now expected ({new_w}km/h)")
        if isinstance(new_tn, (int, float)) and isinstance(old.get("tmin"), (int, float)):
            if new_tn <= 0 and old["tmin"] > 2:
                changes.append(f"\U0001f4c5 {day_name}: Freezing temps now expected ({new_tn}\u00b0C)")
        if isinstance(new_tm, (int, float)) and isinstance(old.get("tmax"), (int, float)):
            if new_tm >= 42 and old["tmax"] < 38:
                changes.append(f"\U0001f4c5 {day_name}: Extreme heat now expected ({new_tm}\u00b0C)")

    return list(dict.fromkeys(changes))


def detect_hourly_changes(location_name, old_hourly, new_hourly):
    """Detect drastic changes in hourly forecast compared to last fetch."""
    changes = []
    if not old_hourly or "error" in new_hourly or "error" in old_hourly:
        return changes

    old_times = old_hourly.get("time", [])
    new_times = new_hourly.get("time", [])
    old_temps = old_hourly.get("temperature_2m", [])
    new_temps = new_hourly.get("temperature_2m", [])
    old_codes = old_hourly.get("weather_code", [])
    new_codes = new_hourly.get("weather_code", [])
    old_precips = old_hourly.get("precipitation", [])
    new_precips = new_hourly.get("precipitation", [])
    old_winds = old_hourly.get("wind_speed_10m", [])
    new_winds = new_hourly.get("wind_speed_10m", [])
    old_probs = old_hourly.get("precipitation_probability", [])
    new_probs = new_hourly.get("precipitation_probability", [])

    # Build map of old data by hour
    old_map = {}
    for i, t in enumerate(old_times):
        old_map[t] = {
            "temp": old_temps[i] if i < len(old_temps) else None,
            "code": old_codes[i] if i < len(old_codes) else 0,
            "rain": old_precips[i] if i < len(old_precips) else 0,
            "wind": old_winds[i] if i < len(old_winds) else 0,
            "prob": old_probs[i] if i < len(old_probs) else 0,
        }

    # Track which timestamps had storm/snow in old
    for i, t in enumerate(new_times):
        new_temp = new_temps[i] if i < len(new_temps) else None
        new_code = new_codes[i] if i < len(new_codes) else 0
        new_rain = new_precips[i] if i < len(new_precips) else 0
        new_wind = new_winds[i] if i < len(new_winds) else 0
        new_prob = new_probs[i] if i < len(new_probs) else 0

        old = old_map.get(t)
        hour_str = t.replace("T", " ")[:16] if t else ""

        if old is None:
            # New hour appeared in forecast
            if new_code in STORM_CODES:
                changes.append(f"\U0001f4c5 {hour_str}: Storm now expected")
            elif new_code in SNOW_CODES:
                changes.append(f"\U0001f4c5 {hour_str}: Snow now expected")
            elif new_rain >= 5:
                changes.append(f"\U0001f4c5 {hour_str}: Heavy rain ({new_rain}mm) now expected")
            continue

        old_code = old["code"]
        old_rain = old["rain"]
        old_temp = old["temp"]
        old_wind = old["wind"]

        # Storm/snow appeared
        if new_code in STORM_CODES and old_code not in STORM_CODES:
            changes.append(f"\U0001f4c5 {hour_str}: Storm now expected")
        if new_code in SNOW_CODES and old_code not in SNOW_CODES:
            changes.append(f"\U0001f4c5 {hour_str}: Snow now expected")

        # Rain appeared/major increase
        if new_rain >= 5 and old_rain < 1:
            changes.append(f"\U0001f4c5 {hour_str}: Heavy rain now expected ({new_rain}mm)")

        # Temperature swing
        if isinstance(new_temp, (int, float)) and isinstance(old_temp, (int, float)):
            if abs(new_temp - old_temp) >= HR_TEMP_CHANGE:
                direction = "warmer" if new_temp > old_temp else "cooler"
                changes.append(f"\U0001f4c5 {hour_str}: Temp {direction} ({old_temp}C -> {new_temp}C)")

        # Wind jump
        if isinstance(new_wind, (int, float)) and isinstance(old_wind, (int, float)):
            if new_wind >= 60 and old_wind < 40:
                changes.append(f"\U0001f4c5 {hour_str}: High winds now ({new_wind}km/h)")

    return list(dict.fromkeys(changes))


def send_ntfy(topic, title, message, priority="default"):
    url = f"https://ntfy.sh/{topic}"
    try:
        resp = requests.post(
            url, data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority, "Tags": "weather"},
            timeout=10
        )
        resp.raise_for_status()
        print(f"Sent to {topic}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


if __name__ == "__main__":
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        raise SystemExit("Error: NTFY_TOPIC environment variable is required.")
    pk_now = get_pk_now()
    today_str = pk_now.strftime("%Y-%m-%d")
    previous_state = load_state()
    all_daily_changes = []
    all_hourly_changes = []
    new_state = {}
    valid_locations = []

    for loc in LOCATIONS:
        loc_key = f"{loc['name']}_{loc['city']}"
        daily = fetch_daily_forecast(loc["lat"], loc["lon"])
        hourly = fetch_hourly_forecast(loc["lat"], loc["lon"])

        if "error" in daily:
            print(f"  Skipping {loc['name']} - daily fetch failed: {daily['error']}")
            continue

        valid_locations.append((loc, daily))

        old_daily = previous_state.get(loc_key, {}).get("daily")
        old_hourly = previous_state.get(loc_key, {}).get("hourly")

        # Changes compared to last run
        daily_changes = detect_major_daily_changes(loc["name"], old_daily, daily)
        hourly_changes = detect_hourly_changes(loc["name"], old_hourly, hourly)

        if daily_changes:
            all_daily_changes.append((loc["name"], daily_changes))
        if hourly_changes:
            all_hourly_changes.append((loc["name"], hourly_changes))

        new_state[loc_key] = {
            "daily": daily,
            "hourly": hourly if "error" not in hourly else previous_state.get(loc_key, {}).get("hourly", {}),
            "timestamp": pk_now.isoformat()
        }

    save_state(new_state)

    last_daily_date = previous_state.get("_last_daily_report_date")
    is_6am_window = pk_now.hour == 6
    already_sent_today = last_daily_date == today_str

    # Daily 6 AM report (once per day)
    sent_notification = False
    if is_6am_window and not already_sent_today and valid_locations:
        report_lines = [f"\u2601\ufe0f Daily Forecast\n{pk_now.strftime('%A %B %d')}\n"]
        for loc, daily in valid_locations:
            report_lines.append(format_location_compact(loc, daily))
        report = "\n\n".join(report_lines)
        print(report)
        send_ntfy(topic, f"Daily Forecast {pk_now.strftime('%b %d')}", report, priority="default")
        new_state["_last_daily_report_date"] = today_str
        save_state(new_state)
        sent_notification = True

    # Drastic hourly change alert (any time, including daily aggregate)
    if all_hourly_changes:
        report = f"\u26a1 Hourly Weather Change\n{pk_now.strftime('%B %d, %Y %I:%M %p')}\n\n"
        for loc_name, changes in all_hourly_changes:
            report += f"\U0001f4cd {loc_name}\n"
            report += "\n".join(f"  {c}" for c in changes)
            report += "\n\n"
        print(report)
        send_ntfy(topic, f"Hourly Alert", report.strip(), priority="high")
        sent_notification = True

    # Major daily change alert
    if all_daily_changes:
        report = f"\u26a1 Weather Alert\n{pk_now.strftime('%B %d, %Y %I:%M %p')}\n\n"
        for loc_name, changes in all_daily_changes:
            report += f"\U0001f4cd {loc_name}\n"
            report += "\n".join(f"  {c}" for c in changes)
            report += "\n\n"
        print(report)
        send_ntfy(topic, f"Weather Alert", report.strip(), priority="high")
        sent_notification = True

    if not sent_notification:
        print(f"[{pk_now.strftime('%I:%M %p')}] No major changes. No notification sent.")
