let meta = #{
    name: "uvai-landscape-waterfall",
    description: "Run exactly one landscape gate: l0, l1, l2, or l3",
    when_to_use: "Advance the UVAI landscape waterfall one verified gate at a time",
    phases: [
        #{ title: "Gate", detail: "dispatch the requested gate only" },
    ],
};

let gate = if args == () { () } else { args.gate };
if gate == () {
    pause("verification", "Pass args.gate — l0, l1, l2, or l3. Do not skip ahead.");
}

phase("Gate");
log("landscape waterfall gate=" + gate);

if gate == "l0" {
    let brief_schema = #{
        "type": "object",
        "required": ["family", "visited", "facts", "eventrelay_overlap", "gaps"],
        "properties": #{
            "family": #{ "type": "string" },
            "visited": #{ "type": "array", "items": #{ "type": "string" } },
            "facts": #{ "type": "array", "maxItems": 12, "items": #{ "type": "string" } },
            "eventrelay_overlap": #{ "type": "string" },
            "gaps": #{ "type": "string" },
        },
    };
    let families = ["eventrelay", "local-corpus", "memory", "video-agents", "avatars", "data-models", "learn-runtime"];
    let jobs = [];
    for f in families {
        let pr = "Cited L0 brief for family ";
        pr += f;
        pr += ". North star: one Studio loop on uvai.io. Read WATERFALL.md. Use tools. Do not invent APIs.";
        jobs.push(#{
            prompt: pr,
            label: f,
            capability_mode: "read-only",
            output_schema: brief_schema,
        });
    }
    let results = parallel(jobs);
    let briefs = [];
    let i = 0;
    for r in results {
        if r != () && r.success && r.output.family != () { briefs.push(r.output); }
        else { log("L0 failed: " + families[i]); }
        i += 1;
    }
    let path = write_scratch_file("inventory.json", json_encode(briefs));
    complete(#{ gate: "l0", path: path, count: briefs.len() });
}

if gate == "l1" {
    let row_schema = #{
        "type": "object",
        "required": ["family", "keep", "adapt", "ignore", "eventrelay_paths", "north_star_note"],
        "properties": #{
            "family": #{ "type": "string" },
            "keep": #{ "type": "array", "items": #{ "type": "string" } },
            "adapt": #{ "type": "array", "items": #{ "type": "string" } },
            "ignore": #{ "type": "array", "items": #{ "type": "string" } },
            "eventrelay_paths": #{ "type": "array", "items": #{ "type": "string" } },
            "north_star_note": #{ "type": "string" },
        },
    };
    let families = ["eventrelay", "local-corpus", "memory", "video-agents", "avatars", "data-models", "learn-runtime"];
    let inv = "/Users/garvey/Dev/EventRelay-landscape/docs/landscape/l0-inventory.json";
    let jobs = [];
    for f in families {
        let pr = "L1 keep/adapt/ignore for ";
        pr += f;
        pr += ". Read ";
        pr += inv;
        pr += " and VideoWorkflowStudio.tsx. Adapt must name an EventRelay path. North star is the one Studio loop.";
        jobs.push(#{
            prompt: pr,
            label: "l1-" + f,
            capability_mode: "read-only",
            output_schema: row_schema,
        });
    }
    let results = parallel(jobs);
    let rows = [];
    let i = 0;
    for r in results {
        if r != () && r.success && r.output.family != () { rows.push(r.output); }
        else { log("L1 failed: " + families[i]); }
        i += 1;
    }
    let path = write_scratch_file("l1-compare.json", json_encode(rows));
    complete(#{ gate: "l1", path: path, count: rows.len() });
}

if gate == "l2" {
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
    let p = "L2 propose structure from L1 only. Read l1-compare.json under docs/landscape or fail. No second monorepo.";
    let prop = agent(p, #{
        label: "l2",
        capability_mode: "read-only",
        output_schema: propose_schema,
    });
    if prop == () || !prop.success { complete(#{ gate: "l2", summary: "failed closed" }); }
    let path = write_scratch_file("l2-proposal.json", json_encode(prop.output));
    complete(#{ gate: "l2", path: path });
}

if gate == "l3" {
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
    let p = "L3 skeptic. Read VideoWorkflowStudio.tsx and L2 proposal. Call out over-build.";
    let sk = agent(p, #{
        label: "l3",
        capability_mode: "read-only",
        output_schema: propose_schema,
    });
    if sk == () || !sk.success { complete(#{ gate: "l3", summary: "failed closed" }); }
    let path = write_scratch_file("l3-skeptic.json", json_encode(sk.output));
    complete(#{ gate: "l3", path: path });
}

pause("verification", "Unknown args.gate — use l0, l1, l2, or l3");
