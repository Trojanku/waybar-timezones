#!/usr/bin/env python3
"""Omarchy Waybar Timezones – a GTK4 Layer Shell popup for Waybar.

Inspired by prettytimezones.com. Click the waybar clock to toggle.
Search and add cities, remove them with ×. Config persists in
~/.config/omarchy-timezones/cities.json.
Colors are pulled from the active omarchy theme automatically.
"""

import gi
import sys
import signal
import os
import subprocess
import math
import json
import re

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gdk, GLib, Graphene
from gi.repository import Gtk4LayerShell as LayerShell

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones

# ── Configuration ────────────────────────────────────────────────────

CONFIG_DIR = os.path.expanduser("~/.config/omarchy-timezones")
CONFIG_FILE = os.path.join(CONFIG_DIR, "cities.json")

DEFAULT_CITIES = [
    ("🇺🇸", "San Francisco", "America/Los_Angeles"),
    ("🇵🇱", "Warsaw", "Europe/Warsaw"),
    ("🇦🇺", "Brisbane", "Australia/Brisbane"),
]

UPDATE_INTERVAL_SECONDS = 30


# ── Persistence ─────────────────────────────────────────────────────

def load_cities():
    """Load cities from JSON config, falling back to defaults."""
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            return [(c["flag"], c["city"], c["tz"]) for c in data]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return list(DEFAULT_CITIES)


