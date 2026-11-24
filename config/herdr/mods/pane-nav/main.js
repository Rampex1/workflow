// vim-tmux-navigator for Herdr: ctrl-h/j/k/l in a terminal (keys.json "terminal" section)
// arrive here. vim/nvim/fzf in front get the key (nvim moves its own splits and calls
// pane.go at its edge); anything else moves to the neighbouring pane or panel.
import { View, div } from "gpui-kit";
import { run, focused, panes, hc, nextCommand, checking } from "herdr";

const VIM = /^(view|l?n?vim?x?|fzf)(diff)?$/i; // vim-tmux-navigator's pattern
const KEY = { left: "ctrl+h", down: "ctrl+j", up: "ctrl+k", right: "ctrl+l" };

export default class PaneNav extends View {
  init(_props, cx) {
    if (checking()) return;
    cx.spawn(async (cx) => {
      for (;;) {
        const dir = await nextCommand();
        if (!KEY[dir]) continue;
        const f = focused();
        const prog = f?.pane && panes().find((p) => p.pane === f.pane)?.program;
        if (f?.terminal && prog && (VIM.test(prog.key) || VIM.test(prog.name))) await hc(["keys", f.terminal, KEY[dir]]);
        else run("pane.go", { direction: dir });
      }
    });
  }
  render() { return div(); }
}
