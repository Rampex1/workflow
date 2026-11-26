# Terminal setup: instructions for an AI assistant

You are setting up my terminal environment on a new machine, or moving it to a new tool. Read this whole file first. It states what I want and why, so you can rebuild it on whatever tools are current without asking me. The config files next to this file (`rex/`, `nvim/`, `ghostty/`) are the last working implementation; `herdr/` and `tmux/` are the ones before it. Use them directly where the tools are the same, and treat them as a reference where they aren't.

Work on your own: read my existing configs, make the changes, test what you can, and tell me what you couldn't test. Only ask me when a choice genuinely conflicts with something below.

## The stack

- **Workspace manager:** the Rex desktop app (superlogical.com/rex). It holds sessions (one per project), tabs and split panes, and tracks coding agents (Claude Code and others) in its Activity sidebar. It replaced the Herdr app, which replaced tmux. Herdr's "spaces" are Rex sessions.
- **Editor:** Neovim with LazyVim, mostly stock.
- **Plain terminal:** Ghostty, for when I want a bare shell. It must not auto-start anything.
- **Shell:** zsh.
- **Look everywhere:** Catppuccin Mocha, JetBrains Mono at size 18, a slightly see-through (about 90% opaque) blurred background.

If Rex is gone or replaced, carry the behaviour below over to whatever plays its role (Herdr, tmux, zellij, WezTerm and so on).

## Rules

1. **Never nest workspace managers.** Nothing auto-starts tmux or the terminal version of herdr inside a pane. In the past `.zshrc` ran `tmux new -A -s dev` and Ghostty had `command = herdr`; both were removed. A new pane opens a plain zsh.
2. **One prefix key: Ctrl-s**, tmux-style. Press Ctrl-s, let go, press the second key.
3. **Ctrl-h/j/k/l move focus everywhere**, vim-tmux-navigator style (details below). This matters most to me.
4. **Keep shipped files untouched.** Where a tool ships files it overwrites on update (Herdr's layouts and mods), copy them and edit the copy.
5. **Keep my configs in this repo**, under `config/<tool>/`, and update `config/README.md` and this file when the setup changes.
6. **Git:** never add a Claude or AI co-author line to commits or PRs. If I'm on `main`, make a branch before committing. Don't push unless I ask.

## Navigation

### Ctrl-h/j/k/l: one set of keys for everything

These move left, down, up and right. The same key works across these levels, in this order:

1. **Inside Neovim:** move between Neovim splits.
2. **At Neovim's last split in that direction:** move to the neighbouring pane of the workspace manager.
3. **In a pane running anything else** (zsh, Claude Code): move to the neighbouring pane.
4. **From the leftmost pane, Ctrl-h:** move into the sidebar (Spaces and Agents panels).
5. **In the sidebar:** Ctrl-j/k move between the Spaces and Agents panels, and Ctrl-l goes back to the terminal.

Rex's sidebar can't take keyboard focus (as of Rex 0.1.0-preview), so levels 4 and 5 only exist in Herdr. In Rex, use the pickers (`Ctrl-s s`, `Ctrl-s w`) and `Cmd-.` (Activity) instead.

Rex also has no way to stack a Spaces panel over an Agents panel: it has no panel or mod system. The closest match, set by `rex/settings.sh`, is the sidebar on the left listing sessions and their tabs, with agent status shown on each tab, and `Cmd-.` swapping the list for Activity grouped by session.

How it works:
- The workspace manager checks what's running in the focused pane. If it matches vim, nvim or fzf (vim-tmux-navigator's pattern, `(view|l?n?vim?x?|fzf)(diff)?`), the key goes to the program. Otherwise it moves panes.
- Neovim maps Ctrl-h/j/k/l to `wincmd`. When the window didn't change (an edge), it tells the workspace manager to move. In Rex that's `rex api call -s $REX_BLOCK session.focus_direction '{"direction":"left"}'`, used when `REX_BLOCK` is set. In Herdr it's `herdr-app do pane.go '{"direction":"left"}'`, used when `HC_TERMINAL_ID` is set.

Trade-off I've accepted: zsh loses Ctrl-l (clear screen), Ctrl-h (backspace), Ctrl-j and Ctrl-k. tmux took these too.

### The sidebar panels (Herdr only)