def save_cities(cities):
    """Save cities list to JSON config."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = [{"flag": f, "city": c, "tz": t} for f, c, t in cities]
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Timezone database ───────────────────────────────────────────────

TIMEZONE_DATABASE = {
    "San Francisco": ("America/Los_Angeles", "🇺🇸"),
    "Los Angeles": ("America/Los_Angeles", "🇺🇸"),
    "New York": ("America/New_York", "🇺🇸"),
    "Chicago": ("America/Chicago", "🇺🇸"),
    "Denver": ("America/Denver", "🇺🇸"),
    "Houston": ("America/Chicago", "🇺🇸"),
    "Phoenix": ("America/Phoenix", "🇺🇸"),
    "Seattle": ("America/Los_Angeles", "🇺🇸"),
    "Miami": ("America/New_York", "🇺🇸"),
    "Boston": ("America/New_York", "🇺🇸"),
    "Atlanta": ("America/New_York", "🇺🇸"),
    "Detroit": ("America/Detroit", "🇺🇸"),
    "Honolulu": ("Pacific/Honolulu", "🇺🇸"),
    "Anchorage": ("America/Anchorage", "🇺🇸"),
    "Toronto": ("America/Toronto", "🇨🇦"),
    "Vancouver": ("America/Vancouver", "🇨🇦"),
    "Montreal": ("America/Montreal", "🇨🇦"),
    "Mexico City": ("America/Mexico_City", "🇲🇽"),
    "São Paulo": ("America/Sao_Paulo", "🇧🇷"),
    "Buenos Aires": ("America/Argentina/Buenos_Aires", "🇦🇷"),
    "Lima": ("America/Lima", "🇵🇪"),
    "Bogotá": ("America/Bogota", "🇨🇴"),
    "Santiago": ("America/Santiago", "🇨🇱"),
    "London": ("Europe/London", "🇬🇧"),
    "Paris": ("Europe/Paris", "🇫🇷"),
    "Berlin": ("Europe/Berlin", "🇩🇪"),
    "Madrid": ("Europe/Madrid", "🇪🇸"),
    "Rome": ("Europe/Rome", "🇮🇹"),
    "Amsterdam": ("Europe/Amsterdam", "🇳🇱"),
    "Brussels": ("Europe/Brussels", "🇧🇪"),
    "Vienna": ("Europe/Vienna", "🇦🇹"),
    "Zurich": ("Europe/Zurich", "🇨🇭"),
    "Stockholm": ("Europe/Stockholm", "🇸🇪"),
    "Oslo": ("Europe/Oslo", "🇳🇴"),
    "Copenhagen": ("Europe/Copenhagen", "🇩🇰"),
    "Helsinki": ("Europe/Helsinki", "🇫🇮"),
    "Warsaw": ("Europe/Warsaw", "🇵🇱"),
    "Prague": ("Europe/Prague", "🇨🇿"),
    "Budapest": ("Europe/Budapest", "🇭🇺"),
    "Bucharest": ("Europe/Bucharest", "🇷🇴"),
    "Athens": ("Europe/Athens", "🇬🇷"),
    "Lisbon": ("Europe/Lisbon", "🇵🇹"),
    "Dublin": ("Europe/Dublin", "🇮🇪"),
    "Edinburgh": ("Europe/London", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    "Moscow": ("Europe/Moscow", "🇷🇺"),
    "Istanbul": ("Europe/Istanbul", "🇹🇷"),
    "Kyiv": ("Europe/Kyiv", "🇺🇦"),
    "Cairo": ("Africa/Cairo", "🇪🇬"),
    "Lagos": ("Africa/Lagos", "🇳🇬"),
    "Nairobi": ("Africa/Nairobi", "🇰🇪"),
    "Johannesburg": ("Africa/Johannesburg", "🇿🇦"),
    "Casablanca": ("Africa/Casablanca", "🇲🇦"),
    "Dubai": ("Asia/Dubai", "🇦🇪"),
    "Riyadh": ("Asia/Riyadh", "🇸🇦"),
    "Tehran": ("Asia/Tehran", "🇮🇷"),
    "Mumbai": ("Asia/Kolkata", "🇮🇳"),
    "Delhi": ("Asia/Kolkata", "🇮🇳"),
    "Bangalore": ("Asia/Kolkata", "🇮🇳"),
    "Kolkata": ("Asia/Kolkata", "🇮🇳"),
    "Karachi": ("Asia/Karachi", "🇵🇰"),
    "Dhaka": ("Asia/Dhaka", "🇧🇩"),
    "Bangkok": ("Asia/Bangkok", "🇹🇭"),
    "Jakarta": ("Asia/Jakarta", "🇮🇩"),
    "Singapore": ("Asia/Singapore", "🇸🇬"),
    "Kuala Lumpur": ("Asia/Kuala_Lumpur", "🇲🇾"),
    "Ho Chi Minh City": ("Asia/Ho_Chi_Minh", "🇻🇳"),
    "Manila": ("Asia/Manila", "🇵🇭"),
    "Hong Kong": ("Asia/Hong_Kong", "🇭🇰"),
    "Taipei": ("Asia/Taipei", "🇹🇼"),
    "Shanghai": ("Asia/Shanghai", "🇨🇳"),
    "Beijing": ("Asia/Shanghai", "🇨🇳"),
    "Seoul": ("Asia/Seoul", "🇰🇷"),
    "Tokyo": ("Asia/Tokyo", "🇯🇵"),
    "Osaka": ("Asia/Tokyo", "🇯🇵"),
    "Sydney": ("Australia/Sydney", "🇦🇺"),
    "Melbourne": ("Australia/Melbourne", "🇦🇺"),
    "Brisbane": ("Australia/Brisbane", "🇦🇺"),
    "Perth": ("Australia/Perth", "🇦🇺"),
    "Auckland": ("Pacific/Auckland", "🇳🇿"),
    "Fiji": ("Pacific/Fiji", "🇫🇯"),
    "Reykjavik": ("Atlantic/Reykjavik", "🇮🇸"),
    "Tel Aviv": ("Asia/Jerusalem", "🇮🇱"),
    "Doha": ("Asia/Qatar", "🇶🇦"),
}


def _iana_to_city(tz_name):
    """Extract city name from IANA tz string: 'America/Los_Angeles' → 'Los Angeles'."""
    return tz_name.rsplit("/", 1)[-1].replace("_", " ")


def search_timezones(query):
    """Search for cities matching query. Returns list of (flag, city, tz), max 20."""
    if len(query) < 2:
        return []
    q = query.lower()
    results = []

    # Search curated database first
    for city, (tz, flag) in TIMEZONE_DATABASE.items():
        if q in city.lower():
            results.append((flag, city, tz))

    # Fallback: search IANA timezone names
    if len(results) < 20:
        seen_tz = {r[2] for r in results}
        for tz_name in sorted(available_timezones()):
            if "/" not in tz_name:
                continue
            city_name = _iana_to_city(tz_name)
            if q in city_name.lower() and tz_name not in seen_tz:
                results.append(("🌐", city_name, tz_name))
                seen_tz.add(tz_name)
            if len(results) >= 20:
                break

    return results[:20]


# ── Theme colors ─────────────────────────────────────────────────────

HEX_COLOR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def normalize_hex(value):
    """Normalize '#RRGGBB' strings and reject invalid colors."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not HEX_COLOR_RE.match(value):
        return None
    if not value.startswith("#"):
        value = f"#{value}"
    return value.lower()


