let meta = #{
    name: "uvai-p3-act",
    description: "Implement Act on the same Analyze run in OneLoopStudio",
    when_to_use: "P3: wire Act to the selected video transcript and show results on /",
    phases: [
        #{ title: "Implement", detail: "edit OneLoopStudio Act path only" },
    ],
};

let report_schema = #{
    "type": "object",
    "required": ["changed", "files", "what"],
    "properties": #{
        "changed": #{ "type": "boolean" },
        "files": #{ "type": "array", "items": #{ "type": "string" } },
        "what": #{ "type": "string" },
    },
};

phase("Implement");
let p = "P3 implementer. Read /Users/garvey/Dev/EventRelay/docs/NEXT-PHASE.md and ";
p += "/Users/garvey/Dev/EventRelay/apps/web/src/components/OneLoopStudio.tsx. ";
p += "Act must use the selected video on this page. If selected.transcript exists, prefer that ";
p += "path (do not pretend extract-events is public). Public Act may still call startVideoToActions ";
p += "with the same URL. Results must render in the Act results section. ";
p += "Do not add ADK/LWP. Do not use dQw4w9WgXcQ. Fixture auJzb1D-fag. ";
p += "Edit only OneLoopStudio and tests if needed. Return files you changed.";

let r = agent(p, #{
    label: "act-implementer",
    capability_mode: "read-write",
    output_schema: report_schema,
});

if r == () || !r.success {
    complete(#{ summary: "p3-act failed closed", changed: false });
}
complete(r.output);
