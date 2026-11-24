# config

My terminal setup: Herdr (desktop app) → Neovim (LazyVim), all on Catppuccin Mocha. Ghostty is the plain terminal; tmux is kept for reference but no longer auto-starts.

| Folder       | Goes to                  |
| ------------ | ------------------------ |
| `herdr/`     | `~/.config/herdr-app/`   |
| `nvim/`      | `~/.config/nvim/`        |
| `ghostty/`   | `~/.config/ghostty/`     |
| `tmux/`      | `~/.config/tmux/` (legacy) |

## Install

```sh
xcode-select --install   # git + C compiler (treesitter)
brew install neovim node ripgrep fd lazygit
brew install --cask ghostty
# Herdr app: https://herdr.dev

# from this folder
cp -R ghostty nvim ~/.config/
rsync -a herdr/ ~/.config/herdr-app/   # merge: the app keeps its own shipped files there
```

Open `nvim` once and lazy.nvim installs the plugins pinned in `lazy-lock.json`. In the Herdr app, pick the `ghostty` layout in Settings → Layout if it isn't already shown.

To pull changes back from this machine:

```sh
rsync -a --delete --exclude .DS_Store ~/.config/nvim/ nvim/
cd ~/.config/herdr-app && cp settings.json keys.json ~/Documents/GitHub/workflow/config/herdr/
# plus layouts/ghostty.json, themes/catppuccin-mocha.json, mods/{spaces,agents,pane}-nav/{main.js,mod.json}
```

## Herdr app

- `settings.json`: Catppuccin Mocha theme, JetBrains Mono 18, Option as Alt (moved over from Ghostty).
- `layouts/ghostty.json`: copy of the shipped `main` layout with a blurred, 90% opaque background, the sidebar using the `*-nav` mods, and a zero-height `pane-nav` block.
- `mods/spaces-nav`, `mods/agents-nav`: copies of the shipped Spaces and Agents panels that can take the keyboard. They're cloned from Herdr 0.1.18 and won't update with the app.
- `mods/pane-nav`: vim-tmux-navigator for Herdr. Ctrl-h/j/k/l go to vim/nvim/fzf when one is in front, otherwise move to the next pane or panel.

## Neovim setup

Extras (`:LazyExtras`): mini-files, json, typescript, mini-animate. Options: no relative numbers, no swapfile, root = cwd, no auto comment continuation, no signature-help popup.

`lua/config/keymaps.lua`: Ctrl-h/j/k/l move between splits, and past the last split ask Herdr to move to the next pane (only inside Herdr, detected by `HC_TERMINAL_ID`).

## Keys

**Herdr app** (prefix `C-s`, tmux-style: press Ctrl-s, release, then the key)
- `C-h/j/k/l`: move between nvim splits, Herdr panes, and the Spaces/Agents panels
- In Spaces: `j/k` switch space (focus stays in the panel), `Enter`/`l`/`Esc` back to the terminal
- In Agents: `j/k` move the highlight, `Enter` jump to that agent, `l`/`Esc` back to the terminal
- `c` new tab, `h`/`l` previous/next tab, `1`–`9` go to tab
- `"` split down, `%` split right, arrows move between panes, `x` close pane, `&` close tab, `z` zoom
- `,` rename tab, `$` rename space, `(`/`)` previous/next space, `w`/`s` picker
- App defaults still work: `Cmd-T` new tab, `Cmd-1..9` tabs, `Ctrl-1..9` spaces, `Cmd-]`/`Cmd-[` agents, `Cmd-P` picker

**Neovim**: stock [LazyVim keys](https://www.lazyvim.org/keymaps) (leader `Space`), plus the Ctrl-h/j/k/l navigation above

**Ghostty**: reload config with `cmd+shift+,`.
