import express from 'express';
import { WebSocketServer } from 'ws';
import { watch } from 'chokidar';
import { readFileSync, existsSync, mkdirSync, appendFileSync, readdirSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { homedir } from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = 3000;

// Serve static files
app.use(express.static('public'));

// Start HTTP server
const server = app.listen(PORT, () => {
  console.log(`\n🚀 Universal Automation Service Monitor running at http://localhost:${PORT}`);
  console.log(`📊 Monitoring pipeline: YouTube → EventRelay → UVAI → Executor`);
  console.log(`📈 Monitoring events in: ${join(__dirname, '..', 'events')}\n`);
});

// WebSocket server
const wss = new WebSocketServer({ server });

// Store connected clients
const clients = new Set();

// Event log directory (parent directory)
const eventsDir = join(__dirname, '..', 'events');
if (!existsSync(eventsDir)) {
  mkdirSync(eventsDir, { recursive: true });
}

const eventLogPath = join(eventsDir, 'pipeline-events.jsonl');

// Initialize event log if it doesn't exist
if (!existsSync(eventLogPath)) {
  appendFileSync(eventLogPath, '');
}

// Broadcast to all connected clients
function broadcast(data) {
  const message = JSON.stringify(data);
  clients.forEach(client => {
    if (client.readyState === 1) { // WebSocket.OPEN
      client.send(message);
    }
  });
}

// Log and broadcast event
function logEvent(eventType, payload) {
  const event = {
    eventId: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    eventType,
    timestamp: Date.now(),
    source: 'claude-skill-monitor',
    payload
  };

  // Append to event log
  appendFileSync(eventLogPath, JSON.stringify(event) + '\n');

  // Broadcast to clients
  broadcast({ type: 'event', data: event });

  return event;
}

// Watch skills directory for changes
const skillsDir = join(homedir(), '.claude/skills');
if (existsSync(skillsDir)) {
  const watcher = watch(skillsDir, {
    persistent: true,
    ignoreInitial: false
  });

  watcher
    .on('add', path => {
      logEvent('skill.file.added', { path, filename: path.split('/').pop() });
    })
    .on('change', path => {
      logEvent('skill.file.changed', { path, filename: path.split('/').pop() });
    })
    .on('unlink', path => {
      logEvent('skill.file.removed', { path, filename: path.split('/').pop() });
    });
}

// Get all skills
function getAllSkills() {
  const skills = [];
  if (!existsSync(skillsDir)) return skills;

  try {
    const entries = readdirSync(skillsDir);

    entries.forEach(entry => {
      const skillPath = join(skillsDir, entry);
      const stat = statSync(skillPath);

      if (stat.isDirectory()) {
        const skillMdPath = join(skillPath, 'SKILL.md');
        if (existsSync(skillMdPath)) {
          const content = readFileSync(skillMdPath, 'utf-8');
          const lines = content.split('\n');
          const title = lines[0]?.replace(/^#\s*/, '').trim() || entry;
          const description = lines.find(l => l.startsWith('## Description'))
            ? lines[lines.indexOf(lines.find(l => l.startsWith('## Description'))) + 1]?.trim()
            : 'No description';

          skills.push({
            name: entry,
            title,
            description,
            path: skillPath,
            lastModified: stat.mtime
          });
        }
      }
    });
  } catch (err) {
    console.error('Error reading skills:', err);
  }

  return skills;
}

// API endpoints
app.get('/api/skills', (req, res) => {
  const skills = getAllSkills();
  res.json(skills);
});

app.get('/api/events', (req, res) => {
  try {
    const events = readFileSync(eventLogPath, 'utf-8')
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line))
      .slice(-100); // Last 100 events

    res.json(events);
  } catch (err) {
    res.json([]);
  }
});

app.get('/api/metrics', (req, res) => {
  try {
    const events = readFileSync(eventLogPath, 'utf-8')
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line));

    const metrics = {
      totalEvents: events.length,
      eventsByType: events.reduce((acc, e) => {
        acc[e.eventType] = (acc[e.eventType] || 0) + 1;
        return acc;
      }, {}),
      lastEvent: events[events.length - 1] || null,
      uptime: process.uptime()
    };

    res.json(metrics);
  } catch (err) {
    res.json({
      totalEvents: 0,
      eventsByType: {},
      lastEvent: null,
      uptime: process.uptime()
    });
  }
});

// WebSocket connection handler
wss.on('connection', (ws) => {
  console.log('📱 Client connected');
  clients.add(ws);

  // Send initial data
  ws.send(JSON.stringify({
    type: 'connected',
    data: {
      skills: getAllSkills(),
      message: 'Connected to Claude Skill Monitor'
    }
  }));

  // Log connection event
  logEvent('client.connected', { totalClients: clients.size });

  ws.on('close', () => {
    console.log('📱 Client disconnected');
    clients.delete(ws);
    logEvent('client.disconnected', { totalClients: clients.size });
  });

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);

      if (data.type === 'skill.invoked') {
        logEvent('skill.invoked', data.payload);
      } else if (data.type === 'task.status') {
        logEvent('task.status.changed', data.payload);
      } else if (data.type === 'pipeline.event') {
        logEvent('pipeline.event.received', data.payload);
      } else if (data.type === 'workflow.update') {
        logEvent('workflow.update.received', data.payload);
      }
    } catch (err) {
      console.error('Error processing message:', err);
    }
  });
});

// Workflow phase tracking
let currentPhase = 'Phase3';

// Function to update workflow phase (called programmatically)
export function updateWorkflowPhase(newPhase, details = {}) {
  currentPhase = newPhase;
  logEvent('workflow.phase.changed', {
    phase: newPhase,
    ...details,
    timestamp: Date.now()
  });
  console.log(`📊 Workflow phase changed to: ${newPhase}`);
}

console.log('✅ Universal Automation Service monitoring active');
console.log('📺 Ready to process YouTube URLs through pipeline');
