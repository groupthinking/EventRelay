let meta = #{
    name: "uvai-landscape-research",
    description: "Gated inventory of local UVAI corpus plus comparison sources; optional structure proposal",
    when_to_use: "Map EventRelay against existing local trees and external video-agent/dataset sources without touching product code",
    phases: [
        #{ title: "Inventory", detail: "one read-only brief per source family" },
        #{ title: "Propose", detail: "structure only when mode=full" },
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

let mode = "inventory";
if args != () && args.mode != () { mode = args.mode; }

phase("Inventory");
let families = ["eventrelay", "local-corpus", "memory", "video-agents", "avatars", "data-models", "learn-runtime"];
let jobs = [];
for f in families {
    let pr = "Cited inventory brief for UVAI landscape family ";
    pr += f;
    pr += ". Use read_file, list_dir, grep, web_search, web_fetch. Do not invent APIs.";
    pr += " Always read /Users/garvey/Dev/EventRelay/docs/landscape/WATERFALL.md first.";
    pr += " EventRelay root is /Users/garvey/Dev/EventRelay — cite real files under apps/web or docs.";
    pr += " local-corpus: /Users/garvey/.uvai /Users/garvey/Dev /Users/garvey/video-intelligence-workbench /Users/garvey/YOUTUBE-EXTENSION /Users/garvey/.eventrelay.";
    pr += " memory: /Users/garvey/BrainVault (Obsidian) and Notion pages UVAI EventRelay Research SSOT and EventRelay Live Launch Board.";
    pr += " video-agents: https://visionagents.ai/introduction/quickstart https://getstream.io/video/ https://inworld.ai/ and GitHub GetStream/vision-agents.";
    pr += " avatars: https://anam.ai/interactive-avatars.";
    pr += " data-models: huggingface.co/datasets/facebook/S-EMBER VidaForge/VidaForge-3M NousResearch/Hermes-3-Llama-3.1-8B.";
    pr += " learn-runtime: github.com/karpathy/build-nanogpt docs.ml5js.org neural-network chromium audio_thread.h browser_main_loop.cc genkit youtube summarize qualiastudios.dev.";
    pr += " If a path or URL is missing, record MISSING in visited. Each facts[] item must contain a path or URL. Family field must equal ";
    pr += f;
    pr += ".";
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
    if r != () && r.success && r.output.family != () {
        briefs.push(r.output);
    } else {
        log("inventory slot failed or empty: " + families[i]);
    }
    i += 1;
}
log(briefs.len().to_string() + "/" + families.len().to_string() + " families produced briefs");

if mode != "full" {
    let inv_path = write_scratch_file("inventory.json", json_encode(briefs));
    complete(#{ path: inv_path, count: briefs.len(), mode: mode });
}

phase("Propose");
let encoded = json_encode(briefs);
let pp = "You are proposing a folder structure for UVAI/EventRelay AFTER reading inventory briefs.";
pp += " Use read_file on /Users/garvey/Dev/EventRelay/apps/web and docs/WORKFLOW_DEVKIT.md.";
pp += " Do not create a second monorepo or coordinator framework. Prefer keep existing EventRelay layout.";
pp += " Inventory JSON follows. Only use what is in it plus files you read:\n";
pp += encoded;
pp += "\nReturn keep/adapt/ignore (EventRelay paths), proposed_top_level (new dirs only if L1 adapt requires them), rationale.";

let prop = agent(pp, #{
    label: "propose-structure",
    capability_mode: "read-only",
    output_schema: propose_schema,
});

if prop == () || !prop.success {
    complete(#{ summary: "proposal failed closed", count: briefs.len() });
}

let sk = "Adversarially refute this proposed structure. Read EventRelay apps/ and the proposal.";
sk += " Set keep to dirs that already exist and should stay. Call out over-build.";
sk += " Proposal JSON:\n";
sk += json_encode(prop.output);
let skeptic = agent(sk, #{
    label: "skeptic",
    capability_mode: "read-only",
    output_schema: propose_schema,
});

let out_path = write_scratch_file("proposal.json", json_encode(#{
    inventory_count: briefs.len(),
    proposal: prop.output,
    skeptic: if skeptic != () && skeptic.success { skeptic.output } else { () },
}));
complete(#{ path: out_path, count: briefs.len(), mode: mode });
