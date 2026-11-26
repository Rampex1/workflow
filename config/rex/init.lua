-- Rex config. Migrated from Herdr app keys.json + tmux.conf; see ../SETUP-PROMPT.md.
-- Copy to ~/.config/rex/init.lua, then `rex config reload`.
-- Herdr "spaces" are Rex sessions, tabs are tabs (windows), panes are panes (blocks).

---------------------------------------------------------------------------
-- Ctrl-h/j/k/l: vim-tmux-navigator. If vim/nvim/fzf is in front, the key goes
-- to it (nvim's keymaps.lua moves on past its last split); otherwise move pane.
---------------------------------------------------------------------------
local function in_vim(ctx)
  local p = rex.block.call("com.superlogical.terminal", "process", { block_id = ctx.block_id })
  local name = p and p.foreground and p.foreground.name or ""
  name = name:gsub("diff$", "")
  -- vim-tmux-navigator's pattern: (view|l?n?vim?x?|fzf)(diff)?
  return name == "view" or name == "fzf" or name:match("^l?n?vim?x?$") ~= nil
end

for key, dir in pairs({ h = "left", j = "down", k = "up", l = "right" }) do
  rex.bind("ctrl+" .. key, function(ctx)
    if in_vim(ctx) then return false end -- false: Rex sends the key to the terminal
    rex.session.focus_direction({ direction = dir })
    return true
  end)
end

---------------------------------------------------------------------------
-- Ctrl-s prefix, tmux-style
---------------------------------------------------------------------------
rex.bind("ctrl+s>ctrl+s", "pane.send_key", { key = "ctrl+s" }) -- press twice to send ctrl+s
rex.bind("ctrl+s>r", "client.config.reload")

rex.bind("ctrl+s>c", "client.tab.new")
rex.bind("ctrl+s>h", "client.tab.previous")
rex.bind("ctrl+s>l", "client.tab.next")
for i = 1, 9 do
  rex.bind("ctrl+s>" .. i, "client.tab.goto", { index = i })
end
rex.bind("ctrl+s>shift+7", "client.tab.close") -- &
rex.bind("ctrl+s>,", "client.tab.rename")

rex.bind("ctrl+s>shift+'", "pane.split", { direction = "down" }) -- "
rex.bind("ctrl+s>shift+5", "pane.split", { direction = "right" }) -- %
for _, dir in ipairs({ "left", "right", "up", "down" }) do
  rex.bind("ctrl+s>" .. dir, "pane.focus", { direction = dir })
end
rex.bind("ctrl+s>o", "pane.focus", { direction = "right" })
rex.bind("ctrl+s>x", "pane.close")
rex.bind("ctrl+s>z", "pane.zoom")

rex.bind("ctrl+s>shift+4", "session.rename") -- $
rex.bind("ctrl+s>shift+9", "session.previous") -- (
rex.bind("ctrl+s>shift+0", "session.next") -- )
rex.bind("ctrl+s>w", "pane.go_to") -- picker: sessions, tabs, panes
rex.bind("ctrl+s>s", "session.switch")

---------------------------------------------------------------------------
-- Herdr app defaults that Rex doesn't already have
-- (Rex already has cmd+t, cmd+1..9, cmd+n, cmd+p, cmd+d, shift+cmd+d)
---------------------------------------------------------------------------
rex.bind("f2", "client.tab.rename")
rex.bind("shift+f2", "session.rename")
rex.bind("cmd+b", "client.sidebar.toggle")

rex.action({
  name = "session_goto",
  title = "Go to Session by Number",
  args = { index = "integer" },
  run = function(ctx, args)
    local list, err = rex.call("session.list")
    if not list then error(err, 0) end
    local s = (list.sessions or {})[args.index]
    if s then rex.client.queue("session.select", { session_id = s.session_id }) end
  end,
})
for i = 1, 9 do
  rex.bind("ctrl+" .. i, "session_goto", { index = i })
end
