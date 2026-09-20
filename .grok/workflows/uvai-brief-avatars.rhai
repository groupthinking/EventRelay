let meta = #{
    name: "uvai-brief-avatars",
    description: "Talking-head avatars vs existing realtime token",
    when_to_use: "L0 cited brief for family avatars before L1 compare",
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
p += "Family must be avatars. ";
p += "Must visit: https://anam.ai/interactive-avatars plus EventRelay apps/web/src/app/api/realtime/session/route.ts and use-realtime-voice.ts. ";
p += "Read /Users/garvey/Dev/EventRelay-landscape/docs/landscape/WATERFALL.md first. ";
p += "Each facts item must contain a path or URL. If missing, put MISSING in visited and continue.";

let r = agent(p, #{
    label: "avatars",
    capability_mode: "read-only",
    output_schema: brief_schema,
});

if r == () || !r.success || r.output.family == () {
    complete(#{ summary: "brief failed closed", family: "avatars" });
}
let path = write_scratch_file("brief.json", json_encode(r.output));
complete(#{ path: path, family: "avatars", brief: r.output });