def load_theme_colors():
    """Read colors from the active omarchy theme's colors.toml."""
    colors_path = os.path.expanduser("~/.config/omarchy/current/theme/colors.toml")
    colors = {}
    line_re = re.compile(
        r"""^\s*([A-Za-z0-9_]+)\s*=\s*["']?(#?[0-9a-fA-F]{6})["']?(?:\s+#.*)?\s*$"""
    )
    try:
        with open(colors_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                match = line_re.match(line)
                if not match:
                    continue
                key = match.group(1).lower()
                val = match.group(2)
                colors[key] = normalize_hex(val)
    except FileNotFoundError:
        pass
    return colors


def hex_to_rgb(h):
    """Convert '#rrggbb' to (r, g, b) floats."""
    h = normalize_hex(h) or "#000000"
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    """Convert (r, g, b) floats to '#rrggbb'."""
    return f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"


def blend_rgb(a, b, t):
    """Blend two RGB tuples (0..1) by t (0..1)."""
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def lighten(hex_color, amount=0.15):
    """Lighten a hex color by blending toward white."""
    r, g, b = hex_to_rgb(hex_color)
    r = r + (1 - r) * amount
    g = g + (1 - g) * amount
    b = b + (1 - b) * amount
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def darken(hex_color, amount=0.3):
    """Darken a hex color by blending toward black."""
    r, g, b = hex_to_rgb(hex_color)
    r = r * (1 - amount)
    g = g * (1 - amount)
    b = b * (1 - amount)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def mix_hex(a, b, t):
    """Blend two hex colors and return hex result."""
    return rgb_to_hex(blend_rgb(hex_to_rgb(a), hex_to_rgb(b), t))


def relative_luminance(hex_color):
    """Return WCAG relative luminance for a hex color."""
    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = hex_to_rgb(hex_color)
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def pick_theme_color(theme, keys, fallback):
    """Pick first available color from theme keys or fallback."""
    for key in keys:
        value = normalize_hex(theme.get(key.lower(), ""))
        if value:
            return value
    return normalize_hex(fallback) or "#000000"


def build_semantic_theme(theme):
    """Map Omarchy theme keys to robust semantic UI colors."""
    bg = pick_theme_color(theme, ["background"], "#1a1b26")
    fg = pick_theme_color(theme, ["foreground", "color15", "color7"], "#a9b1d6")
    accent = pick_theme_color(
        theme,
        ["accent", "color4", "color12", "selection_background"],
        "#7aa2f7",
    )
    cursor = pick_theme_color(
        theme,
        ["cursor", "selection_foreground", "foreground"],
        "#c0caf5",
    )

    is_light_theme = relative_luminance(bg) > 0.46

    # Derive neutral UI surfaces from bg/fg mix so both light and dark themes
    # keep consistent contrast regardless of terminal palette conventions.
    dim = mix_hex(fg, bg, 0.44 if is_light_theme else 0.5)
    surface = mix_hex(bg, fg, 0.09 if is_light_theme else 0.11)
    surface2 = mix_hex(bg, fg, 0.16 if is_light_theme else 0.2)

    day_seed = pick_theme_color(theme, ["color11", "color3", "accent"], accent)
    night_seed = pick_theme_color(theme, ["color4", "accent", "color12"], accent)
    day = mix_hex(day_seed, "#ffffff", 0.16 if is_light_theme else 0.28)
    night = mix_hex(bg, night_seed, 0.42 if is_light_theme else 0.34)
    red = pick_theme_color(theme, ["color1"], "#ef4444")

    return {
        "bg": bg,
        "fg": fg,
        "accent": accent,
        "cursor": cursor,
        "dim": dim,
        "surface": surface,
        "surface2": surface2,
        "day": day,
        "night": night,
        "red": red,
        "daylight_contrast": 1.45 if is_light_theme else 1.6,
        "daylight_gamma": 1.1 if is_light_theme else 1.35,
    }


TC = load_theme_colors()
THEME = build_semantic_theme(TC)

# Map theme colors to semantic roles
BG       = THEME["bg"]
FG       = THEME["fg"]
ACCENT   = THEME["accent"]
CURSOR   = THEME["cursor"]
DIM      = THEME["dim"]
SURFACE  = THEME["surface"]
SURFACE2 = THEME["surface2"]

# Status colors derived from active Omarchy palette.
DAY   = THEME["day"]
NIGHT = THEME["night"]
RED   = THEME["red"]

DAY_RGB = hex_to_rgb(DAY)
NIGHT_RGB = hex_to_rgb(NIGHT)
DAYLIGHT_CONTRAST = THEME["daylight_contrast"]
DAYLIGHT_GAMMA = THEME["daylight_gamma"]


# ── Helpers ──────────────────────────────────────────────────────────

def get_local_tz():
    """Get IANA timezone name for the local system."""
    try:
        result = subprocess.run(
            ["timedatectl", "show", "-p", "Timezone", "--value"],
            capture_output=True, text=True, timeout=2,
        )
        tz = result.stdout.strip()
        if tz:
            return tz
    except Exception:
        pass
    tz = os.environ.get("TZ")
    if tz:
        return tz
    try:
        return os.path.realpath("/etc/localtime").split("zoneinfo/")[1]
    except Exception:
        return "UTC"


LOCAL_TZ = get_local_tz()


def contrast_mix(mix):
    """Boost contrast around midday/midnight for clearer separation."""
    mix = (mix - 0.5) * DAYLIGHT_CONTRAST + 0.5
    mix = max(0.0, min(1.0, mix))
    mix = pow(mix, DAYLIGHT_GAMMA)
    return max(0.0, min(1.0, mix))


def daylight_mix(hour):
    """Return day/night mix (0..1) based on hour of day."""
    angle = (hour - 12) / 12 * math.pi
    mix = (math.cos(angle) + 1) / 2
    return contrast_mix(mix)


def daylight_rgb(hour):
    """Return blended RGB for day/night based on hour."""
    return blend_rgb(NIGHT_RGB, DAY_RGB, daylight_mix(hour))


def daylight_hex(hour):
    """Return blended hex color for day/night based on hour."""
    return rgb_to_hex(daylight_rgb(hour))


def get_offset_str(remote_tz):
    """Return human-readable offset string like '+9h' or 'Local'."""
    now = datetime.now()
    local_off = now.astimezone(ZoneInfo(LOCAL_TZ)).utcoffset().total_seconds()
    remote_off = now.astimezone(ZoneInfo(remote_tz)).utcoffset().total_seconds()
    diff_secs = remote_off - local_off
    diff_h = int(diff_secs / 3600)
    diff_m = int((abs(diff_secs) % 3600) / 60)
    if diff_h == 0 and diff_m == 0:
        return "Local"
    if diff_m == 0:
        return f"{diff_h:+d}h"
    sign = "+" if diff_secs >= 0 else "-"
    return f"{sign}{abs(diff_h)}h{diff_m:02d}m"


def get_gmt_label(remote_tz):
    """Return timezone label like 'UTC' or 'GMT +10'."""
    now = datetime.now(ZoneInfo(remote_tz))
    off = now.utcoffset()
    if off is None:
        return "UTC"

    total_secs = int(off.total_seconds())
    if total_secs == 0:
        return "UTC"

    sign = "+" if total_secs > 0 else "-"
    abs_secs = abs(total_secs)
    hours = abs_secs // 3600
    minutes = (abs_secs % 3600) // 60
    if minutes:
        return f"GMT {sign}{hours}:{minutes:02d}"
    return f"GMT {sign}{hours}"


def get_tz_name_label(remote_tz):
    """Return timezone abbreviation label like 'CET' or 'AEST'."""
    now = datetime.now(ZoneInfo(remote_tz))
    name = now.tzname()
    if name:
        return name
    return get_gmt_label(remote_tz)


def format_offset_label(remote_tz):
    """Format row subtitle with local difference and timezone name."""
    return f"{get_offset_str(remote_tz)} · ({get_tz_name_label(remote_tz)})"


def format_slider_label(hours_offset):
    """Format the slider offset label showing local time at offset + relative."""
    local_now = datetime.now(ZoneInfo(LOCAL_TZ))
    target_time = local_now + timedelta(hours=hours_offset)
    time_str = target_time.strftime("%H:%M")
    total_minutes = int(round(hours_offset * 60))
    if total_minutes == 0:
        return f"{time_str} · Now"

    sign = "+" if total_minutes > 0 else "-"
    abs_minutes = abs(total_minutes)
    hours, minutes = divmod(abs_minutes, 60)

    if hours and minutes:
        rel = f"{sign}{hours}h{minutes:02d}m"
    elif hours:
        rel = f"{sign}{hours}h"
    else:
        rel = f"{sign}{minutes}m"
    return f"{time_str} · {rel} from now"


# ── CSS (templated with theme colors) ────────────────────────────────

CSS = f"""
window {{
  background: transparent;
}}

.popup-container {{
  background: {BG};
  border-radius: 16px;
  border: 1px solid alpha({SURFACE2}, 0.5);
  padding: 20px 28px 18px 28px;
  margin: 8px;
  min-width: 400px;
}}

.header-label {{
  font-size: 12px;
  font-weight: 600;
  color: alpha({DIM}, 0.95);
  letter-spacing: 1px;
  margin-bottom: 10px;
}}

/* ── Search box ── */

.search-entry {{
  font-size: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: alpha({SURFACE}, 0.8);
  color: {FG};
  border: 1px solid alpha({SURFACE2}, 0.5);
  margin-bottom: 8px;
  caret-color: {ACCENT};
}}

.search-entry:focus {{
  border-color: alpha({ACCENT}, 0.8);
  background: alpha({SURFACE}, 1.0);
}}

.search-dropdown {{
  background: alpha({BG}, 0.98);
  border: 1px solid alpha({SURFACE2}, 0.6);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 8px;
}}

.search-dropdown row {{
  border-radius: 8px;
}}

.search-result-row {{
  border-radius: 8px;
  transition: background 150ms ease;
}}

.search-result-row:hover,
.search-result-row:selected {{
  background: alpha({SURFACE2}, 0.45);
}}

.search-result {{
  padding: 7px 10px;
}}

.search-result-row:focus-visible {{
  background: alpha({ACCENT}, 0.2);
}}

.search-result-flag {{
  font-size: 15px;
  margin-right: 8px;
}}

.search-result-city {{
  font-size: 14px;
  font-weight: 500;
  color: {FG};
}}

.search-result-tz {{
  font-size: 11px;
  color: alpha({DIM}, 0.95);
  margin-left: 6px;
}}

/* ── City rows ── */

.city-row {{
  padding: 9px 6px;
  border-radius: 12px;
  transition: background 200ms ease;
}}

.city-row:hover {{
  background: alpha({SURFACE}, 0.7);
}}

.city-flag {{
  font-size: 18px;
  margin-right: 12px;
}}

.city-name {{
  font-size: 15px;
  font-weight: 700;
  color: {FG};
}}

.city-offset {{
  font-size: 12px;
  color: alpha({DIM}, 0.95);
}}

.city-date {{
  font-size: 11px;
  color: alpha({DIM}, 0.95);
  margin-right: 8px;
}}

.city-time {{
  font-size: 22px;
  font-weight: 700;
  color: {CURSOR};
  font-family: 'JetBrainsMono Nerd Font';
}}

.status-dot {{
  font-size: 11px;
  margin-left: 12px;
  color: {DAY};
}}

.remove-btn {{
  font-size: 13px;
  padding: 2px 6px;
  min-height: 0;
  min-width: 0;
  margin-left: 10px;
  border-radius: 7px;
  border: 1px solid alpha({SURFACE2}, 0.35);
  background: alpha({SURFACE2}, 0.16);
  color: alpha({DIM}, 0.95);
  opacity: 0.78;
  transition: color 200ms ease, background 200ms ease, border-color 200ms ease, opacity 200ms ease;
}}

.remove-btn:hover {{
  color: {RED};
  opacity: 1.0;
  border-color: alpha({RED}, 0.5);
  background: alpha({RED}, 0.14);
}}

.remove-btn:focus-visible {{
  color: {CURSOR};
  opacity: 1.0;
  border-color: alpha({ACCENT}, 0.55);
  background: alpha({ACCENT}, 0.18);
}}

.separator {{
  background: alpha({SURFACE2}, 0.2);
  min-height: 1px;
  margin: 3px 6px;
}}

/* ── Slider section ── */

.slider-section {{
  margin-top: 14px;
}}

.time-travel-card {{
  padding: 10px 10px 8px 10px;
  border-radius: 12px;
  background: alpha({SURFACE}, 0.28);
  border: 1px solid alpha({SURFACE2}, 0.35);
}}

.slider-title {{
  font-size: 10px;
  font-weight: 600;
  color: alpha({DIM}, 0.9);
  letter-spacing: 0.9px;
  margin-bottom: 6px;
}}

.slider-header {{
  margin-bottom: 6px;
}}

.slider-offset-label {{
  font-size: 12px;
  color: {FG};
}}

.slider-offset-label.shifted {{
  color: {ACCENT};
  font-weight: 600;
}}

.now-button {{
  font-size: 11px;
  padding: 3px 11px;
  border-radius: 8px;
  border: 1px solid alpha({SURFACE2}, 0.4);
  background: alpha({SURFACE2}, 0.42);
  color: {FG};
  min-height: 0;
  min-width: 0;
}}

.now-button:hover {{
  background: alpha({SURFACE2}, 0.65);
  border-color: alpha({ACCENT}, 0.4);
  color: {CURSOR};
}}

.now-button:focus-visible {{
  border-color: alpha({ACCENT}, 0.6);
  background: alpha({ACCENT}, 0.2);
  color: {CURSOR};
}}

.time-slider {{
  margin: 0;
}}

.time-slider trough {{
  min-height: 8px;
  border-radius: 4px;
  background: alpha({SURFACE}, 0.8);
}}

.time-slider highlight {{
  background: alpha({ACCENT}, 0.35);
  border-radius: 4px;
}}

.time-slider slider {{
  min-width: 19px;
  min-height: 19px;
  border-radius: 10px;
  background: {CURSOR};
  border: 2px solid alpha({BG}, 0.5);
}}

.time-slider slider:hover {{
  background: {lighten(CURSOR, 0.2)};
}}

.slider-labels {{
  margin-top: 3px;
  margin-bottom: 7px;
}}

.slider-edge-label {{
  font-size: 10px;
  color: alpha({DIM}, 0.95);
}}

/* ── Status strip ── */

.status-strip-container {{
  margin-top: 4px;
  min-height: 10px;
  border-radius: 5px;
}}

/* ── Legend ── */

.legend-box {{
  margin-top: 8px;
  padding: 0 4px;
}}

.legend-hint {{
  font-size: 10px;
  color: alpha({DIM}, 0.88);
}}
"""

# ── Status strip drawing ─────────────────────────────────────────────


class StatusStrip(Gtk.DrawingArea):
    """A thin colored bar showing 24h of day/night gradient for all cities."""

    def __init__(self, tz_list):
        super().__init__()
        self.tz_list = list(tz_list)
        self.offset_hours = 0.0
        self.set_content_width(380)
        self.set_content_height(8)
        self.add_css_class("status-strip-container")
        self.set_draw_func(self._draw)

    def update_timezones(self, tz_list):
        self.tz_list = list(tz_list)
        self.queue_draw()

    def set_offset(self, hours):
        self.offset_hours = hours
        self.queue_draw()

    def _get_average_daylight(self, hour_offset):
        """Get average day/night mix across all cities for a given hour offset."""
        if not self.tz_list:
            return 0.5
        total = 0.0
        for tz in self.tz_list:
            now = datetime.now(ZoneInfo(tz)) + timedelta(hours=self.offset_hours)
            t = now + timedelta(hours=hour_offset)
            total += daylight_mix(t.hour)
        return total / len(self.tz_list)

    def _draw(self, area, cr, width, height):
        segments = 48
        seg_w = width / segments
        radius = 4

        # Clip to rounded rect
        cr.new_sub_path()
        cr.arc(radius, radius, radius, math.pi, 1.5 * math.pi)
        cr.arc(width - radius, radius, radius, 1.5 * math.pi, 0)
        cr.arc(width - radius, height - radius, radius, 0, 0.5 * math.pi)
        cr.arc(radius, height - radius, radius, 0.5 * math.pi, math.pi)
        cr.close_path()
        cr.clip()

        for i in range(segments):
            hour_offset = -24 + i
            mix = contrast_mix(self._get_average_daylight(hour_offset))
            r, g, b = blend_rgb(NIGHT_RGB, DAY_RGB, mix)
            cr.set_source_rgb(r, g, b)
            cr.rectangle(i * seg_w, 0, seg_w + 1, height)
            cr.fill()

        # "Now" marker line at center
        cx = width / 2
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.set_line_width(1.5)
        cr.move_to(cx, 0)
        cr.line_to(cx, height)
        cr.stroke()


# ── Widgets ──────────────────────────────────────────────────────────

class CityRow(Gtk.Box):
    def __init__(self, flag, city, tz, on_remove=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_css_class("city-row")
        self.tz = tz
        self.flag = flag
        self.city = city
        self._on_remove = on_remove

        # Flag
        flag_label = Gtk.Label(label=flag)
        flag_label.add_css_class("city-flag")
        self.append(flag_label)

        # City name + offset column
        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name_box.set_valign(Gtk.Align.CENTER)
        name_box.set_hexpand(True)

        self.name_label = Gtk.Label(label=city, xalign=0)
        self.name_label.add_css_class("city-name")
        name_box.append(self.name_label)

        self.offset_label = Gtk.Label(label=format_offset_label(tz), xalign=0)
        self.offset_label.add_css_class("city-offset")
        self.offset_label.set_tooltip_text(tz)
        name_box.append(self.offset_label)

        self.append(name_box)

        # Date label (shown when day differs from local)
        self.date_label = Gtk.Label(label="")
        self.date_label.add_css_class("city-date")
        self.date_label.set_valign(Gtk.Align.CENTER)
        self.append(self.date_label)

        # Time
        self.time_label = Gtk.Label(label="--:--")
        self.time_label.add_css_class("city-time")
        self.time_label.set_valign(Gtk.Align.CENTER)
        self.append(self.time_label)

        # Status dot
        self.dot = Gtk.Label(label="●")
        self.dot.add_css_class("status-dot")
        self.dot.set_valign(Gtk.Align.CENTER)
        self.append(self.dot)

        # Remove button
        remove_btn = Gtk.Button(label="×")
        remove_btn.add_css_class("remove-btn")
        remove_btn.set_valign(Gtk.Align.CENTER)
        remove_btn.connect("clicked", self._remove_clicked)
        self.append(remove_btn)

        self.update(0.0)

    def _remove_clicked(self, btn):
        if self._on_remove:
            self._on_remove(self)

    def update(self, slider_offset_hours=0.0):
        now = datetime.now(ZoneInfo(self.tz)) + timedelta(hours=slider_offset_hours)
        local_now = datetime.now(ZoneInfo(LOCAL_TZ)) + timedelta(hours=slider_offset_hours)

        self.time_label.set_label(now.strftime("%H:%M"))

        # Show date if different day from local
        if now.date() != local_now.date():
            self.date_label.set_label(now.strftime("%a, %b %-d"))
            self.date_label.set_visible(True)
        else:
            self.date_label.set_visible(False)

        color = daylight_hex(now.hour)
        period = "Day" if daylight_mix(now.hour) >= 0.5 else "Night"
        self.dot.set_markup(f"<span foreground=\"{color}\">●</span>")
        self.dot.set_tooltip_text(period)
        self.offset_label.set_label(format_offset_label(self.tz))


class CitySearchBox(Gtk.Box):
    """Search entry with dropdown results for adding cities."""

    def __init__(self, on_city_selected):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_city_selected = on_city_selected
        self._result_count = 0
        self._row_data = {}

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Search cities...")
        self.entry.add_css_class("search-entry")
        self.entry.connect("changed", self._on_text_changed)
        self.entry.connect("activate", self._on_entry_activate)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_entry_key_pressed)
        self.entry.add_controller(key_controller)
        self.append(self.entry)

        # Dropdown container
        self.dropdown = Gtk.ListBox()
        self.dropdown.add_css_class("search-dropdown")
        self.dropdown.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.dropdown.set_activate_on_single_click(True)
        self.dropdown.connect("row-activated", self._on_row_activated)
        self.dropdown.set_visible(False)
        self.append(self.dropdown)

    def _on_text_changed(self, entry):
        query = entry.get_text().strip()
        self._result_count = 0
        self._row_data.clear()

        # Clear old results
        while True:
            child = self.dropdown.get_first_child()
            if child is None:
                break
            self.dropdown.remove(child)

        if len(query) < 2:
            self._hide_dropdown()
            return

        results = search_timezones(query)
        if not results:
            self._hide_dropdown()
            return

        for flag, city, tz in results:
            row = Gtk.ListBoxRow()
            row.add_css_class("search-result-row")
            self._row_data[row] = (flag, city, tz)

            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            content.add_css_class("search-result")

            flag_lbl = Gtk.Label(label=flag)
            flag_lbl.add_css_class("search-result-flag")
            content.append(flag_lbl)

            city_lbl = Gtk.Label(label=city, xalign=0)
            city_lbl.add_css_class("search-result-city")
            city_lbl.set_hexpand(True)
            content.append(city_lbl)

            tz_lbl = Gtk.Label(label=tz, xalign=1)
            tz_lbl.add_css_class("search-result-tz")
            content.append(tz_lbl)

            row.set_child(content)
            self.dropdown.append(row)
            self._result_count += 1

        if self._result_count:
            self.dropdown.set_visible(True)
            self.dropdown.select_row(self.dropdown.get_row_at_index(0))

    def _hide_dropdown(self):
        self.dropdown.set_visible(False)
        self.dropdown.unselect_all()
        # Force the window to recalculate its size so it shrinks back
        win = self.get_root()
        if win:
            win.set_default_size(-1, -1)
            win.queue_resize()

    def _select_result_row(self, row):
        if row is None:
            return
        city_data = self._row_data.get(row)
        if city_data is None:
            return
        flag, city, tz = city_data
        self.entry.set_text("")
        self._hide_dropdown()
        self._on_city_selected(flag, city, tz)

    def _on_row_activated(self, _listbox, row):
        self._select_result_row(row)

    def _on_entry_activate(self, _entry):
        if not self.dropdown.get_visible():
            return
        row = self.dropdown.get_selected_row() or self.dropdown.get_row_at_index(0)
        self._select_result_row(row)

    def _on_entry_key_pressed(self, _controller, keyval, _keycode, _state):
        if not self.dropdown.get_visible() or self._result_count == 0:
            return False

        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            current = self.dropdown.get_selected_row()
            current_idx = current.get_index() if current else -1
            delta = 1 if keyval == Gdk.KEY_Down else -1
            next_idx = max(0, min(self._result_count - 1, current_idx + delta))
            row = self.dropdown.get_row_at_index(next_idx)
            if row:
                self.dropdown.select_row(row)
                row.grab_focus()
            return True

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._on_entry_activate(self.entry)
            return True

        if keyval == Gdk.KEY_Escape:
            self._hide_dropdown()
            return True

        return False


class TimezonesPopup(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.omarchy.timezones")
        self.win = None
        self.rows = []
        self.cities = []
        self.slider_offset = 0.0
        self.offset_label = None
        self.status_strip = None
        self.slider = None
        self.city_container = None

    def do_activate(self):
        if self.win is not None:
            self.win.present()
            return

        # Load persisted cities
        self.cities = load_cities()

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Window
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_decorated(False)

        # Layer shell setup
        LayerShell.init_for_window(self.win)
        LayerShell.set_layer(self.win, LayerShell.Layer.OVERLAY)
        LayerShell.set_anchor(self.win, LayerShell.Edge.TOP, True)
        LayerShell.set_margin(self.win, LayerShell.Edge.TOP, 32)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.ON_DEMAND)

        # Container
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        container.add_css_class("popup-container")

        # Header
        header = Gtk.Label(label="TIMEZONES", xalign=0)
        header.add_css_class("header-label")
        container.append(header)

        # Search box
        self.search_box = CitySearchBox(self._on_city_added)
        container.append(self.search_box)

        # Scrolled window for city rows
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(350)
        scrolled.set_propagate_natural_height(True)

        self.city_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.city_container)
        container.append(scrolled)

        # Build city rows
        self._rebuild_city_rows()

        # ── Slider section ──
        slider_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        slider_section.add_css_class("slider-section")
        slider_section.add_css_class("time-travel-card")

        slider_title = Gtk.Label(label="TIME TRAVEL", xalign=0)
        slider_title.add_css_class("slider-title")
        slider_section.append(slider_title)

        # Offset label + Now button row
        slider_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        slider_header.add_css_class("slider-header")

        self.offset_label = Gtk.Label(label=format_slider_label(0), xalign=0)
        self.offset_label.add_css_class("slider-offset-label")
        self.offset_label.set_hexpand(True)
        slider_header.append(self.offset_label)

        now_btn = Gtk.Button(label="Now")
        now_btn.add_css_class("now-button")
        now_btn.connect("clicked", self._on_now_clicked)
        slider_header.append(now_btn)

        slider_section.append(slider_header)

        # Slider
        adjustment = Gtk.Adjustment(
            value=0, lower=-24, upper=24, step_increment=0.5,
            page_increment=1, page_size=0,
        )
        self.slider = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=adjustment,
        )
        self.slider.set_draw_value(False)
        self.slider.add_css_class("time-slider")
        self.slider.connect("value-changed", self._on_slider_changed)
        slider_section.append(self.slider)

        # -24h / +24h labels
        slider_labels = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        slider_labels.add_css_class("slider-labels")
        lbl_left = Gtk.Label(label="-24h", xalign=0)
        lbl_left.add_css_class("slider-edge-label")
        lbl_left.set_hexpand(True)
        slider_labels.append(lbl_left)
        lbl_right = Gtk.Label(label="+24h", xalign=1)
        lbl_right.add_css_class("slider-edge-label")
        slider_labels.append(lbl_right)
        slider_section.append(slider_labels)

        # Status strip (colored bar) — combined for all cities
        tz_list = [tz for _, _, tz in self.cities]
        self.status_strip = StatusStrip(tz_list)
        slider_section.append(self.status_strip)

        container.append(slider_section)

        # Legend
        legend = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        legend.add_css_class("legend-box")
        legend.set_halign(Gtk.Align.CENTER)
        legend_hint = Gtk.Label(label="☀️ brighter strip = day   •   🌑 darker strip = night")
        legend_hint.add_css_class("legend-hint")
        legend.append(legend_hint)
        container.append(legend)

        self.win.set_child(container)

        # Close on Escape
        esc_controller = Gtk.EventControllerKey()
        esc_controller.connect("key-pressed", self._on_key)
        self.win.add_controller(esc_controller)

        # Periodic update
        GLib.timeout_add_seconds(UPDATE_INTERVAL_SECONDS, self._tick)

        self.win.present()

    def _rebuild_city_rows(self):
        """Rebuild all city rows and separators from self.cities."""
        # Clear container
        while True:
            child = self.city_container.get_first_child()
            if child is None:
                break
            self.city_container.remove(child)

        self.rows = []
        for i, (flag, city, tz) in enumerate(self.cities):
            if i > 0:
                sep = Gtk.Separator()
                sep.add_css_class("separator")
                self.city_container.append(sep)
            row = CityRow(flag, city, tz, on_remove=self._on_city_removed)
            row.update(self.slider_offset)
            self.rows.append(row)
            self.city_container.append(row)

    def _on_city_added(self, flag, city, tz):
        """Called when user selects a city from search results."""
        # Avoid duplicates
        for _, _, existing_tz in self.cities:
            if existing_tz == tz:
                return
        self.cities.append((flag, city, tz))
        save_cities(self.cities)
        self._rebuild_city_rows()
        if self.status_strip:
            self.status_strip.update_timezones([t for _, _, t in self.cities])

    def _on_city_removed(self, row):
        """Called when user clicks × on a city row."""
        self.cities = [(f, c, t) for f, c, t in self.cities if t != row.tz]
        save_cities(self.cities)
        self._rebuild_city_rows()
        if self.status_strip:
            self.status_strip.update_timezones([t for _, _, t in self.cities])

    def _on_slider_changed(self, slider):
        val = slider.get_value()
        # Snap to 0 when close
        if abs(val) < 0.3:
            val = 0.0
        self.slider_offset = val
        self.offset_label.set_label(format_slider_label(val))
        if val != 0:
            self.offset_label.add_css_class("shifted")
        else:
            self.offset_label.remove_css_class("shifted")
        for row in self.rows:
            row.update(val)
        self.status_strip.set_offset(val)

    def _on_now_clicked(self, btn):
        self.slider.set_value(0)

    def _on_key(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.quit()
            return True
        return False

    def _tick(self):
        for row in self.rows:
            row.update(self.slider_offset)
        if self.status_strip:
            self.status_strip.queue_draw()
        return True


def main():
    pidfile = os.path.join(
        os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "omarchy-timezones.pid"
    )

    # Toggle: if already running, kill the existing instance and exit
    if os.path.exists(pidfile):
        try:
            with open(pidfile, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            os.unlink(pidfile)
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            try:
                os.unlink(pidfile)
            except FileNotFoundError:
                pass

    # Write our PID
    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))

    def cleanup(*_):
        try:
            os.unlink(pidfile)
        except FileNotFoundError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    app = TimezonesPopup()
    try:
        app.run([])
    finally:
        try:
            os.unlink(pidfile)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
