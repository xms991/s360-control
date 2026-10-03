#!/usr/bin/env python3
"""Feed CPU status to an MSI MEG CoreLiquid S360 and manage its fan curves.

The S360 has no temperature sensor of its own: its firmware interpolates
fan/pump duty cycles from the CPU temperature that software periodically
sends it.  This script sets the curves once, then feeds CPU temperature
(and frequency, for the display) every POLL_SECONDS.

If this service stops, the cooler simply keeps running at the duty cycle
implied by the last temperature it received.

Curves are (duty%, tempC) pairs.  Edit below.

IMPORTANT: the S360 stores at most 4 points per channel (the K360
supports 7; the S360 firmware silently drops points beyond the 4th).
"""

import glob
import logging
import sys
import time

from liquidctl.driver import find_liquidctl_devices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("s360-feed")

VENDOR_ID = 0x0DB0
PRODUCT_ID = 0x6A05
POLL_SECONDS = 2.0
RETRY_SECONDS = 5.0
MAX_CURVE_POINTS = 4  # S360 firmware limit; extra points are silently dropped

# (duty%, tempC) — device interpolates linearly between points.
FAN_PROFILE = [(25, 30), (40, 55), (60, 70), (100, 85)]
PUMP_PROFILE = [(70, 30), (80, 50), (90, 70), (100, 85)]
WATERBLOCK_PROFILE = [(30, 30), (45, 50), (65, 65), (100, 85)]

CPU_HWMON_NAMES = {"k10temp", "coretemp", "zenpower"}
CPU_TEMP_LABELS = {"Tctl", "Tdie", "Package id 0"}


def read_cpu_temp():
    """CPU temperature in °C from the best available hwmon sensor."""
    for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            with open(f"{hwmon}/name") as f:
                if f.read().strip() not in CPU_HWMON_NAMES:
                    continue
            for temp_file in sorted(glob.glob(f"{hwmon}/temp*_input")):
                label_file = temp_file.replace("_input", "_label")
                try:
                    with open(label_file) as f:
                        label = f.read().strip()
                except OSError:
                    label = None
                if label is None or label in CPU_TEMP_LABELS:
                    with open(temp_file) as f:
                        return int(f.read().strip()) / 1000.0
        except OSError:
            continue
    raise RuntimeError("no CPU temperature sensor found (tried k10temp/coretemp/zenpower)")


def read_cpu_freq():
    """Mean CPU frequency in MHz across all cores (0 if cpufreq is unavailable)."""
    freqs = []
    for f in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
        try:
            with open(f) as fh:
                freqs.append(int(fh.read().strip()) / 1000.0)
        except OSError:
            pass
    return int(sum(freqs) / len(freqs)) if freqs else 0


def find_s360():
    for dev in find_liquidctl_devices():
        if dev.vendor_id == VENDOR_ID and dev.product_id == PRODUCT_ID:
            return dev
    return None


def apply_profiles(dev):
    profiles = {"fans": FAN_PROFILE, "pump": PUMP_PROFILE, "waterblock-fan": WATERBLOCK_PROFILE}
    for channel, profile in profiles.items():
        if len(profile) > MAX_CURVE_POINTS:
            raise ValueError(
                f"{channel}: {len(profile)} points, but the S360 stores at most "
                f"{MAX_CURVE_POINTS}; extra points would be silently dropped"
            )
        dev.set_speed_profile(channel, profile)


def run():
    while True:
        dev = find_s360()
        if dev is None:
            log.warning("S360 not found, retrying in %ss", RETRY_SECONDS)
            time.sleep(RETRY_SECONDS)
            continue
        try:
            with dev.connect():
                log.info("connected, applying fan curves")
                apply_profiles(dev)
                log.info("curves applied, feeding CPU status every %ss", POLL_SECONDS)
                while True:
                    temp = read_cpu_temp()
                    freq = read_cpu_freq()
                    dev.set_hardware_status(temp, cpu_f=freq)
                    log.debug("cpu: %.1f°C %d MHz", temp, freq)
                    time.sleep(POLL_SECONDS)
        except Exception as exc:
            log.error("lost device (%s), reconnecting in %ss", exc, RETRY_SECONDS)
            time.sleep(RETRY_SECONDS)


if __name__ == "__main__":
    run()