The Spaces and Agents panels can take keyboard focus. In Herdr the shipped ones can't, so they're cloned as `spaces-nav` and `agents-nav` with `"focusable": true`. The panel with focus shows its title in the accent colour, and the highlight clears when focus leaves.

**In Spaces:**
- `j` / `k` (or the arrow keys) switch to the next or previous space right away, so I can see it, but keyboard focus stays in the panel. Switching a space normally moves focus to its pane, so take it back after each switch.
- `Enter`, `l`, `Esc` or Ctrl-l: go into that space's terminal.

**In Agents:**
- `j` / `k` move a highlight box between agents without switching.
- `Enter`: jump to that agent's pane.
- `l`, `Esc` or Ctrl-l: back to the terminal.

**Going back to the terminal:** focus the shown tab's current pane by its id. Don't use "move right": Herdr's `pane.go` picks the most recently focused pane, which can be in another space, and then nothing visible gets focus.

### Ctrl-s prefix keys (tmux-style)

| Ctrl-s, then | Does |
|---|---|
| `c` | New tab |
| `h` / `l` | Previous / next tab |
| `1`–`9` | Go to tab 1–9 |
| `"` | Split down |
| `%` | Split right |
| arrow keys | Move between panes |
| `o` | Move to the pane on the right |
| `x` | Close pane |
| `&` | Close tab |
| `z` | Zoom the pane, or unzoom |
| `,` | Rename tab |
| `$` | Rename space (Rex: session) |
| `(` / `)` | Previous / next space (Rex: session) |
| `w` / `s` | Open the picker (Rex: `w` Go to Anything, `s` session picker) |
| `r` | Reload config (Rex) |
| Ctrl-s | Send a real Ctrl-s to the program (Rex) |

Tabs are h/l, not n/p. I don't want Shift-H/L or Ctrl-Shift-H/L for tabs; I tried them and reverted.

### App defaults I keep

In Rex: keep Rex's own defaults (Cmd-T, Cmd-1–9, Cmd-N, Cmd-K, Cmd-P, Cmd-D / Cmd-Shift-D, Cmd-W closes the pane, else the tab) and add the Herdr ones it lacks: Ctrl-1–9 go to session, F2 rename tab, Shift-F2 rename session, Cmd-B toggle sidebar.

In Herdr, keep the Herdr app's own shortcuts: Cmd-T new tab, Cmd-W close tab, Cmd-1–9 go to tab, Ctrl-1–9 go to space, Cmd-N new space, Shift-F2 rename space, F2 rename tab, Cmd-] / Cmd-[ next or previous agent, Cmd-P picker, Cmd-D / Cmd-Shift-D split, Cmd-B toggle sidebar.

## Look

