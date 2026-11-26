let meta = #{
    name: "uvai-brief-data-models",
    description: "Large video datasets and Hermes vs serving RAG",
    when_to_use: "L0 cited brief for family data-models before L1 compare",
    phases: [
        #{ title: "Brief", detail: "read listed sources, write cited brief" },
    ],
};

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

phase("Brief");
let p = "Product north star: one user loop on uvai.io Studio — paste a real YouTube URL then transcript plus typed events then act (tools, agents, scaffold, deploy). EventRelay live tree is /Users/garvey/Dev/EventRelay (apps/web + src/youtube_extension). Adapt means wire into that loop. Ignore means do not copy webpack or start a second monorepo. Do not invent APIs. Do not use dQw4w9WgXcQ. Visit listed paths with read_file list_dir grep web_fetch. ";
p += "Family must be data-models. ";
p += "Must visit: https://huggingface.co/datasets/facebook/S-EMBER https://huggingface.co/datasets/VidaForge/VidaForge-3M https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B plus EventRelay embeddings and training-store. ";
p += "Read /Users/garvey/Dev/EventRelay-landscape/docs/landscape/WATERFALL.md first. ";
p += "Each facts item must contain a path or URL. If missing, put MISSING in visited and continue.";

let r = agent(p, #{
    label: "data-models",
    capability_mode: "read-only",
    output_schema: brief_schema,
});

if r == () || !r.success || r.output.family == () {
    complete(#{ summary: "brief failed closed", family: "data-models" });
}
let path = write_scratch_file("brief.json", json_encode(r.output));
complete(#{ path: path, family: "data-models", brief: r.output });
