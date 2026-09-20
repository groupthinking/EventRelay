/**
 * Isolated fx hook.
 * Tries libfx browser terminal when JSPI + key exist.
 * Always exposes write/log so the UI never depends on Gateway.
 */
export async function attachFx(xterm, env = {}) {
  const status = { mode: "fallback", runtime: null };

  const hasKey = Boolean(env.AI_GATEWAY_API_KEY);
  const hasJspi = typeof WebAssembly !== "undefined" &&
    typeof WebAssembly.Suspending === "function";

  if (hasKey && hasJspi) {
    try {
      const mod = await import("libfx/browser");
      if (mod.createFxTerminal && mod.xtermAdapter) {
        status.runtime = await mod.createFxTerminal({
          terminal: mod.xtermAdapter(xterm),
          env,
        });
        status.mode = "fx";
        return status;
      }
    } catch (err) {
      console.warn("fx unavailable, using local terminal", err);
    }
  }

  xterm.writeln("fx fallback online. Set AI_GATEWAY_API_KEY + JSPI to attach libfx.");
  xterm.writeln("Actions: summarize | extract | escalate | embed | ask <text>");
  return status;
}

export function fxPrompt(action, payload) {
  const map = {
    summarize: "Summarize the active preview / lesson content.",
    extract: "Extract and clarify the current editor or quote selection.",
    escalate: "File a human support ticket from this workspace session.",
    embed: "Keep the learner in split-screen: workspace left, assistant right.",
    ask: payload || "Ask about the active video or project.",
  };
  return map[action] || map.ask;
}
