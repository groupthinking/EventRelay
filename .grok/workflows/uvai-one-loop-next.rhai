let meta = #{
    name: "uvai-one-loop-next",
    description: "Gated P3 then P2 then P4 for the one-loop product",
    when_to_use: "Run the next phase after P1: Act same-run, then auth audit, then hygiene",
    phases: [
        #{ title: "P3-implement", detail: "Act on the same run" },
        #{ title: "P3-verify", detail: "fail closed" },
        #{ title: "P2-auth", detail: "public vs gated" },
        #{ title: "P4-hygiene", detail: "board only" },
    ],
};

let impl_schema = #{
    "type": "object",
    "required": ["changed", "files", "what"],
    "properties": #{
        "changed": #{ "type": "boolean" },
        "files": #{ "type": "array", "items": #{ "type": "string" } },
        "what": #{ "type": "string" },
    },
};
let verify_schema = #{
    "type": "object",
    "required": ["pass", "evidence", "gap"],
    "properties": #{
        "pass": #{ "type": "boolean" },
        "evidence": #{ "type": "string" },
        "gap": #{ "type": "string" },
    },
};
let auth_schema = #{
    "type": "object",
    "required": ["pass", "evidence"],
    "properties": #{
        "pass": #{ "type": "boolean" },
        "evidence": #{ "type": "string" },
    },
};
let hyg_schema = #{
    "type": "object",
    "required": ["pass", "did_not_delete"],
    "properties": #{
        "pass": #{ "type": "boolean" },
        "did_not_delete": #{ "type": "string" },
    },
};

phase("P3-implement");
let impl_p = "Implement P3 per /Users/garvey/Dev/EventRelay/docs/NEXT-PHASE.md. ";
impl_p += "Edit OneLoopStudio so Act is the same run and results render on /. Fixture auJzb1D-fag. No ADK. No dQw4w9WgXcQ.";
let impl = agent(impl_p, #{
    label: "act-implementer",
    capability_mode: "read-write",
    output_schema: impl_schema,
});

phase("P3-verify");
let ver_p = "Verify P3. Read OneLoopStudio.tsx. pass=true only with file evidence that Act results can show on /. ";
ver_p += "If you can curl, POST /api/workflows/video-to-actions with auJzb1D-fag. Default pass=false.";
let ver = agent(ver_p, #{
    label: "act-verifier",
    capability_mode: "execute",
    output_schema: verify_schema,
});

let impl_out = if impl != () && impl.success { impl.output } else { () };
let ver_out = if ver != () && ver.success { ver.output } else { () };
let ver_pass = if ver_out != () && ver_out.pass == true { true } else { false };
if !ver_pass {
    complete(#{
        summary: "P3 verify failed — stop",
        implement: impl_out,
        verify: ver_out,
    });
}

phase("P2-auth");
let auth_p = "Audit auth-paths.ts and OneLoopStudio 401 redirects. Do not add secrets. pass=true if stream and video-to-actions are public and studio-deploy is gated.";
let auth = agent(auth_p, #{
    label: "auth-auditor",
    capability_mode: "read-only",
    output_schema: auth_schema,
});

phase("P4-hygiene");
let hyg_p = "Mark stale Launch Board rows if needed. NEVER delete GitHub EventRelay Synced Database.";
let hyg = agent(hyg_p, #{
    label: "hygiene",
    capability_mode: "read-write",
    output_schema: hyg_schema,
});

complete(#{
    summary: "next phase finished",
    implement: impl_out,
    verify: ver_out,
    auth: if auth != () && auth.success { auth.output } else { () },
    hygiene: if hyg != () && hyg.success { hyg.output } else { () },
});
