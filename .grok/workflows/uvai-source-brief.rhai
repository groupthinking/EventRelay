let meta = #{
    name: "uvai-source-brief",
    description: "Read-only brief of one UVAI landscape source family with citations",
    when_to_use: "Inventory one local path or external URL family before comparing to EventRelay",
    phases: [
        #{ title: "Brief", detail: "read the named source, write a cited brief" },
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

let family = if args == () { () } else { args.family };
if family == () {
    pause("verification", "Pass args.family — one of eventrelay, local-corpus, memory, video-agents, avatars, data-models, learn-runtime");
}

phase("Brief");
let p = "Write a cited inventory brief for UVAI landscape family: ";
p += family;
p += ". Use read_file, list_dir, grep, web_search, or web_fetch as needed. Do not invent APIs.";
p += " Compare overlap to EventRelay at /Users/garvey/Dev/EventRelay (read apps/web/src and docs/WORKFLOW_DEVKIT.md).";
p += " Family paths: eventrelay=GitHub groupthinking/EventRelay plus this repo;";
p += " local-corpus=/Users/garvey/.uvai /Users/garvey/Dev /Users/garvey/video-intelligence-workbench /Users/garvey/YOUTUBE-EXTENSION /Users/garvey/.eventrelay;";
p += " memory=/Users/garvey/BrainVault and Notion UVAI EventRelay SSOT;";
p += " video-agents=https://visionagents.ai/introduction/quickstart https://getstream.io/video/ https://inworld.ai/ GetStream/vision-agents;";
p += " avatars=https://anam.ai/interactive-avatars;";
p += " data-models=huggingface facebook/S-EMBER VidaForge/VidaForge-3M NousResearch/Hermes-3-Llama-3.1-8B;";
p += " learn-runtime=karpathy/build-nanogpt ml5 neural-network chromium audio_thread.h browser_main_loop.cc genkit summarize-youtube-videos qualiastudios.dev.";
p += " If a path is missing or a URL fails, list it in visited as MISSING/FAILED and continue.";
p += " facts must include a path or URL in each string. Empty facts only after you actually listed the directories or fetched the pages.";

let r = agent(p, #{
    label: "brief",
    capability_mode: "read-only",
    output_schema: brief_schema,
});

if r == () || !r.success || r.output.family == () {
    complete(#{ summary: "brief failed closed", family: family });
}
let path = write_scratch_file("brief.md", json_encode(r.output));
complete(#{ path: path, brief: r.output });
