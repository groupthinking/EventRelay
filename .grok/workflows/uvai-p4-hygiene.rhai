let meta = #{
    name: "uvai-p4-hygiene",
    description: "Mark stale Launch Board rows; never delete GitHub PR sync",
    when_to_use: "After P2 auth audit, board cleanup only",
    phases: [
        #{ title: "Hygiene", detail: "Notion Launch Board only" },
    ],
};

let report_schema = #{
    "type": "object",
    "required": ["pass", "touched", "did_not_delete"],
    "properties": #{
        "pass": #{ "type": "boolean" },
        "touched": #{ "type": "array", "items": #{ "type": "string" } },
        "did_not_delete": #{ "type": "string" },
    },
};

phase("Hygiene");
let p = "P4 hygiene. Notion Launch Board https://app.notion.com/p/3803c2339c04815fae06d6ebf047ea49 ";
p += "and DB https://app.notion.com/p/dc579a8a4de04ae2bc83ebf3f14944dc. ";
p += "Mark leftover stale P0/P1 rows that contradict one-loop (fake Studio shipped already updated). ";
p += "NEVER delete EventRelay Synced Database or GitHub PR sync 9cc3c2339c0482c590dd0112ee41c179. ";
p += "did_not_delete must name that PR sync. pass=true only if you did not delete it.";

let r = agent(p, #{
    label: "hygiene",
    capability_mode: "read-write",
    output_schema: report_schema,
});

if r == () || !r.success {
    complete(#{ pass: false, touched: [], did_not_delete: "hygiene failed closed" });
}
complete(r.output);
