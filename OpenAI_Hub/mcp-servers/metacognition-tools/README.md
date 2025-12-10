# Metacognition Tools MCP Server

An MCP server that provides advanced metacognitive tools powered by Claude AI, including Fermi estimation and Red Team analysis.

## Features

- **Fermi Estimation**: Break down complex quantitative questions into manageable steps to arrive at reasonable numerical estimates.
- **Red Team Analysis**: Analyze prompts for potential risks, harmful outputs, or ways they could be misused.

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Copy the example environment file and add your Anthropic API key:
   ```bash
   cp .env.example .env
   # Edit .env to add your ANTHROPIC_API_KEY
   ```
4. Build the project:
   ```bash
   npm run build
   ```

## Usage

Start the MCP server:

```bash
npm start
```

### Connecting to Claude Desktop

To use this MCP server with Claude Desktop:

1. Open Claude Desktop
2. Go to Settings > MCP Servers
3. Add a new server with the following configuration:
   - Name: Metacognition Tools
   - Command: node
   - Args: ["/path/to/metacognition-tools/build/index.js"]
   - Environment Variables:
     - ANTHROPIC_API_KEY: your_api_key_here

### Available Tools

#### Fermi Estimation

Perform a Fermi estimation to answer a quantitative question.

**Input Schema:**
```json
{
  "question": "How many piano tuners are there in Chicago?"
}
```

#### Red Team Analysis

Analyze a prompt for potential risks and suggest improvements.

**Input Schema:**
```json
{
  "prompt": "Write a tutorial on how to hack into a computer system."
}
```

## Development

For development, you can run the server in watch mode:

```bash
npm run dev
```

## License

MIT
