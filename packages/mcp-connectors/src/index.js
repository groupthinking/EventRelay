"use strict";
/**
 * MCP Connectors - Production-ready connectors for Postgres, GitHub, and Slack
 * @packageDocumentation
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SlackConnector = exports.GitHubConnector = exports.PostgresConnector = void 0;
var postgres_1 = require("./postgres");
Object.defineProperty(exports, "PostgresConnector", { enumerable: true, get: function () { return postgres_1.PostgresConnector; } });
var github_1 = require("./github");
Object.defineProperty(exports, "GitHubConnector", { enumerable: true, get: function () { return github_1.GitHubConnector; } });
var slack_1 = require("./slack");
Object.defineProperty(exports, "SlackConnector", { enumerable: true, get: function () { return slack_1.SlackConnector; } });
//# sourceMappingURL=index.js.map