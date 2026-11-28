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
r client.setting.interface.tabs.color value=active_tabs # colour icons only in the current tab
r client.setting.interface.tabs.count value=1 # one icon per tab keeps the sidebar tidy

# Focus, like Herdr: blue edge on the focused pane; unfocused panes dim their text
# but keep the Mocha background (fading the surface turned them grey).
r client.setting.interface.active_panes.active_border value=true
r client.setting.interface.active_panes.active_border_color value=blue
r client.setting.interface.active_panes.active_border_animation value=fade
r client.setting.interface.active_panes.inactive_window value=true # dim windows that aren't in front
r client.setting.interface.splits_focus.autobalance value=true # equal-size panes on split/close
r client.setting.interface.splits_focus.focus_follows_mouse value=false
r client.setting.interface.animation.style value=natural
r client.setting.interface.active_panes.fade value=content
r client.setting.interface.panes.density value=comfortable
r client.setting.interface.panes.headers value=on_hover
r client.setting.interface.window.sidebar_text_size value=14
r client.setting.interface.pane_padding.color value=automatic # nvim's background fills the padding
r client.setting.interface.pane_padding.program_background value=true # and the pane header
# Glass (Rex's blurred see-through look) needs macOS 26; skipped on older macOS.
r client.setting.interface.appearance.style value=glass
r client.setting.interface.appearance.glass value=true

# Sidebar on the left, like Herdr's Spaces panel: sessions, each with its tabs.
# Agents: status dots on those tabs, and Cmd-. swaps the list for Activity, grouped by session.
r client.setting.interface.toolbar.layout value=left
r client.setting.interface.toolbar.auto_hide_toolbar value=on_hover # with the sidebar hidden, no floating tab card in the top-left
r client.setting.notifications.activity.tab_activity value=true
r client.setting.notifications.activity.system_notifications value=true # macOS notification when a background agent finishes, blocks or fails
r client.setting.notifications.activity.sounds value=true # chime when an agent blocks, fails or finishes
r client.setting.notifications.activity.idle_in_activity value=true # Activity lists idle agents too
r client.setting.notifications.overview.position value=top_right
r client.setting.notifications.macos.terminal_notifications value=true # programs may send their own notifications
r client.sidebar.activity.by_session

# Font: JetBrains Mono 18, no ligatures
r client.setting.terminal.typography.font value="JetBrainsMono Nerd Font Mono"
r client.setting.terminal.typography.size value=18
r client.setting.terminal.advanced_fonts.ligatures value=false
r client.setting.terminal.advanced_fonts.bold_italic value=both
r client.setting.terminal.advanced_fonts.smoothing value=true
r client.setting.terminal.colors.contrast value=true # fix unreadable low-contrast text
r client.setting.terminal.colors.palette value=true # snap true-colour output to the theme
r client.setting.terminal.colors.display_p3 value=true # more vivid colours
r client.setting.terminal.cursor.style value=block
r client.setting.terminal.cursor.force value=false # nvim can still switch to a bar in insert mode
r client.setting.terminal.cursor.blink value=off
r client.setting.terminal.cursor.shaders value=true
r client.setting.terminal.cursor.shader value=blaze_tapered
r client.setting.terminal.scrolling.smooth value=true
r client.setting.terminal.resizing.smooth value=true
r client.setting.terminal.selection.copy_on_select value=true
r client.setting.terminal.selection.play_animation_on_copy value=true
r client.setting.terminal.selection.corners value=true
r client.setting.terminal.links.custom_schemes value=ask # confirm before a link launches another app
r client.setting.terminal.path_browser.recent_paths value=true
r client.setting.terminal.titles.prefer_generated value=true # tabs named after the program
r client.setting.developer.experimental.new_quick_switcher value=true # one list of sessions, panes, processes

# Keyboard: Option as Alt, and show what can follow the ctrl+s prefix
r client.setting.terminal.keyboard.option value=sends_alt
r client.setting.terminal.keyboard.sequence_hints value=true
