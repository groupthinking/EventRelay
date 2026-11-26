let meta = #{
    name: "uvai-brief-eventrelay",
    description: "EventRelay live product plus Vercel v0-uvai",
    when_to_use: "L0 cited brief for family eventrelay before L1 compare",
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
p += "Family must be eventrelay. ";
p += "Must visit: /Users/garvey/Dev/EventRelay /Users/garvey/Dev/EventRelay/apps/web/src/components/VideoWorkflowStudio.tsx /Users/garvey/Dev/EventRelay/apps/web/src/app/api/pipeline/route.ts /Users/garvey/Dev/EventRelay/apps/web/src/workflows/video-to-actions.ts /Users/garvey/Dev/EventRelay/docs/WORKFLOW_DEVKIT.md /Users/garvey/Dev/EventRelay/CANONICAL.md https://github.com/groupthinking/EventRelay https://vercel.com/garv1/v0-uvai https://uvai.io. ";
p += "Read /Users/garvey/Dev/EventRelay-landscape/docs/landscape/WATERFALL.md first. ";
p += "Each facts item must contain a path or URL. If missing, put MISSING in visited and continue.";

let r = agent(p, #{
    label: "eventrelay",
    capability_mode: "read-only",
    output_schema: brief_schema,
});

if r == () || !r.success || r.output.family == () {
    complete(#{ summary: "brief failed closed", family: "eventrelay" });
}
let path = write_scratch_file("brief.json", json_encode(r.output));
complete(#{ path: path, family: "eventrelay", brief: r.output });
