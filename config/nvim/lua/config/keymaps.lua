-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua

-- Search
vim.keymap.set("n", "<leader>h", ":nohlsearch<CR>", { desc = "Clear Search Highlight" })

-- Telescope
vim.keymap.set("n", "<leader>fg", function() require("telescope.builtin").live_grep() end, { desc = "Live Grep" })

-- LSP
vim.keymap.set("n", "<leader>gd", vim.lsp.buf.definition, { desc = "Go to Definition" })
vim.keymap.set("n", "<leader>uL", function()
  local clients = vim.lsp.get_clients({ bufnr = 0 })
  if #clients > 0 then
    vim.lsp.stop_client(clients)
    vim.notify("LSP stopped")
  else
    vim.cmd("LspStart")
    vim.notify("LSP started")
  end
end, { desc = "Toggle LSP" })
