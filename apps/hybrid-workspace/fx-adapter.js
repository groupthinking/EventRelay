import { parseTermCommand } from "./logic.js";

/**
 * Local activity log + optional future libfx hook.
 * Bare `libfx/browser` is not resolvable from python http.server.
 * Do not put AI_GATEWAY_API_KEY on window.
 */
export async function attachFx(xterm, { onCommand } = {}) {
  const status = { mode: "log", runtime: null };
  xterm.writeln("Activity log. Type: summarize | extract | escalate | embed | ask <text>");
  let buf = "";
  xterm.onData((data) => {
    for (const ch of data) {
      if (ch === "\r" || ch === "\n") {
        xterm.write("\r\n");
        const parsed = parseTermCommand(buf);
        buf = "";
        onCommand?.(parsed.action, parsed.text);
        continue;
      }
      if (ch === "\u007f") {
        if (buf.length) {
          buf = buf.slice(0, -1);
          xterm.write("\b \b");
        }
        continue;
      }
      buf += ch;
      xterm.write(ch);
    }
  });
  return status;
}

export function fxPrompt(action, payload) {
  const map = {
    summarize: "Summarize the active preview / lesson content.",
    extract: "Extract and clarify the current editor or quote selection.",
    escalate: "Create a local support reference from this session.",
    embed: "Keep the learner in split-screen: workspace left, assistant right.",
    ask: payload || "Ask about the active video or project.",
  };
  return map[action] || map.ask;
}
