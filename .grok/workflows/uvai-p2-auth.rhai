let meta = #{
    name: "uvai-p2-auth",
    description: "Audit one-loop auth honesty without inventing local secrets",
    when_to_use: "After P3 verify; confirm public vs gated routes",
    phases: [
        #{ title: "Audit", detail: "read auth-paths and Studio 401 redirects" },
    ],
};

let report_schema = #{
    "type": "object",
    "required": ["pass", "public_ok", "gated_ok", "evidence"],
    "properties": #{
        "pass": #{ "type": "boolean" },
        "public_ok": #{ "type": "boolean" },
        "gated_ok": #{ "type": "boolean" },
        "evidence": #{ "type": "string" },
    },
};

phase("Audit");
let p = "Read /Users/garvey/Dev/EventRelay/apps/web/src/lib/auth-paths.ts and OneLoopStudio.tsx. ";
p += "public_ok if /api/pipeline/stream and /api/workflows/video-to-actions are public. ";
p += "gated_ok if /api/workflows/studio-deploy is NOT public and 401/403 sends the user to /login. ";
p += "Do not claim local deploy 401 if NEXTAUTH_SECRET is missing. Do not add secrets. ";
p += "pass = public_ok and gated_ok.";

let r = agent(p, #{
    label: "auth-auditor",
    capability_mode: "read-only",
    output_schema: report_schema,
});

if r == () || !r.success {
    complete(#{ pass: false, public_ok: false, gated_ok: false, evidence: "audit failed closed" });
}
complete(r.output);
