let meta = #{
    name: "uvai-landscape-l1",
    description: "Compare each L0 family to EventRelay against the one Studio loop",
    when_to_use: "After L0 inventory exists; before any folder structure proposal",
    phases: [
        #{ title: "Compare", detail: "one keep/adapt/ignore row per family" },
        #{ title: "Synthesize", detail: "north-star gap plus table" },
    ],
};

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

let synth_schema = #{
    "type": "object",
    "required": ["north_star_gap", "rows_ok", "blocked_reason"],
    "properties": #{
        "north_star_gap": #{ "type": "string" },
        "rows_ok": #{ "type": "boolean" },
        "blocked_reason": #{ "type": "string" },
    },
};

phase("Compare");
let inv = "/Users/garvey/Dev/EventRelay-landscape/docs/landscape/l0-inventory.json";
let families = ["eventrelay", "local-corpus", "memory", "video-agents", "avatars", "data-models", "learn-runtime"];
let jobs = [];
for f in families {
    let pr = "L1 compare for family ";
    pr += f;
    pr += ". Product north star: one Studio loop paste YouTube then transcript/events then act/deploy on uvai.io. ";
    pr += "Read ";
    pr += inv;
    pr += " and WATERFALL.md. Read EventRelay apps/web VideoWorkflowStudio.tsx, /api/pipeline, video-to-actions.ts. ";
    pr += "keep = already in EventRelay and should stay. ";
    pr += "adapt = existing code or idea that should enter a named EventRelay path (write that path in the string). ";
    pr += "ignore = do not copy (webpack trees, CC-BY-NC TB datasets, second runtime). ";
    pr += "eventrelay_paths must be real files you read. Do not invent APIs. Family field must equal ";
    pr += f;
    pr += ".";
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
    if r != () && r.success && r.output.family != () {
        rows.push(r.output);
    } else {
        log("L1 slot failed: " + families[i]);
    }
    i += 1;
}
log(rows.len().to_string() + "/" + families.len().to_string() + " L1 rows");

phase("Synthesize");
let sp = "Synthesize L1 against the north star. Read VideoWorkflowStudio.tsx and l0-inventory.json. ";
sp += "north_star_gap must describe Studio planning-draft vs live pipeline in concrete file terms. ";
sp += "rows_ok true only if you received 7 family rows and each adapt names an EventRelay path or explicitly says none. ";
sp += "blocked_reason empty string if rows_ok else why L2 must not start. Rows JSON:\n";
sp += json_encode(rows);

let syn = agent(sp, #{
    label: "l1-synth",
    capability_mode: "read-only",
    output_schema: synth_schema,
});

let payload = #{
    rows: rows,
    synth: if syn != () && syn.success { syn.output } else { () },
};
let path = write_scratch_file("l1-compare.json", json_encode(payload));
complete(#{ path: path, count: rows.len() });
