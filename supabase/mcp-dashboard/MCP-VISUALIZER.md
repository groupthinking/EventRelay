# MCP Context Visualizer

The MCP Context Visualizer is a powerful tool for visualizing and analyzing Model Context Protocol (MCP) data flows within your application. It enables developers to understand complex context relationships, track context lineage, and gain insights into how data moves through the MCP framework.

## Features

- **Interactive Graph Visualization**: View context relationships as an interactive network graph
- **Context Analytics**: Analyze patterns and statistics of your MCP contexts
- **Import/Export**: Save and load contexts to/from JSON files
- **Seamless Integration**: Works with the MCP Orchestrator out of the box
- **Rich Filtering**: Find contexts by source, operation, or other attributes

## Installation

The MCP Context Visualizer is included in the core MCP Framework package. No additional installation is required.

## Usage

### Basic Usage

```javascript
const { MCPContextVisualizer } = require('./mcp-context-visualizer');

// Create a new visualizer
const visualizer = new MCPContextVisualizer();

// Add contexts
visualizer.addContext({
  context_id: 'my-context-1',
  operation: 'extract',
  parameters: { source: 'claude' },
  result: { /* context data */ }
});

// Generate visualization
visualizer.generateHtmlVisualization('mcp-visualization.html');

// Analyze contexts
const analytics = visualizer.analyzeContexts();
console.log(analytics);
```

### Integration with MCP Orchestrator

The visualizer integrates seamlessly with the MCP Orchestrator:

```javascript
const { MCPOrchestrator } = require('./mcp-orchestrator');

// Create an orchestrator with visualization enabled
const orchestrator = new MCPOrchestrator({ visualize: true });

// Extract data
await orchestrator.extract('claude', { conversationId: 'my-conversation' });
await orchestrator.extract('github', { repoPath: 'user/repo' });

// Generate visualization from the orchestrator
const path = require('path');
const outputPath = path.join(__dirname, 'mcp-visualization.html');
orchestrator.generateVisualization(outputPath);

// Analyze contexts
const analytics = orchestrator.analyzeContexts();
console.log(analytics);
```

### Importing Existing Contexts

```javascript
// Import from orchestrator
visualizer.importFromOrchestrator(orchestrator);

// Import from file
visualizer.loadFromFile('contexts.json');
```

### Exporting Contexts

```javascript
// Save to file
visualizer.saveToFile('contexts.json');
```

## Visualization

The HTML visualization provides:

1. **Interactive Graph**: A network graph showing relationships between contexts
2. **Context Details**: Expandable cards with full context information
3. **Color Coding**: Contexts are colored by source for easy identification
4. **Selection**: Click on nodes to highlight the corresponding context details

## Analytics

The analytics feature provides insights such as:

- Total number of contexts
- Breakdown by source and operation
- Time range of context creation
- Most connected contexts
- Orphaned contexts (not referenced by any other context)

Example analytics output:

```json
{
  "totalContexts": 15,
  "sourceBreakdown": {
    "claude": 7,
    "github": 5,
    "cursor": 3
  },
  "operationBreakdown": {
    "extract": 12,
    "combine": 3
  },
  "timeRange": {
    "start": "2023-05-15T10:23:45.123Z",
    "end": "2023-05-15T11:45:12.431Z",
    "durationMs": 4887308
  },
  "mostConnectedContexts": [
    ["claude-conv1-123", 5],
    ["github-repo1-456", 3]
  ],
  "contextRelationships": 8,
  "orphanedContexts": 2
}
```

## API Reference

### Constructor

```javascript
const visualizer = new MCPContextVisualizer(config);
```

- `config` (optional): Configuration object

### Methods

| Method | Description |
|--------|-------------|
| `addContext(context)` | Add a context to the visualizer |
| `importFromOrchestrator(orchestrator)` | Import contexts from an MCP Orchestrator |
| `loadFromFile(filePath)` | Load contexts from a JSON file |
| `saveToFile(filePath)` | Save contexts to a JSON file |
| `generateContextGraph()` | Generate a graph representation of context relationships |
| `generateHtmlVisualization(outputPath)` | Generate an HTML visualization of context data |
| `analyzeContexts()` | Analyze context data for insights |
| `getContexts()` | Get all contexts |
| `findContextsBySource(source)` | Find contexts by source |
| `findContextsByOperation(operation)` | Find contexts by operation |
| `clearContexts()` | Clear all stored contexts |

## Example Visualization

When you open the generated HTML file in a browser, you'll see a visualization similar to this:

```
+---------------------------------------------------+--------------------------------+
|                                                   |                                |
|                                                   |  MCP Context Visualization     |
|                                                   |                                |
|                                                   |  Total Contexts: 15            |
|                                                   |                                |
|                    [claude]                       |  +------------------------+    |
|                        |                          |  | extract - claude       |    |
|                        v                          |  +------------------------+    |
|                    [github]----+                  |                                |
|                        |       |                  |  +------------------------+    |
|                        v       |                  |  | extract - github       |    |
|                   [combine]<---+                  |  +------------------------+    |
|                                                   |                                |
|                                                   |  +------------------------+    |
|                                                   |  | combine - orchestrator |    |
|                                                   |  | {                      |    |
|                                                   |  |   "context_id": "...", |    |
|                                                   |  |   ...                  |    |
|                                                   |  | }                      |    |
|                                                   |  +------------------------+    |
|                                                   |                                |
+---------------------------------------------------+--------------------------------+
```

## Use Cases

1. **Debugging MCP Flows**: Visualize how contexts are created and combined
2. **Documentation**: Generate visualizations for documentation and presentations
3. **Performance Analysis**: Analyze context patterns to optimize data flow
4. **Monitoring**: Track context generation and usage over time
5. **Auditing**: Review context lineage for security and compliance

## Next Steps

- **Real-time Updates**: Add WebSocket support for live context visualization
- **Search & Filter**: Add advanced search and filtering capabilities
- **Timeline View**: Add a chronological view of context creation and modification
- **Context Diff**: Compare different versions of the same context
- **Export Formats**: Support additional visualization formats (SVG, PNG)

## Advanced Visualization Features

The MCP Context Visualizer now includes several advanced features to help users explore and analyze their context data:

### Natural Language Analysis

- **Automatic Summarization**: Convert technical context data into human-readable summaries
- **Relationship Analysis**: Natural language descriptions of how different contexts relate to each other
- **Recommendations**: Smart suggestions for further exploration based on the current view

### Enhanced Filtering

- **Source Filtering**: Quick filtering by source type (Claude, GitHub, Cursor, etc.)
- **Custom Filters**: Input any custom filter term to find specific contexts
- **Search Highlighting**: Visual highlighting of search terms in context data

### Interactive Elements

- **Dynamic Graph Updates**: Graph visualization updates in real-time with filtering
- **Highlighted Relationships**: See connections between related contexts
- **Custom Data Visualization**: Support for custom visualization of specific context types

### Usage

To use these advanced features:

1. **Search**: Enter terms, ideas, or phrases in the search bar to filter contexts
2. **Filter Dropdown**: Select a specific source or choose "Custom Filter" for more options
3. **Analyze Button**: Click "Analyze in Natural Language" to generate insights about your current view
4. **Custom Filters**: When "Custom Filter" is selected, enter any text to search by content

These features are designed to make the exploration of complex MCP context data more intuitive and insightful.
