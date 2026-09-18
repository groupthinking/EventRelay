let meta = #{
    name: "uvai-deep-research",
    description: "Deep-research one UVAI source against the one-loop product intent",
    when_to_use: "After P1 when a source (Google Doc, Notion, HF) still has unread sections",
    phases: [
        #{ title: "Read", detail: "open the source with tools" },
        #{ title: "Compare", detail: "match or gap vs one-loop intent" },
    ],
};

let report_schema = #{
    "type": "object",
    "required": ["source", "intent_match", "keep", "ignore", "gaps"],
    "properties": #{
        "source": #{ "type": "string" },
        "intent_match": #{ "type": "boolean" },
        "keep": #{ "type": "array", "items": #{ "type": "string" } },
        "ignore": #{ "type": "array", "items": #{ "type": "string" } },
        "gaps": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

let source = if args == () { () } else { args.source };
if source == () { pause("verification", "Pass args.source — a URL or path."); }

phase("Read");
let p = "Read this UVAI source with tools (read_file, grep, or cited URL). ";
p += "Source: ";
p += source;
p += " Product intent: one Studio loop paste YouTube then transcript then events then act on uvai.io. ";
p += "Do not invent ADK/LWP/Ultron as something to build. Report keep/ignore/gaps with evidence.";

let r = agent(p, #{
    label: "reader",
    capability_mode: "read-only",
    output_schema: report_schema,
});

phase("Compare");
if r == () || !r.success {
    complete(#{ summary: "deep-research failed closed", source: source });
}
let path = write_scratch_file("deep-research.json", json_encode(r.output));
complete(#{ path: path, report: r.output });
