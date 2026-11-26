#!/bin/sh
# Rex.app settings that init.lua can't hold (the app keeps them itself).
# Needs Rex > Settings > General > Remote Control turned on. Safe to re-run.
# A setting this Mac's Rex doesn't offer is reported and skipped.
r() { rex do "$@" || echo "skipped: $1" >&2; }

# Look: official Catppuccin Mocha (Ghostty's bundled copy has a rosewater selection
# and lightened bright colours), with the sidebar and window tinted to match.
here=$(cd "$(dirname "$0")" && pwd)
rex do client.theme.change name="Catppuccin Mocha Official" 2>/dev/null ||
  r client.theme.import path="$here/Catppuccin Mocha Official" # importing also selects it
r client.setting.interface.appearance.scheme value=dark
r client.setting.interface.appearance.tint value=true
r client.setting.interface.tabs.shell_icon_theme value=theme_accent

# Focus, like Herdr: blue edge on the focused pane; unfocused panes dim their text
# but keep the Mocha background (fading the surface turned them grey).
r client.setting.interface.active_panes.active_border value=true
r client.setting.interface.active_panes.active_border_color value=blue
r client.setting.interface.active_panes.fade value=content
# Glass (Rex's blurred see-through look) needs macOS 26; skipped on older macOS.
r client.setting.interface.appearance.style value=glass
r client.setting.interface.appearance.glass value=true

# Sidebar on the left, like Herdr's Spaces panel: sessions, each with its tabs.
# Agents: status dots on those tabs, and Cmd-. swaps the list for Activity, grouped by session.
r client.setting.interface.toolbar.layout value=left
r client.setting.interface.toolbar.auto_hide_toolbar value=always_show
r client.setting.notifications.activity.tab_activity value=true
r client.sidebar.activity.by_session

# Font: JetBrains Mono 18, no ligatures
r client.setting.terminal.typography.font value="JetBrainsMono Nerd Font Mono"
r client.setting.terminal.typography.size value=18
r client.setting.terminal.advanced_fonts.ligatures value=false

# Keyboard: Option as Alt, and show what can follow the ctrl+s prefix
r client.setting.terminal.keyboard.option value=sends_alt
r client.setting.terminal.keyboard.sequence_hints value=true
