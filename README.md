# weather-alerts-pakistan

Hourly weather monitoring and alerts using Open-Meteo + ntfy.sh.

## Features

- Hourly change detection (storms, snow, heavy rain, high winds, temperature swings)
- Daily 6 AM forecast report
- Severe weather push notifications via ntfy.sh
- State persistence between runs for accurate diff alerts

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

Set the ntfy topic (required):

```bash
export NTFY_TOPIC=your-topic-name
```

Provide the locations to monitor (required). Either:

- Pass a JSON array via env var (used in CI):
  ```bash
  export LOCATIONS_JSON='[{"name":"My City","city":"My City","country":"CC","lat":0.0,"lon":0.0}]'
  ```
- Or create a private git-ignored file at `locations/config.local.py` with a `LOCATIONS` list variable (see the loader in `locations/config.py`).

Subscribe to alerts on your phone:
1. Install the ntfy app ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/us/app/ntfy/id1625396347))
2. Subscribe to your topic
3. Or view at `https://ntfy.sh/<your-topic-name>`

## Run manually

```bash
python weather_fetcher.py
```

## Run continuously (7 days)

```bash
python scheduler.py
```

## Run on schedule (cron)

```bash
0 * * * * cd /path/to/weather-alerts-pakistan && LOCATIONS_JSON='...' NTFY_TOPIC='...' /usr/bin/python3 weather_fetcher.py >> logs/cron.log 2>&1
```

## Alert Conditions

- Thunderstorms expected
- Snow expected
- Heavy rain (>2mm)
- High winds (>50 km/h)
- Temperature drop >5°C compared to previous reading

## API

Uses [Open-Meteo](https://open-meteo.com/) — free, no API key required.
