# MCP Data Extraction Framework

This framework outlines how to extract data from multiple sources using the Model Context Protocol (MCP) pattern and your Edge Function.

## Architecture Overview

```
┌───────────────┐     ┌─────────────────┐     ┌────────────────┐
│  Data Sources │────▶│ MCP Extractors  │────▶│  MCP   │
└───────────────┘     └─────────────────┘     │ Edge Function  │
                                              └────────────────┘
                                                      │
                                                      ▼
                                              ┌────────────────┐
                                              │ MCP Database   │
                                              └────────────────┘
```

## Common Extraction Pattern

Each data source will follow this general pattern:

1. **Authentication** - Connect to the source API
2. **Discovery** - Find available data
3. **Extraction** - Pull data with context
4. **Transformation** - Convert to MCP format
5. **Transmission** - Send to MCP endpoint

## Source-Specific Implementation

### 1. Claude

```javascript
async function extractFromClaude(conversationId) {
  // 1. Authentication
  const anthropicClient = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY
  });
  
  // 2. Discovery & 3. Extraction 
  const messages = await anthropicClient.messages.list({
    conversationId: conversationId
  });
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `claude-${conversationId}`,
    operation: "extract",
    parameters: {
      source: "claude",
      conversationId: conversationId
    },
    result: {
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at
      }))
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 2. GitHub

```javascript
async function extractFromGitHub(repo, branch = 'main', path = '') {
  // 1. Authentication
  const octokit = new Octokit({ 
    auth: process.env.GITHUB_TOKEN 
  });
  
  // 2. Discovery
  const [owner, repoName] = repo.split('/');
  
  // 3. Extraction
  const { data: contents } = await octokit.repos.getContent({
    owner,
    repo: repoName,
    path,
    ref: branch
  });
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `github-${repo}-${branch}-${path}`.replace(/[^a-zA-Z0-9-]/g, '-'),
    operation: "extract",
    parameters: {
      source: "github",
      repo,
      branch,
      path
    },
    result: Array.isArray(contents) 
      ? { files: contents.map(file => ({ name: file.name, type: file.type, path: file.path })) }
      : { content: Buffer.from(contents.content, 'base64').toString('utf-8') },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 3. Cursor

```javascript
async function extractFromCursor(sessionId) {
  // 1. Authentication
  const cursorClient = new CursorAPI({
    apiKey: process.env.CURSOR_API_KEY
  });
  
  // 2. Discovery & 3. Extraction
  const sessionData = await cursorClient.sessions.get(sessionId);
  const codeContext = await cursorClient.context.getCodeContext(sessionId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `cursor-${sessionId}`,
    operation: "extract",
    parameters: {
      source: "cursor",
      sessionId
    },
    result: {
      session: {
        files: sessionData.files,
        currentFile: sessionData.currentFile,
        codeContext
      }
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 4. Replit

```javascript
async function extractFromReplit(replitId) {
  // 1. Authentication
  const replitClient = new ReplitGraphQL({
    apiKey: process.env.REPLIT_API_KEY
  });
  
  // 2. Discovery & 3. Extraction
  const { data } = await replitClient.query({
    query: `
      query GetRepl($id: String!) {
        repl(id: $id) {
          id
          title
          files {
            name
            content
            path
          }
        }
      }
    `,
    variables: { id: replitId }
  });
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `replit-${replitId}`,
    operation: "extract",
    parameters: {
      source: "replit",
      replitId
    },
    result: {
      repl: data.repl
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 5. Google Gemini

```javascript
async function extractFromGemini(chatId) {
  // 1. Authentication
  const { GoogleGenerativeAI } = require('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  
  // 2. Discovery & 3. Extraction
  const chatHistory = await genAI.getChatHistory(chatId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `gemini-${chatId}`,
    operation: "extract",
    parameters: {
      source: "gemini",
      chatId
    },
    result: {
      history: chatHistory.map(msg => ({
        role: msg.role,
        content: msg.parts.map(part => part.text).join(''),
        timestamp: msg.created
      }))
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 6. Google Drive

```javascript
async function extractFromGoogleDrive(fileId) {
  // 1. Authentication
  const { google } = require('googleapis');
  const auth = new google.auth.GoogleAuth({
    keyFile: 'credentials.json',
    scopes: ['https://www.googleapis.com/auth/drive.readonly']
  });
  const drive = google.drive({ version: 'v3', auth });
  
  // 2. Discovery & 3. Extraction
  const { data: metadata } = await drive.files.get({ fileId });
  const { data: content } = await drive.files.get({
    fileId,
    alt: 'media'
  });
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `gdrive-${fileId}`,
    operation: "extract",
    parameters: {
      source: "google_drive",
      fileId
    },
    result: {
      metadata,
      content: content.toString('utf-8')
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 7. iOS Notes

```javascript
// iOS Notes requires a local app or shortcuts integration
async function extractFromIOSNotes(noteId) {
  // 1. Authentication (using Shortcuts API/App)
  // This requires a Shortcuts integration on iOS
  
  // 2. Discovery & 3. Extraction
  // Create a shortcut that exports a note and sends to an API endpoint
  // For demonstration, we'll assume data is POSTed to our service
  
  // 4. Transformation to MCP (on our server receiving the shortcut data)
  function processNoteData(noteData) {
    const mcpContext = {
      context_id: `ios-notes-${noteData.id}`,
      operation: "extract",
      parameters: {
        source: "ios_notes",
        noteId: noteData.id
      },
      result: {
        title: noteData.title,
        content: noteData.text,
        created: noteData.created,
        modified: noteData.modified
      },
      metadata: {
        extractionTime: new Date().toISOString()
      }
    };
    
    // 5. Transmission to MCP endpoint
    return sendToMcpEndpoint(mcpContext);
  }
  
  // This would be called by your API endpoint receiving iOS Shortcut data
}
```

### 8. Craft

```javascript
async function extractFromCraft(documentId) {
  // 1. Authentication
  const craftClient = new CraftAPI({
    apiKey: process.env.CRAFT_API_KEY
  });
  
  // 2. Discovery & 3. Extraction
  const document = await craftClient.documents.get(documentId);
  const blocks = await craftClient.blocks.list(documentId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `craft-${documentId}`,
    operation: "extract",
    parameters: {
      source: "craft",
      documentId
    },
    result: {
      document: {
        title: document.title,
        blocks: blocks.map(block => ({
          id: block.id,
          type: block.type,
          content: block.content
        }))
      }
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 9. xAI

```javascript
async function extractFromXAI(conversationId) {
  // 1. Authentication
  const xAIClient = new XAIClient({
    apiKey: process.env.XAI_API_KEY
  });
  
  // 2. Discovery & 3. Extraction
  const conversation = await xAIClient.conversations.retrieve(conversationId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `xai-${conversationId}`,
    operation: "extract",
    parameters: {
      source: "xai",
      conversationId
    },
    result: {
      messages: conversation.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at
      }))
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 10. ChatGPT

```javascript
async function extractFromChatGPT(conversationId) {
  // 1. Authentication
  const { OpenAI } = require('openai');
  const openai = new OpenAI(process.env.OPENAI_API_KEY);
  
  // 2. Discovery & 3. Extraction
  // Note: Requires ChatGPT API access which might not be available
  // Alternative approach: use browser extension to extract data
  const messages = await openai.beta.threads.messages.list(conversationId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `chatgpt-${conversationId}`,
    operation: "extract",
    parameters: {
      source: "chatgpt",
      conversationId
    },
    result: {
      messages: messages.data.map(msg => ({
        role: msg.role,
        content: msg.content[0].text.value,
        timestamp: msg.created_at
      }))
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 11. Abacus.ai

```javascript
async function extractFromAbacusAI(projectId, modelId = null) {
  // 1. Authentication
  const abacusClient = new AbacusAPI({
    apiKey: process.env.ABACUS_API_KEY
  });
  
  // 2. Discovery
  const project = await abacusClient.projects.get(projectId);
  
  // 3. Extraction
  let data;
  if (modelId) {
    data = await abacusClient.models.get(modelId);
  } else {
    const models = await abacusClient.models.list({ 
      projectId, 
      limit: 10 
    });
    data = { project, models };
  }
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `abacus-${projectId}${modelId ? `-${modelId}` : ''}`,
    operation: "extract",
    parameters: {
      source: "abacus_ai",
      projectId,
      modelId
    },
    result: data,
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 12. LinkedIn

```javascript
async function extractFromLinkedIn(profileId) {
  // 1. Authentication
  // LinkedIn API access is restricted
  // Options: 
  // a) Use official Marketing API with proper permissions
  // b) Use browser extension to extract data
  // c) Use third-party service like Proxycurl
  
  // For this example, we'll use Proxycurl
  const response = await fetch(`https://nubela.co/proxycurl/api/v2/linkedin?url=https://www.linkedin.com/in/${profileId}`, {
    headers: {
      'Authorization': `Bearer ${process.env.PROXYCURL_API_KEY}`
    }
  });
  
  const profile = await response.json();
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `linkedin-${profileId}`,
    operation: "extract",
    parameters: {
      source: "linkedin",
      profileId
    },
    result: {
      profile: {
        name: profile.full_name,
        headline: profile.headline,
        summary: profile.summary,
        experiences: profile.experiences,
        education: profile.education
      }
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 13. Bear

```javascript
async function extractFromBear(noteId) {
  // 1. Authentication
  // Bear requires x-callback-url or using Bear's native app API
  // This requires a local Mac app integration
  
  // 2-3. Discovery & Extraction using AppleScript or x-callback-url
  // For demonstration, we'll use a hypothetical Node-AppleScript bridge
  
  const { runAppleScript } = require('node-applescript');
  
  const result = await runAppleScript(`
    tell application "Bear"
      set noteText to note with id "${noteId}"
      return {title:title of noteText, text:text of noteText, id:id of noteText}
    end tell
  `);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `bear-${noteId}`,
    operation: "extract",
    parameters: {
      source: "bear",
      noteId
    },
    result: {
      title: result.title,
      content: result.text,
      id: result.id
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 14. File Server

```javascript
async function extractFromFileServer(path, serverId = 'default') {
  // 1. Authentication
  const { readFile, stat } = require('fs/promises');
  const { join } = require('path');
  
  // Define the root directories for each server
  const serverRoots = {
    default: process.env.FILE_SERVER_ROOT || '/data/files',
    // Add other servers as needed
  };
  
  // 2. Discovery & 3. Extraction
  const fullPath = join(serverRoots[serverId], path);
  const fileStat = await stat(fullPath);
  
  let content;
  // Only read content for reasonable file sizes and text files
  if (fileStat.size < 10 * 1024 * 1024) { // 10MB limit
    content = await readFile(fullPath, 'utf-8');
  }
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `file-server-${serverId}-${path}`.replace(/[^a-zA-Z0-9-]/g, '-'),
    operation: "extract",
    parameters: {
      source: "file_server",
      serverId,
      path
    },
    result: {
      metadata: {
        size: fileStat.size,
        created: fileStat.birthtime,
        modified: fileStat.mtime,
        isDirectory: fileStat.isDirectory()
      },
      content: content || null
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

### 15. NotebookLLM

```javascript
async function extractFromNotebookLLM(notebookId) {
  // 1. Authentication
  const notebookClient = new NotebookLLMClient({
    apiKey: process.env.NOTEBOOK_LLM_API_KEY
  });
  
  // 2. Discovery & 3. Extraction
  const notebook = await notebookClient.notebooks.get(notebookId);
  const cells = await notebookClient.cells.list(notebookId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `notebook-llm-${notebookId}`,
    operation: "extract",
    parameters: {
      source: "notebook_llm",
      notebookId
    },
    result: {
      notebook: {
        title: notebook.title,
        cells: cells.map(cell => ({
          id: cell.id,
          type: cell.type, // code, markdown, etc.
          content: cell.content,
          outputs: cell.outputs
        }))
      }
    },
    metadata: {
      extractionTime: new Date().toISOString()
    }
  };
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}
```

## MCP Transmission Function

This central function handles sending data to your MCP endpoint:

```javascript
async function sendToMcpEndpoint(mcpContext) {
  // Define endpoint URL and API key
  const MCP_ENDPOINT = ';
  
  const response = await fetch(MCP_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${}$
    },
    body: JSON.stringify({
      modelId: 'mcp-extractor',
      context: mcpContext
    })
  });
  
  if (!response.ok) {
    throw new Error(`MCP endpoint error: ${response.status}`);
  }
  
  return await response.json();
}
```

## Integration Example

Here's an example of how to use the framework:

```javascript
// Example usage
async function main() {
  try {
    // Extract from GitHub
    const githubData = await extractFromGitHub('username/repo', 'main', 'src/');
    console.log('GitHub extraction complete:', githubData.context_id);
    
    // Extract from Cursor
    const cursorData = await extractFromCursor('session-123');
    console.log('Cursor extraction complete:', cursorData.context_id);
    
    // Extract from multiple sources and combine
    const [claude, github, cursor] = await Promise.all([
      extractFromClaude('conv-123'),
      extractFromGitHub('user/repo'),
      extractFromCursor('session-456')
    ]);
    
    // Create a combined context
    const combinedContext = {
      context_id: `combined-${Date.now()}`,
      operation: "combine",
      parameters: {
        sources: [claude.context_id, github.context_id, cursor.context_id]
      },
      result: {
        claude: claude.result,
        github: github.result,
        cursor: cursor.result
      },
      metadata: {
        extractionTime: new Date().toISOString()
      }
    };
    
    // Send combined context to MCP endpoint
    const combinedResult = await sendToMcpEndpoint(combinedContext);
    console.log('Combined extraction complete:', combinedResult.context_id);
    
  } catch (error) {
    console.error('Extraction error:', error);
  }
}
```

## Next Steps

1. **Authentication Management**: Implement secure storage for API keys
2. **Error Handling**: Add robust error handling and retries
3. **Caching**: Implement caching for frequent extractions
4. **Rate Limiting**: Add rate limiting to respect API limits
5. **UI**: Create an admin interface to trigger extractions
6. **Scheduling**: Set up scheduled extractions for important data
7. **Extensions**: Develop a browser extension for web-based sources
8. **Webhooks**: Implement webhooks to trigger extractions on events 