- **Theme:** Catppuccin Mocha. Herdr needs a theme file (`themes/catppuccin-mocha.json`) with the standard Mocha palette, set in `settings.json`.
- **Font:** JetBrains Mono, size 18, ligatures off.
- **Background:** blurred, about 90% opaque. In Herdr this needs a cloned layout (`layouts/ghostty.json`) with `"window_blur": true` and `background`, `canvas` and `chrome` colours ending in alpha `e6`.
- **Option key works as Alt:** Ghostty `macos-option-as-alt = true`, Herdr `"option_as_alt": "on"`, Rex Option key "sends Alt".
- **Rex:** these live in the app, not a file, so `rex/settings.sh` sets them with `rex do client.setting.…`. Rex has no opacity number; the Glass interface style with glass panes is its blurred see-through look, and it needs macOS 26 (on macOS 15 the script skips it and the background stays solid). Font is `JetBrainsMono Nerd Font Mono` (what's installed). Rex doesn't ship Catppuccin, so `rex/Catppuccin Mocha Official` (Ghostty theme format, official palette with a `#585b70` selection) is imported. Don't use Ghostty's bundled copy: its selection is rosewater and its bright colours are lightened. "Tint with theme" must be on, or the sidebar and window frame stay neutral grey. Fade inactive panes by text only; fading the surface turns them grey.

## Neovim

- LazyVim, stock keys, leader Space.
- Extras: mini-files, json, typescript, mini-animate.
- Options: no relative numbers, no swapfile, root is the current directory, no automatic comment continuation, no signature-help popup.
- `lua/config/keymaps.lua` holds the Ctrl-h/j/k/l edge-navigation mapping. There's no vim-tmux-navigator plugin.
- A running Neovim only picks up keymap changes after a restart. Tell me to restart it rather than debugging something else.

## Rex implementation notes

Everything lives in `~/.config/rex/init.lua`, which is `config/rex/init.lua` in this repo, plus the app settings in `config/rex/settings.sh`.

- **Ctrl-h/j/k/l** are Lua function bindings. Each calls the terminal block's `process` method, checks the foreground program's name against the vim pattern, and returns `false` (Rex then sends the key to the program) or calls `rex.session.focus_direction`.
- **Ctrl-s prefix** keys are key sequences (`ctrl+s>c`). Shifted symbols are written unshifted: `"` is `shift+'`, `%` is `shift+5`, `&` is `shift+7`, `$` is `shift+4`, `(`/`)` are `shift+9`/`shift+0`.
- **Ctrl-1–9** run the custom action `session_goto`, which picks the Nth session from `session.list` and asks the app to select it.
- **Reloading:** Rex doesn't watch the file. Run `rex config reload` (or `Ctrl-s r`). `rex config check FILE` validates a draft; `rex keymap` lists what loaded.
- **App settings** need Remote Control on (Settings → General). That's my call; tell me rather than turning it on.
- **Checking work:** `rex -C <client> actions` lists action names and arguments; `rex do <action>` runs one; `rex send-key -b BLOCK ctrl+l` sends a key straight to a program (it skips Rex's own bindings, so it tests nvim's mapping, not `init.lua`'s).
- **Updating the repo:** copy `~/.config/rex/init.lua` back to `config/rex/`.

## Herdr implementation notes (legacy)

Everything lives in `~/.config/herdr-app/`, which is `config/herdr/` in this repo.

- **`settings.json`:** theme, font, size, `option_as_alt`.
- **`keys.json`:**
  - `global` section: the Ctrl-s prefix keys, and Ctrl-h/j/k/l running `pane.go` (used in the sidebar).
  - `terminal` section: Ctrl-h/j/k/l running `pane-nav.left` and so on.
  - `mod:spaces-nav` and `mod:agents-nav` sections: Ctrl-l running `<mod>.back`.
- **`layouts/ghostty.json`:** clone of the shipped `main` layout, with blur, the `*-nav` mods in the sidebar, and a zero-height block running `pane-nav` so it always receives commands. It has to stay in the layout even when the sidebar is hidden.
- **`mods/pane-nav`:** receives a direction. If vim, nvim or fzf is in front, it sends the real key with `hc keys <terminal> ctrl+h`. Otherwise it runs `pane.go`.
- **`mods/spaces-nav`, `mods/agents-nav`:** clones of the shipped panels, with focus handling, j/k/Enter, a 250 ms check that clears the highlight when focus leaves, and the "back to terminal" fix described above.
- **Checking work:** after editing, run `herdr-app check <mod folder>` and `herdr-app status`, which lists errors. `herdr-app shot` saves a screenshot. `herdr-app do <command>` tests a key's command without pressing the key.
- **Updating the repo:** copy only files I own. Leave out the generated `gpui-kit.d.ts` and `jsconfig.json`.
- **Clones don't update:** the panel clones won't pick up Herdr updates. After a major Herdr update, re-clone from the new shipped versions and re-apply the changes.

## Shell

- `.zshrc` does not auto-start tmux or herdr.
- `~/.local/bin` is on PATH, where `herdr-app` and `hc` live.

## Phone access (Herdr)

The Herdr phone app connects to the Mac over SSH. It needs Remote Login on (System Settings → General → Sharing, allowed for my user only), my username, and port 22. For use away from home Wi-Fi, use Tailscale and its machine name. The Mac has to be awake. Turning on SSH is my call; tell me the steps rather than doing it.

## When something doesn't work

- **Rex keys do nothing:** run `rex config reload` and `rex config check`, and check the app hasn't set its own shortcut for that key (app shortcuts beat `init.lua`).
- **Herdr keys do nothing:** check the app reloaded (`keys.error` and `herdr-app status`), and that the shortcut isn't being typed into the terminal version of herdr running inside the app.
- **Can't leave Neovim with Ctrl-h/j/k/l:** Neovim was probably opened before the keymap existed. Restart it.
- **The sidebar won't hand focus back:** focus the shown tab's pane directly; don't use `pane.go`.
- **Report honestly:** tell me what you tested (by running commands or taking screenshots) and what you couldn't test with real keypresses.
