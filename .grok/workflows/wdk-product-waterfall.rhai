let meta = #{
    name: "wdk-product-waterfall",
    description: "Verify EventRelay product gates in order: smoke B, schema 3b, then whether C may start",
    when_to_use: "Check Act-on-findings production status before starting WDK C",
    phases: [
        #{ title: "Verify", detail: "read live git, schema, and smoke evidence" },
    ],
};

let report_schema = #{
    "type": "object",
    "required": ["gate_3_smoke_b", "gate_3b_schema", "gate_4_c_allowed", "evidence", "next"],
    "properties": #{
        "gate_3_smoke_b": #{ "type": "string" },
        "gate_3b_schema": #{ "type": "string" },
        "gate_4_c_allowed": #{ "type": "boolean" },
        "evidence": #{ "type": "string" },
        "next": #{ "type": "string" },
    },
};

phase("Verify");
let prompt = "You are verifying EventRelay product gates. Use tools. Do not guess.";
prompt += " 1) read_file /Users/garvey/BrainVault/UVAI-EventRelay-SSOT/14-MASTER-TRACKING.md and 10-NEXT-TURN.md.";
prompt += " 2) grep apps/web/src/lib/action-tools.ts for get_agent_session_logs and its required array.";
prompt += " 3) If you can execute, curl -sS -X POST https://uvai.io/api/workflows/video-to-actions";
prompt += " with JSON url https://www.youtube.com/watch?v=dQw4w9WgXcQ and report ok/runId/code only.";
prompt += " 4) Set gate_3_smoke_b to pass if a production runId and terminal status already exist";
prompt += " (wrun_01KZYCN3XJMP9ANBXEARCNM41F on dpl_7KGT counts).";
prompt += " 5) Set gate_3b_schema to pass only if required includes every properties key";
prompt += " for get_agent_session_logs (must include agentType). Otherwise fail.";
prompt += " 6) gate_4_c_allowed is true only if 3 is pass AND 3b is pass.";
prompt += " Return the schema fields. Evidence must cite file paths or HTTP bodies you actually read.";

let r = agent(prompt, #{
    label: "verify-product-gates",
    capability_mode: "execute",
    output_schema: report_schema,
});

if r == () || !r.success || r.output.evidence == () {
    complete(#{ summary: "verifier failed closed", gate_4_c_allowed: false });
}
complete(r.output);
