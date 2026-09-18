let meta = #{
    name: "uvai-p3-verify",
    description: "Verify Act results can appear on the same Studio page",
    when_to_use: "After /uvai-p3-act, before calling P3 done",
    phases: [
        #{ title: "Verify", detail: "read code; curl Act start if you can execute" },
    ],
};

let report_schema = #{
    "type": "object",
    "required": ["pass", "evidence", "gap"],
    "properties": #{
        "pass": #{ "type": "boolean" },
        "evidence": #{ "type": "string" },
        "gap": #{ "type": "string" },
    },
};

phase("Verify");
let p = "Adversarial P3 verifier. Read OneLoopStudio.tsx act() and the Act results JSX. ";
p += "If you can execute, POST localhost:3000 or uvai.io /api/workflows/video-to-actions ";
p += "with url https://www.youtube.com/watch?v=auJzb1D-fag — never dQw4w9WgXcQ. ";
p += "pass=true only if (1) Act UI exists on / and (2) start returns runId or you cite a real blocker. ";
p += "Default pass=false if you did not read the file. evidence must cite paths or HTTP.";

let r = agent(p, #{
    label: "act-verifier",
    capability_mode: "execute",
    output_schema: report_schema,
});

if r == () || !r.success || r.output.evidence == () {
    complete(#{ pass: false, evidence: "verifier failed closed", gap: "no evidence" });
}
complete(r.output);
