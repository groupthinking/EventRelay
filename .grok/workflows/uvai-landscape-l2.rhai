let meta = #{
    name: "uvai-landscape-l2",
    description: "Propose EventRelay folder/integration structure from L1 only",
    when_to_use: "Only after l1-compare.json exists",
    phases: [
        #{ title: "Propose", detail: "structure mapped to L1 adapt rows" },
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

phase("Propose");
let p = "Propose folder structure for UVAI/EventRelay AFTER L1. ";
p += "Read /Users/garvey/Dev/EventRelay-landscape/docs/landscape/WATERFALL.md ";
p += "and l1-compare.json if present else fail and say L1 missing. ";
p += "Read /Users/garvey/Dev/EventRelay/apps/web and docs/WORKFLOW_DEVKIT.md. ";
p += "Do not create a second monorepo. Every proposed_top_level dir must map to an L1 adapt. ";
p += "Prefer keep existing apps/web + src/youtube_extension. No webpack copies.";

let prop = agent(p, #{
    label: "propose-structure",
    capability_mode: "read-only",
    output_schema: propose_schema,
});

if prop == () || !prop.success {
    complete(#{ summary: "L2 failed closed" });
}
let path = write_scratch_file("l2-proposal.json", json_encode(prop.output));
complete(#{ path: path, proposal: prop.output });
