"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.useBuiltInAI = useBuiltInAI;
const react_1 = require("react");
const builtin_ai_1 = require("@/lib/services/builtin-ai");
/**
 * React hook exposing Chrome Built-in AI capabilities.
 *
 * Usage:
 * ```tsx
 * const { available, summarize, extractEvents } = useBuiltInAI();
 * if (available.promptAPI) {
 *   const summary = await summarize(transcript);
 * }
 * ```
 */
function useBuiltInAI() {
    const [available, setAvailable] = (0, react_1.useState)({
        promptAPI: false,
        summarizerAPI: false,
    });
    (0, react_1.useEffect)(() => {
        (0, builtin_ai_1.checkCapabilities)().then(setAvailable);
    }, []);
    return {
        available,
        summarize: builtin_ai_1.summarizeTranscript,
        extractEvents: builtin_ai_1.extractEventsLocal,
    };
}
//# sourceMappingURL=use-builtin-ai.js.map