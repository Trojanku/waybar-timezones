# Omarchy Waybar Timezones

A GTK4 Layer Shell popup widget for Waybar that shows world clocks across multiple timezones. Built for [omarchy](https://github.com/nichochar/omarchy).

## Features

- Search and add cities from a database of 80+ major cities (plus full IANA timezone fallback)
- Remove cities with one click
- Persistent city list across sessions
- Time slider to preview times up to 24 hours ahead or behind
- Day/night gradient strip showing overall daylight across your cities
- Day/night theming with a smooth gradient based on local hours
- Automatic theme integration with omarchy color scheme (`~/.config/omarchy/current/theme/colors.toml`)

## Prerequisites

- [omarchy](https://github.com/nichochar/omarchy) installed and configured
- Python 3.9+
- GTK 4
- [gtk4-layer-shell](https://github.com/wmww/gtk4-layer-shell)

On Arch Linux (omarchy's primary target):

```bash
sudo pacman -S python gtk4 gtk4-layer-shell
```

## Installation

1. Clone or copy this repository:

```bash
git clone https://github.com/yourusername/waybar-timezones.git
cd waybar-timezones
```

2. Make the launcher script executable:

```bash
chmod +x omarchy-timezones
```

3. Add the custom module to your Waybar config (`~/.config/waybar/config.jsonc`):

```jsonc
"custom/timezones": {
  "format": "󰔎",
  "tooltip-format": "Omarchy Waybar Timezones",
  "on-click": "/path/to/waybar-timezones/omarchy-timezones",
  "interval": "once"
}
```

4. Include `"custom/timezones"` in one of your bar's module lists (e.g. `modules-right`):

```jsonc
"modules-right": ["custom/timezones", "clock"]
```

5. Optionally style the icon in `~/.config/waybar/style.css`:

```css
#custom-timezones {
  margin-left: 7px;
  font-size: 15px;
  opacity: 0.6;
  transition: opacity 200ms ease;
}

#custom-timezones:hover {
  opacity: 1.0;
}
```

6. Reload Waybar:

```bash
killall -SIGUSR2 waybar
```

## Usage

- **Open/close** — Click the waybar icon (runs as a toggle; clicking again kills the popup)
- **Search** — Type 2+ characters in the search box to find cities
- **Add** — Click a search result to add it
- **Remove** — Click the `×` button on any city row
- **Time travel** — Drag the slider to preview times up to ±24 hours
- **Reset** — Click `⟳ Now` to snap back to current time
- **Close** — Press `Escape`

## Configuration

City selections are saved to `~/.config/omarchy-timezones/cities.json` and persist across sessions. The default cities are San Francisco, Warsaw, and Brisbane.

Colors are pulled automatically from your active omarchy theme at `~/.config/omarchy/current/theme/colors.toml`.

## License

MIT
