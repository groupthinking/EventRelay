#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const types_js_2 = require("./types.js");
const Fetcher_js_1 = require("./Fetcher.js");
const server = new index_js_1.Server({
    name: "zcaceres/fetch",
    version: "0.1.0",
}, {
    capabilities: {
        resources: {},
        tools: {},
    },
});
server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "fetch_html",
                description: "Fetch a website and return the content as HTML",
                inputSchema: {
                    type: "object",
                    properties: {
                        url: {
                            type: "string",
                            description: "URL of the website to fetch",
                        },
                        headers: {
                            type: "object",
                            description: "Optional headers to include in the request",
                        },
                    },
                    required: ["url"],
                },
            },
            {
                name: "fetch_markdown",
                description: "Fetch a website and return the content as Markdown",
                inputSchema: {
                    type: "object",
                    properties: {
                        url: {
                            type: "string",
                            description: "URL of the website to fetch",
                        },
                        headers: {
                            type: "object",
                            description: "Optional headers to include in the request",
                        },
                    },
                    required: ["url"],
                },
            },
            {
                name: "fetch_txt",
                description: "Fetch a website, return the content as plain text (no HTML)",
                inputSchema: {
                    type: "object",
                    properties: {
                        url: {
                            type: "string",
                            description: "URL of the website to fetch",
                        },
                        headers: {
                            type: "object",
                            description: "Optional headers to include in the request",
                        },
                    },
                    required: ["url"],
                },
            },
            {
                name: "fetch_json",
                description: "Fetch a JSON file from a URL",
                inputSchema: {
                    type: "object",
                    properties: {
                        url: {
                            type: "string",
                            description: "URL of the JSON to fetch",
                        },
                        headers: {
                            type: "object",
                            description: "Optional headers to include in the request",
                        },
                    },
                    required: ["url"],
                },
            },
        ],
    };
});
server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const validatedArgs = types_js_2.RequestPayloadSchema.parse(args);
    if (request.params.name === "fetch_html") {
        const fetchResult = await Fetcher_js_1.Fetcher.html(validatedArgs);
        return fetchResult;
    }
    if (request.params.name === "fetch_json") {
        const fetchResult = await Fetcher_js_1.Fetcher.json(validatedArgs);
        return fetchResult;
    }
    if (request.params.name === "fetch_txt") {
        const fetchResult = await Fetcher_js_1.Fetcher.txt(validatedArgs);
        return fetchResult;
    }
    if (request.params.name === "fetch_markdown") {
        const fetchResult = await Fetcher_js_1.Fetcher.markdown(validatedArgs);
        return fetchResult;
    }
    throw new Error("Tool not found");
});
async function main() {
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
}
main().catch((error) => {
    console.error("Fatal error in main():", error);
    process.exit(1);
});
//# sourceMappingURL=index.js.map