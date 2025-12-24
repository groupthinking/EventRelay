#!/usr/bin/env node

/**
 * Git Workflow MCP Server
 * ------------------------
 * Provides controlled access to common git commands (status/add/commit/push/pull)
 * through the Model Context Protocol so agents can manage repository state safely.
 */

import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { Server } from '@modelcontextprotocol/sdk/server';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ErrorCode,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';

const WORKSPACE_ROOT = process.env.GIT_WORKSPACE_ROOT
  ? path.resolve(process.env.GIT_WORKSPACE_ROOT)
  : process.cwd();

if (!fs.existsSync(WORKSPACE_ROOT)) {
  console.error(`Error: Workspace root ${WORKSPACE_ROOT} does not exist.`);
  process.exit(1);
}

function runGitCommand(args, { allowEmpty = false } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn('git', args, {
      cwd: WORKSPACE_ROOT,
      env: process.env,
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', (error) => {
      reject(error);
    });

    child.on('close', (code) => {
      if (code === 0 || (allowEmpty && code === 1 && !stdout && !stderr)) {
        resolve({ stdout: stdout.trim(), stderr: stderr.trim(), code });
      } else {
        reject(new Error(stderr.trim() || stdout.trim() || `git ${args.join(' ')} failed with code ${code}`));
      }
    });
  });
}

async function gitStatus({ porcelain = true } = {}) {
  const args = porcelain ? ['status', '--short', '--branch'] : ['status'];
  return runGitCommand(args);
}

async function gitAdd({ files }) {
  if (!Array.isArray(files) || files.length === 0) {
    throw new Error('git_add requires a non-empty "files" array');
  }
  const normalized = files.map((file) => (file === '.' ? '.' : path.normalize(file)));
  return runGitCommand(['add', ...normalized]);
}

async function gitCommit({ message, allowEmpty = false }) {
  if (!message || typeof message !== 'string') {
    throw new Error('git_commit requires a commit "message"');
  }
  const args = ['commit', '-m', message];
  if (allowEmpty) {
    args.push('--allow-empty');
  }
  return runGitCommand(args);
}

async function gitPush({ remote, branch, force = false } = {}) {
  const targetRemote = remote || process.env.GIT_DEFAULT_REMOTE || 'origin';
  const args = ['push', targetRemote];
  if (branch && branch.length > 0) {
    args.push(branch);
  }
  if (force) {
    args.push('--force-with-lease');
  }
  return runGitCommand(args);
}

async function gitPull({ remote, branch, rebase = false } = {}) {
  const targetRemote = remote || process.env.GIT_DEFAULT_REMOTE || 'origin';
  const args = ['pull', targetRemote];
  if (branch && branch.length > 0) {
    args.push(branch);
  }
  if (rebase) {
    args.push('--rebase');
  }
  return runGitCommand(args);
}

async function gitDiff({ pathspec, staged = false } = {}) {
  const args = ['diff'];
  if (staged) {
    args.push('--staged');
  }
  if (pathspec && pathspec.length > 0) {
    args.push('--', pathspec);
  }
  return runGitCommand(args);
}

class GitWorkflowMCPServer {
  constructor() {
    this.server = new Server(
      { name: 'git-workflow-mcp', version: '1.0.0' },
      { capabilities: { tools: {} } }
    );

    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'git_status',
          description: 'Show current repository status (defaults to porcelain output).',
          inputSchema: {
            type: 'object',
            properties: {
              porcelain: { type: 'boolean', description: 'Return condensed status output', default: true },
            },
          },
        },
        {
          name: 'git_diff',
          description: 'Show git diff (optionally staged or limited to a path).',
          inputSchema: {
            type: 'object',
            properties: {
              staged: { type: 'boolean', description: 'Show staged changes only', default: false },
              pathspec: { type: 'string', description: 'Optional path filter (relative to repo root)' },
            },
          },
        },
        {
          name: 'git_add',
          description: 'Run git add for the specified files.',
          inputSchema: {
            type: 'object',
            properties: {
              files: {
                type: 'array',
                items: { type: 'string' },
                description: 'List of files or patterns to add (relative paths or ".")',
              },
            },
            required: ['files'],
          },
        },
        {
          name: 'git_commit',
          description: 'Create a git commit with the provided message.',
          inputSchema: {
            type: 'object',
            properties: {
              message: { type: 'string', description: 'Commit message' },
              allowEmpty: { type: 'boolean', description: 'Allow empty commits', default: false },
            },
            required: ['message'],
          },
        },
        {
          name: 'git_push',
          description: 'Push commits to a remote.',
          inputSchema: {
            type: 'object',
            properties: {
              remote: { type: 'string', description: 'Remote name (default origin)' },
              branch: { type: 'string', description: 'Branch name (defaults to current HEAD)' },
              force: { type: 'boolean', description: 'Use --force-with-lease', default: false },
            },
          },
        },
        {
          name: 'git_pull',
          description: 'Pull latest changes from a remote.',
          inputSchema: {
            type: 'object',
            properties: {
              remote: { type: 'string', description: 'Remote name (default origin)' },
              branch: { type: 'string', description: 'Branch name (default tracked branch)' },
              rebase: { type: 'boolean', description: 'Rebase instead of merge', default: false },
            },
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args = {} } = request.params;

      try {
        let result;
        switch (name) {
          case 'git_status':
            result = await gitStatus(args);
            break;
          case 'git_diff':
            result = await gitDiff(args);
            break;
          case 'git_add':
            result = await gitAdd(args);
            break;
          case 'git_commit':
            result = await gitCommit(args);
            break;
          case 'git_push':
            result = await gitPush(args);
            break;
          case 'git_pull':
            result = await gitPull(args);
            break;
          default:
            throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
        }

        const message = [result.stdout, result.stderr].filter(Boolean).join('\n');
        return {
          content: [
            {
              type: 'text',
              text: message || `${name} completed successfully`,
            },
          ],
        };
      } catch (error) {
        return {
          isError: true,
          content: [
            {
              type: 'text',
              text: `Error running ${name}: ${error.message}`,
            },
          ],
        };
      }
    });

    this.server.onerror = (error) => {
      console.error('[Git Workflow MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error(`git-workflow-mcp server running in ${WORKSPACE_ROOT}`);
  }
}

const server = new GitWorkflowMCPServer();
server.run().catch((error) => {
  console.error('Failed to start git-workflow-mcp server:', error);
  process.exit(1);
});
