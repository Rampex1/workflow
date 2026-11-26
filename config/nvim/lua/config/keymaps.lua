-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua

-- vim-tmux-navigator replacement for Rex: ctrl-h/j/k/l moves between nvim splits,
-- and past the last split moves to the neighbouring Rex pane (Herdr pane as fallback).
local dirs = { h = "left", j = "down", k = "up", l = "right" }
for key, dir in pairs(dirs) do
  vim.keymap.set("n", "<C-" .. key .. ">", function()
    local win = vim.fn.winnr()
    vim.cmd("wincmd " .. key)
    if vim.fn.winnr() ~= win then
      return
    end
    local arg = vim.json.encode({ direction = dir })
    if vim.env.REX_BLOCK then
      vim.fn.jobstart({ "rex", "api", "call", "-s", vim.env.REX_BLOCK, "session.focus_direction", arg }, { detach = true })
    elseif vim.env.HC_TERMINAL_ID then
      vim.fn.jobstart({ "herdr-app", "do", "pane.go", arg }, { detach = true })
    end
  end, { desc = "Navigate " .. dir })
end
