# config

My terminal setup: Ghostty → tmux → Neovim (LazyVim), all on Catppuccin Mocha.

| Folder     | Goes to              |
| ---------- | -------------------- |
| `ghostty/` | `~/.config/ghostty/` |
| `tmux/`    | `~/.config/tmux/`    |
| `nvim/`    | `~/.config/nvim/`    |

## Install

```sh
xcode-select --install   # git + C compiler (treesitter)
brew install neovim tmux node ripgrep fd lazygit
brew install --cask ghostty
git clone https://github.com/tmux-plugins/tpm ~/.config/tmux/plugins/tpm

# from this folder
cp -R ghostty tmux nvim ~/.config/
```

Then start tmux and press `C-s I` to install tmux plugins. Open `nvim` once and lazy.nvim installs the plugins pinned in `lazy-lock.json`.

To pull changes back from this machine: `rsync -a --delete --exclude .DS_Store ~/.config/nvim/ nvim/` (and `cp` the ghostty/tmux files).

## Neovim setup

Extras (`:LazyExtras`): mini-files, json, typescript, mini-animate. Options: no relative numbers, no swapfile, root = cwd, no auto comment continuation, no signature-help popup.

## Keys

**tmux** (prefix `C-s`)
- `C-h/j/k/l`: move between tmux panes *and* Neovim splits (vim-tmux-navigator)
- `"` / `%`: split, keeping the current directory
- `r`: reload config

**Neovim**: stock [LazyVim keys](https://www.lazyvim.org/keymaps) (leader `Space`)

**Ghostty**: reload config with `cmd+shift+,`.
