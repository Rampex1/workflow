-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua

local map = vim.keymap.set

map("n", "<leader>h", "<cmd>nohlsearch<cr>", { desc = "Clear Search Highlight" })
-- LazyVim.pick uses whichever picker is installed (snacks here; telescope isn't)
map("n", "<leader>fg", LazyVim.pick("live_grep"), { desc = "Live Grep" })
map("n", "<leader>gd", vim.lsp.buf.definition, { desc = "Go to Definition" })

map("n", "<leader>uL", function()
  local clients = vim.lsp.get_clients({ bufnr = 0 })
  if #clients > 0 then
    vim.lsp.stop_client(clients)
    vim.notify("LSP stopped")
  else
    vim.cmd("LspStart")
    vim.notify("LSP started")
  end
end, { desc = "Toggle LSP" })
