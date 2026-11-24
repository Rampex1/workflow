-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua

-- vim-tmux-navigator replacement for Herdr: ctrl-h/j/k/l moves between nvim splits,
-- and past the last split moves to the neighbouring Herdr pane/panel.
local dirs = { h = "left", j = "down", k = "up", l = "right" }
for key, dir in pairs(dirs) do
  vim.keymap.set("n", "<C-" .. key .. ">", function()
    local win = vim.fn.winnr()
    vim.cmd("wincmd " .. key)
    if vim.fn.winnr() == win and vim.env.HC_TERMINAL_ID then
      vim.fn.jobstart({ "herdr-app", "do", "pane.go", vim.json.encode({ direction = dir }) }, { detach = true })
    end
  end, { desc = "Navigate " .. dir })
end
