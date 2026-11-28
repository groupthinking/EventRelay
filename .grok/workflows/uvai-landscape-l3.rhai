let meta = #{
    name: "uvai-landscape-l3",
    description: "Adversarial refute of L2 proposed structure",
    when_to_use: "Only after l2-proposal.json exists",
    phases: [
        #{ title: "Skeptic", detail: "read apps/ and refute over-build" },
    ],
};

let propose_schema = #{
    "type": "object",
    "required": ["keep", "adapt", "ignore", "proposed_top_level", "rationale"],
    "properties": #{
        "keep": #{ "type": "array", "items": #{ "type": "string" } },
        "adapt": #{ "type": "array", "items": #{ "type": "string" } },
        "ignore": #{ "type": "array", "items": #{ "type": "string" } },
        "proposed_top_level": #{ "type": "array", "items": #{ "type": "string" } },
        "rationale": #{ "type": "string" },
    },
};

phase("Skeptic");
let p = "Adversarially refute the L2 proposal. You must read_file at least one file under ";
p += "/Users/garvey/Dev/EventRelay/apps/web/src/components/VideoWorkflowStudio.tsx ";
p += "and /Users/garvey/Dev/EventRelay-landscape/docs/landscape/WATERFALL.md. ";
p += "Call out over-build or say none with evidence. Prefer fewer dirs. ";
p += "Read scratch or docs l2-proposal.json if you can find it.";

let sk = agent(p, #{
    label: "skeptic",
    capability_mode: "read-only",
    output_schema: propose_schema,
});

if sk == () || !sk.success {
    complete(#{ summary: "L3 failed closed" });
}
let path = write_scratch_file("l3-skeptic.json", json_encode(sk.output));
complete(#{ path: path, skeptic: sk.output });
