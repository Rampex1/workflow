# config

My terminal setup: Ghostty → tmux → Neovim (LazyVim), all on Catppuccin Mocha.

| Folder     | Goes to                      |
| ---------- | ---------------------------- |
| `ghostty/` | `~/.config/ghostty/`         |
| `tmux/`    | `~/.config/tmux/`            |
| `nvim/`    | `~/.config/nvim/`            |

## Install

```sh
# from this folder
cp -R ghostty tmux nvim ~/.config/
echo 'source-file ~/.config/tmux/tmux.conf' > ~/.tmux.conf   # only needed for tmux < 3.1

brew install neovim tmux ripgrep fd lazygit
brew install --cask ghostty font-jetbrains-mono
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

Then start tmux and press `C-s I` to install tmux plugins. Open `nvim` once and lazy.nvim installs the plugins pinned in `lazy-lock.json`.

To pull changes back from this machine: `rsync -a --delete --exclude .DS_Store ~/.config/nvim/ nvim/` (and `cp` the ghostty/tmux files).

## Keys

**tmux** (prefix `C-s`)
- `C-h/j/k/l`: move between tmux panes *and* Neovim splits (vim-tmux-navigator)
- `"` / `%`: split, keeping the current directory
- `r`: reload config

**Neovim** (leader `Space`, on top of [LazyVim defaults](https://www.lazyvim.org/keymaps))
- `<leader>h`: clear search highlight
- `<leader>fg`: live grep
- `<leader>gd`: go to definition (replaces LazyVim's git diff)
- `<leader>uL`: toggle LSP for the buffer

Extras (`:LazyExtras`): mini-files, json, typescript, mini-animate. Options: no relative numbers, no swapfile, root = cwd, no auto comment continuation, no signature-help popup.

**Ghostty**: reload config with `cmd+shift+,`.
