# config

My terminal setup: Rex (desktop app) → Neovim (LazyVim), all on Catppuccin Mocha. Ghostty is the plain terminal. Herdr and tmux configs are kept for reference; neither auto-starts.

Migrating to a new machine or tool? Give [`SETUP-PROMPT.md`](SETUP-PROMPT.md) to an AI assistant: it describes the whole setup and the reasons behind it.

| Folder       | Goes to                  |
| ------------ | ------------------------ |
| `rex/`       | `~/.config/rex/` (`init.lua`; `settings.sh` is run, not copied) |
| `herdr/`     | `~/.config/herdr-app/` (legacy) |
| `nvim/`      | `~/.config/nvim/`        |
| `ghostty/`   | `~/.config/ghostty/`     |
| `tmux/`      | `~/.config/tmux/` (legacy) |

## Install

```sh
xcode-select --install   # git + C compiler (treesitter)
brew install neovim node ripgrep fd lazygit
brew install --cask ghostty
# Rex app: https://www.superlogical.com/rex/docs/installation

# from this folder
cp -R ghostty nvim ~/.config/
mkdir -p ~/.config/rex && cp rex/init.lua ~/.config/rex/ && rex config reload
# Rex > Settings > General > Remote Control on, then:
rex/settings.sh   # theme, font, glass, Option as Alt
```

Open `nvim` once and lazy.nvim installs the plugins pinned in `lazy-lock.json`.

To pull changes back from this machine:

```sh
rsync -a --delete --exclude .DS_Store ~/.config/nvim/ nvim/
cp ~/.config/rex/init.lua rex/
```

## Rex app

- `init.lua`: all key bindings (below). Herdr spaces are Rex sessions; tabs and panes are the same.
- `settings.sh`: the settings Rex keeps in the app rather than a file: official Catppuccin Mocha (imported from `Catppuccin Mocha Official`, the same palette as Herdr's theme), dark, sidebar and window tinted with the theme, blue edge on the focused pane, unfocused panes dimmed text only, Glass style with glass panes (the blurred see-through look; needs macOS 26, skipped before that), JetBrainsMono Nerd Font Mono 18, ligatures off, Option sends Alt, key sequence hints on, and the sidebar on the left (sessions and their tabs, agent status on each tab; `Cmd-.` shows Activity grouped by session).
- Ctrl-h/j/k/l is a Lua function in `init.lua`: it asks Rex what's in front of the focused pane and lets vim/nvim/fzf have the key, otherwise moves pane.

## Herdr app (legacy)

- `settings.json`: Catppuccin Mocha theme, JetBrains Mono 18, Option as Alt (moved over from Ghostty).
- `layouts/ghostty.json`: copy of the shipped `main` layout with a blurred, 90% opaque background, the sidebar using the `*-nav` mods, and a zero-height `pane-nav` block.
- `mods/spaces-nav`, `mods/agents-nav`: copies of the shipped Spaces and Agents panels that can take the keyboard. They're cloned from Herdr 0.1.18 and won't update with the app.
- `mods/pane-nav`: vim-tmux-navigator for Herdr. Ctrl-h/j/k/l go to vim/nvim/fzf when one is in front, otherwise move to the next pane or panel.

## Neovim setup

Extras (`:LazyExtras`): mini-files, json, typescript, mini-animate. Options: no relative numbers, no swapfile, root = cwd, no auto comment continuation, no signature-help popup.

`lua/config/keymaps.lua`: Ctrl-h/j/k/l move between splits, and past the last split ask Rex (detected by `REX_BLOCK`) or Herdr (`HC_TERMINAL_ID`) to move to the next pane.

## Keys

**Rex** (prefix `C-s`, tmux-style: press Ctrl-s, release, then the key; `C-s C-s` sends a real Ctrl-s)
- `C-h/j/k/l`: move between nvim splits and Rex panes
- `c` new tab, `h`/`l` previous/next tab, `1`–`9` go to tab
- `"` split down, `%` split right, arrows or `o` move between panes, `x` close pane, `&` close tab, `z` zoom
- `,` rename tab, `$` rename session, `(`/`)` previous/next session, `w` Go to Anything, `s` session picker, `r` reload config
- Kept from Herdr: `Ctrl-1..9` sessions, `F2` rename tab, `Shift-F2` rename session, `Cmd-B` sidebar
- Rex defaults: `Cmd-T` new tab, `Cmd-1..9` tabs, `Cmd-N` new session, `Cmd-K` sessions, `Cmd-P` Go to Anything, `Cmd-D`/`Cmd-Shift-D` split, `Cmd-W` close pane (else tab), `Cmd-.` Activity (agents)

**Neovim**: stock [LazyVim keys](https://www.lazyvim.org/keymaps) (leader `Space`), plus the Ctrl-h/j/k/l navigation above

**Ghostty**: reload config with `cmd+shift+,`.
