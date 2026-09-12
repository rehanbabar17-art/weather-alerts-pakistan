"""
scheduler.py - Runs weather_fetcher.py periodically.
Usage: python scheduler.py
"""
import time
import os
import subprocess

CHECK_INTERVAL = 3600  # 1 hour


def main():
    while True:
        try:
            subprocess.run(["python3", "weather_fetcher.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running weather_fetcher: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
