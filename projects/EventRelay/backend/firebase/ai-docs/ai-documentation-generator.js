/**
 * AI-Assisted Documentation Generator
 * Intelligent documentation generation using code analysis and NLP
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { EventEmitter } = require('events');

class AIDocumentationGenerator extends EventEmitter {
  constructor() {
    super();
    this.templates = new Map();
    this.patterns = new Map();
    this.context = new Map();
    this.isInitialized = false;

    this.config = this.loadConfig();
    this.nlp = new NaturalLanguageProcessor();
    this.codeAnalyzer = new CodeAnalyzer();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'ai-docs-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    return {
      enabled: true,
      autoGenerate: true,
      updateOnChanges: true,
      templates: {
        component: './ai-docs/templates/component.md',
        service: './ai-docs/templates/service.md',
        api: './ai-docs/templates/api.md',
        module: './ai-docs/templates/module.md'
      },
      analysis: {
        depth: 'deep',
        includeDependencies: true,
        generateDiagrams: true,
        extractComments: true
      },
      quality: {
        minConfidence: 0.7,
        reviewThreshold: 0.8,
        autoApprove: false
      }
    };
  }

  /**
   * Initialize the AI documentation generator
   */
  async initialize() {
    if (this.isInitialized) return;

    console.log('🤖 Initializing AI Documentation Generator...');

    try {
      // Load templates
      await this.loadTemplates();

      // Load analysis patterns
      await this.loadPatterns();

      // Initialize NLP processor
      await this.nlp.initialize();

      // Initialize code analyzer
      await this.codeAnalyzer.initialize();

      this.isInitialized = true;
      console.log('✅ AI Documentation Generator initialized');

      this.emit('initialized');
    } catch (error) {
      console.error('❌ Failed to initialize AI Documentation Generator:', error.message);
      throw error;
    }
  }

  /**
   * Load documentation templates
   */
  async loadTemplates() {
    console.log('📄 Loading documentation templates...');

    for (const [type, templatePath] of Object.entries(this.config.templates)) {
      const fullPath = path.join(__dirname, '..', templatePath);

      if (fs.existsSync(fullPath)) {
        const template = fs.readFileSync(fullPath, 'utf8');
        this.templates.set(type, template);
        console.log(`✅ Loaded ${type} template`);
      } else {
        console.warn(`⚠️  Template not found: ${fullPath}`);
      }
    }
  }

  /**
   * Load analysis patterns
   */
  async loadPatterns() {
    console.log('🔍 Loading analysis patterns...');

    this.patterns.set('function', {
      regex: /function\s+(\w+)\s*\(([^)]*)\)/g,
      extract: (match) => ({
        type: 'function',
        name: match[1],
        params: match[2].split(',').map(p => p.trim()).filter(p => p),
        complexity: this.estimateComplexity(match[2])
      })
    });

    this.patterns.set('class', {
      regex: /class\s+(\w+)(?:\s+extends\s+(\w+))?/g,
      extract: (match) => ({
        type: 'class',
        name: match[1],
        extends: match[2] || null,
        methods: [],
        properties: []
      })
    });

    this.patterns.set('component', {
      regex: /(?:export\s+)?(?:const|function)\s+(\w+)\s*(?:\([^)]*\))?\s*{/g,
      extract: (match) => ({
        type: 'component',
        name: match[1],
        props: [],
        state: [],
        methods: []
      })
    });

    console.log('✅ Analysis patterns loaded');
  }

  /**
   * Analyze codebase and generate documentation
   */
  async analyzeAndGenerate(sourcePath = './src', outputPath = './Docs') {
    console.log('🔍 Starting AI-powered code analysis...');

    const analysis = await this.codeAnalyzer.analyze(sourcePath);
    const documentation = await this.generateDocumentation(analysis);

    // Save generated documentation
    await this.saveDocumentation(documentation, outputPath);

    // Generate quality report
    const qualityReport = await this.generateQualityReport(documentation);

    console.log('✅ Documentation generation completed');
    console.log(`📄 Generated ${documentation.length} documentation files`);

    this.emit('documentationGenerated', { documentation, qualityReport });
    return { documentation, qualityReport };
  }

  /**
   * Generate documentation from analysis
   */
  async generateDocumentation(analysis) {
    const documentation = [];

    for (const file of analysis.files) {
      try {
        const fileDocs = await this.generateFileDocumentation(file);
        if (fileDocs) {
          documentation.push(fileDocs);
        }
      } catch (error) {
        console.warn(`⚠️  Failed to generate docs for ${file.path}:`, error.message);
      }
    }

    // Generate module-level documentation
    const moduleDocs = await this.generateModuleDocumentation(analysis);
    documentation.push(...moduleDocs);

    // Generate architectural documentation
    const archDocs = await this.generateArchitectureDocumentation(analysis);
    documentation.push(archDocs);

    return documentation;
  }

  /**
   * Generate documentation for a single file
   */
  async generateFileDocumentation(file) {
    const fileType = this.determineFileType(file);
    const template = this.templates.get(fileType);

    if (!template) {
      console.warn(`⚠️  No template found for file type: ${fileType}`);
      return null;
    }

    // Extract code entities
    const entities = await this.extractCodeEntities(file);

    // Generate natural language descriptions
    const descriptions = await this.nlp.generateDescriptions(entities);

    // Generate documentation using template
    const documentation = this.renderTemplate(template, {
      file: file,
      entities: entities,
      descriptions: descriptions,
      metadata: {
        generated: new Date().toISOString(),
        generator: 'AI Documentation Generator',
        confidence: this.calculateConfidence(entities, descriptions)
      }
    });

    return {
      type: 'file',
      path: file.path,
      content: documentation,
      metadata: {
        fileType: fileType,
        entities: entities.length,
        quality: this.assessQuality(documentation)
      }
    };
  }

  /**
   * Determine file type based on content and path
   */
  determineFileType(file) {
    const ext = path.extname(file.path).toLowerCase();
    const content = file.content;

    // JavaScript/TypeScript files
    if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) {
      if (content.includes('React') || content.includes('Component')) {
        return 'component';
      }
      if (content.includes('class') && content.includes('extends')) {
        return 'service';
      }
      if (content.includes('router') || content.includes('app.')) {
        return 'module';
      }
      return 'service';
    }

    return 'module';
  }

  /**
   * Extract code entities from file
   */
  async extractCodeEntities(file) {
    const entities = [];
    const content = file.content;

    for (const [patternName, pattern] of this.patterns) {
      let match;
      while ((match = pattern.regex.exec(content)) !== null) {
        const entity = pattern.extract(match);
        if (entity) {
          // Extract additional context
          entity.context = this.extractContext(content, match.index);
          entity.comments = this.extractComments(content, match.index);
          entity.dependencies = this.extractDependencies(content, entity.name);

          entities.push(entity);
        }
      }
    }

    return entities;
  }

  /**
   * Extract context around a code entity
   */
  extractContext(content, position, radius = 100) {
    const start = Math.max(0, position - radius);
    const end = Math.min(content.length, position + radius);
    return content.substring(start, end);
  }

  /**
   * Extract comments related to a code entity
   */
  extractComments(content, position) {
    const lines = content.substring(0, position).split('\n');
    const comments = [];

    // Look for JSDoc comments above the entity
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();

      if (line.startsWith('/**')) {
        // Found start of JSDoc comment
        const commentLines = [];
        for (let j = i; j < lines.length; j++) {
          commentLines.push(lines[j]);
          if (lines[j].includes('*/')) {
            break;
          }
        }
        comments.push(commentLines.join('\n'));
        break;
      }

      if (line.startsWith('//') || line.startsWith('/*')) {
        comments.push(line);
      }

      // Stop if we hit another function/class definition
      if (line.match(/^(function|class|const|let|var)\s+/) && i < lines.length - 1) {
        break;
      }
    }

    return comments;
  }

  /**
   * Extract dependencies for a code entity
   */
  extractDependencies(content, entityName) {
    const dependencies = [];
    const importRegex = /import\s+.*from\s+['"]([^'"]+)['"]/g;
    const requireRegex = /require\s*\(\s*['"]([^'"]+)['"]\s*\)/g;

    let match;
    while ((match = importRegex.exec(content)) !== null) {
      dependencies.push({
        type: 'import',
        module: match[1]
      });
    }

    while ((match = requireRegex.exec(content)) !== null) {
      dependencies.push({
        type: 'require',
        module: match[1]
      });
    }

    return dependencies;
  }

  /**
   * Generate module-level documentation
   */
  async generateModuleDocumentation(analysis) {
    const modules = this.groupByModule(analysis.files);
    const documentation = [];

    for (const [moduleName, files] of modules) {
      const moduleDoc = await this.generateModuleDoc(moduleName, files);
      documentation.push(moduleDoc);
    }

    return documentation;
  }

  /**
   * Group files by module
   */
  groupByModule(files) {
    const modules = new Map();

    files.forEach(file => {
      const moduleName = this.extractModuleName(file.path);
      if (!modules.has(moduleName)) {
        modules.set(moduleName, []);
      }
      modules.get(moduleName).push(file);
    });

    return modules;
  }

  /**
   * Extract module name from file path
   */
  extractModuleName(filePath) {
    const parts = filePath.split('/');
    const srcIndex = parts.indexOf('src');

    if (srcIndex >= 0 && srcIndex < parts.length - 1) {
      return parts[srcIndex + 1];
    }

    return 'root';
  }

  /**
   * Generate documentation for a module
   */
  async generateModuleDoc(moduleName, files) {
    const entities = [];
    const dependencies = new Set();

    // Aggregate entities and dependencies from all files
    files.forEach(file => {
      file.entities?.forEach(entity => entities.push(entity));
      file.dependencies?.forEach(dep => dependencies.add(dep));
    });

    const description = await this.nlp.generateModuleDescription(moduleName, entities);

    return {
      type: 'module',
      name: moduleName,
      content: `# ${moduleName} Module

## Overview
${description}

## Files
${files.map(f => `- \`${f.path}\``).join('\n')}

## Components
${entities.filter(e => e.type === 'component').map(e => `- \`${e.name}\``).join('\n') || 'None'}

## Services
${entities.filter(e => e.type === 'service').map(e => `- \`${e.name}\``).join('\n') || 'None'}

## Dependencies
${Array.from(dependencies).map(d => `- \`${d}\``).join('\n') || 'None'}

---

*Generated by AI Documentation Generator on ${new Date().toISOString()}*`,
      metadata: {
        files: files.length,
        entities: entities.length,
        dependencies: dependencies.size
      }
    };
  }

  /**
   * Generate architecture documentation
   */
  async generateArchitectureDocumentation(analysis) {
    const architecture = {
      modules: this.groupByModule(analysis.files),
      dependencies: this.analyzeDependencies(analysis.files),
      patterns: this.identifyPatterns(analysis.files)
    };

    const description = await this.nlp.generateArchitectureDescription(architecture);

    return {
      type: 'architecture',
      name: 'System Architecture',
      content: `# System Architecture

## Overview
${description}

## Module Structure
${Array.from(architecture.modules.keys()).map(module =>
  `### ${module}\n- Files: ${architecture.modules.get(module).length}`
).join('\n')}

## Dependency Analysis
${this.renderDependencyGraph(architecture.dependencies)}

## Design Patterns
${architecture.patterns.map(pattern =>
  `- **${pattern.name}**: ${pattern.description}`
).join('\n')}

---

*Generated by AI Documentation Generator on ${new Date().toISOString()}*`,
      metadata: {
        modules: architecture.modules.size,
        dependencies: architecture.dependencies.length,
        patterns: architecture.patterns.length
      }
    };
  }

  /**
   * Analyze dependencies across the codebase
   */
  analyzeDependencies(files) {
    const dependencies = new Map();

    files.forEach(file => {
      file.dependencies?.forEach(dep => {
        if (!dependencies.has(dep)) {
          dependencies.set(dep, []);
        }
        dependencies.get(dep).push(file.path);
      });
    });

    return Array.from(dependencies.entries()).map(([dep, files]) => ({
      dependency: dep,
      usedBy: files,
      usage: files.length
    }));
  }

  /**
   * Identify architectural patterns
   */
  identifyPatterns(files) {
    const patterns = [];

    // MVC Pattern
    const hasControllers = files.some(f => f.path.includes('controller'));
    const hasModels = files.some(f => f.path.includes('model'));
    const hasViews = files.some(f => f.path.includes('view') || f.path.includes('component'));

    if (hasControllers && hasModels && hasViews) {
      patterns.push({
        name: 'MVC Pattern',
        description: 'Model-View-Controller architecture detected'
      });
    }

    // Service Layer Pattern
    const hasServices = files.some(f => f.path.includes('service'));
    if (hasServices) {
      patterns.push({
        name: 'Service Layer',
        description: 'Service layer pattern for business logic separation'
      });
    }

    // Repository Pattern
    const hasRepositories = files.some(f => f.path.includes('repository') || f.path.includes('repo'));
    if (hasRepositories) {
      patterns.push({
        name: 'Repository Pattern',
        description: 'Data access abstraction layer'
      });
    }

    return patterns;
  }

  /**
   * Render dependency graph in markdown
   */
  renderDependencyGraph(dependencies) {
    if (dependencies.length === 0) return 'No external dependencies detected.';

    return `### Top Dependencies
${dependencies
  .sort((a, b) => b.usage - a.usage)
  .slice(0, 10)
  .map(dep => `- **${dep.dependency}** (${dep.usage} files)`)
  .join('\n')}

### Dependency Graph
\`\`\`mermaid
graph TD
${dependencies
  .slice(0, 5)
  .map(dep => `  ${dep.dependency.replace(/[^a-zA-Z0-9]/g, '_')}["${dep.dependency}"]`)
  .join('\n')}
\`\`\``;
  }

  /**
   * Render template with data
   */
  renderTemplate(template, data) {
    let result = template;

    // Replace simple variables
    Object.entries(data).forEach(([key, value]) => {
      if (typeof value === 'string' || typeof value === 'number') {
        result = result.replace(new RegExp(`{{${key}}}`, 'g'), value);
      }
    });

    // Handle complex data structures
    if (data.entities) {
      result = result.replace('{{entities}}', this.renderEntities(data.entities));
    }

    if (data.descriptions) {
      result = result.replace('{{description}}', data.descriptions.overview || '');
    }

    return result;
  }

  /**
   * Render entities section
   */
  renderEntities(entities) {
    if (!entities || entities.length === 0) return 'No entities detected.';

    return entities.map(entity => {
      let output = `### ${entity.name}\n`;
      output += `**Type:** ${entity.type}\n\n`;

      if (entity.params && entity.params.length > 0) {
        output += `**Parameters:**\n${entity.params.map(p => `- \`${p}\``).join('\n')}\n\n`;
      }

      if (entity.comments && entity.comments.length > 0) {
        output += `**Description:**\n${entity.comments.join('\n')}\n\n`;
      }

      return output;
    }).join('\n');
  }

  /**
   * Estimate complexity of a code entity
   */
  estimateComplexity(params) {
    if (!params) return 'low';

    const paramCount = params.split(',').length;
    if (paramCount > 5) return 'high';
    if (paramCount > 2) return 'medium';
    return 'low';
  }

  /**
   * Calculate confidence score for generated documentation
   */
  calculateConfidence(entities, descriptions) {
    let confidence = 0;

    if (entities && entities.length > 0) confidence += 0.4;
    if (descriptions && descriptions.overview) confidence += 0.4;
    if (entities && entities.some(e => e.comments && e.comments.length > 0)) confidence += 0.2;

    return Math.min(confidence, 1.0);
  }

  /**
   * Assess quality of generated documentation
   */
  assessQuality(documentation) {
    let score = 0;

    if (documentation.includes('# ')) score += 0.3; // Has title
    if (documentation.includes('## ')) score += 0.3; // Has sections
    if (documentation.includes('```')) score += 0.2; // Has code examples
    if (documentation.length > 500) score += 0.2; // Sufficient length

    return Math.min(score, 1.0);
  }

  /**
   * Save generated documentation
   */
  async saveDocumentation(documentation, outputPath) {
    const outputDir = path.join(__dirname, '..', outputPath);

    for (const doc of documentation) {
      try {
        let filePath;

        if (doc.type === 'file') {
          // Generate path based on source file
          const relativePath = path.relative('./src', doc.path);
          const docPath = relativePath.replace(/\.[^.]+$/, '.md');
          filePath = path.join(outputDir, '02_Development_Phase', docPath);
        } else if (doc.type === 'module') {
          filePath = path.join(outputDir, '02_Development_Phase', `${doc.name}.md`);
        } else if (doc.type === 'architecture') {
          filePath = path.join(outputDir, '05_References', 'architecture.md');
        }

        // Ensure directory exists
        const dir = path.dirname(filePath);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }

        fs.writeFileSync(filePath, doc.content);
        console.log(`✅ Generated: ${path.relative(outputDir, filePath)}`);

      } catch (error) {
        console.error(`❌ Failed to save ${doc.path}:`, error.message);
      }
    }
  }

  /**
   * Generate quality report
   */
  async generateQualityReport(documentation) {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalFiles: documentation.length,
        averageQuality: 0,
        highQuality: 0,
        needsReview: 0
      },
      files: []
    };

    documentation.forEach(doc => {
      report.files.push({
        path: doc.path || doc.name,
        type: doc.type,
        quality: doc.metadata.quality,
        confidence: doc.metadata.confidence || 0,
        entities: doc.metadata.entities || 0
      });

      if (doc.metadata.quality >= 0.8) {
        report.summary.highQuality++;
      } else if (doc.metadata.quality < 0.6) {
        report.summary.needsReview++;
      }
    });

    report.summary.averageQuality = documentation.reduce(
      (sum, doc) => sum + doc.metadata.quality, 0
    ) / documentation.length;

    return report;
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      isInitialized: this.isInitialized,
      templates: Array.from(this.templates.keys()),
      patterns: Array.from(this.patterns.keys()),
      config: this.config
    };
  }
}

/**
 * Natural Language Processor for documentation generation
 */
class NaturalLanguageProcessor {
  constructor() {
    this.templates = {
      function: "This function {name} {purpose}. It takes {params} parameters and {returns}.",
      class: "The {name} class {purpose}. It {extends} and provides {methods}.",
      component: "The {name} component {purpose}. It renders {output} and handles {interactions}.",
      module: "The {name} module {purpose}. It contains {components} and {services}."
    };
  }

  async initialize() {
    // Initialize NLP models if needed
    console.log('🧠 Initializing NLP processor...');
  }

  async generateDescriptions(entities) {
    const descriptions = {
      overview: '',
      entities: {}
    };

    // Generate overview
    descriptions.overview = await this.generateOverview(entities);

    // Generate entity descriptions
    for (const entity of entities) {
      descriptions.entities[entity.name] = await this.generateEntityDescription(entity);
    }

    return descriptions;
  }

  async generateOverview(entities) {
    const types = entities.reduce((acc, entity) => {
      acc[entity.type] = (acc[entity.type] || 0) + 1;
      return acc;
    }, {});

    const typeDescriptions = Object.entries(types)
      .map(([type, count]) => `${count} ${type}${count > 1 ? 's' : ''}`)
      .join(', ');

    return `This file contains ${typeDescriptions}. It provides functionality for ${this.inferPurpose(entities)}.`;
  }

  async generateEntityDescription(entity) {
    const template = this.templates[entity.type] || this.templates.function;

    return template
      .replace('{name}', entity.name)
      .replace('{purpose}', this.inferPurpose([entity]))
      .replace('{params}', entity.params?.length || 0)
      .replace('{returns}', 'performs operations')
      .replace('{extends}', entity.extends ? `extends ${entity.extends}` : 'is a base class')
      .replace('{methods}', entity.methods?.length || 0)
      .replace('{output}', 'UI elements')
      .replace('{interactions}', 'user interactions');
  }

  async generateModuleDescription(moduleName, entities) {
    const purpose = this.inferPurpose(entities);
    return `The ${moduleName} module ${purpose}. It contains ${entities.length} code entities including functions, classes, and components.`;
  }

  async generateArchitectureDescription(architecture) {
    const moduleCount = architecture.modules.size;
    const totalFiles = Array.from(architecture.modules.values())
      .reduce((sum, files) => sum + files.length, 0);

    return `This system consists of ${moduleCount} modules containing ${totalFiles} files. The architecture follows ${architecture.patterns.length > 0 ? 'established patterns' : 'a modular structure'} for maintainability and scalability.`;
  }

  inferPurpose(entities) {
    // Simple heuristic-based purpose inference
    if (entities.some(e => e.type === 'component')) {
      return 'renders user interface components';
    }
    if (entities.some(e => e.type === 'service')) {
      return 'provides business logic and data processing';
    }
    if (entities.some(e => e.name.toLowerCase().includes('auth'))) {
      return 'handles authentication and authorization';
    }
    if (entities.some(e => e.name.toLowerCase().includes('api'))) {
      return 'manages API communications';
    }

    return 'provides core functionality';
  }
}

/**
 * Code Analyzer for source code analysis
 */
class CodeAnalyzer {
  constructor() {
    this.supportedExtensions = ['.js', '.ts', '.jsx', '.tsx', '.py', '.java'];
  }

  async initialize() {
    console.log('🔍 Initializing code analyzer...');
  }

  async analyze(sourcePath) {
    console.log(`🔍 Analyzing codebase at ${sourcePath}...`);

    const files = this.scanDirectory(sourcePath);
    const analysis = {
      files: [],
      summary: {
        totalFiles: 0,
        totalLines: 0,
        languages: {},
        complexity: {}
      }
    };

    for (const file of files) {
      try {
        const fileAnalysis = await this.analyzeFile(file);
        analysis.files.push(fileAnalysis);

        // Update summary
        analysis.summary.totalFiles++;
        analysis.summary.totalLines += fileAnalysis.lines;

        const lang = this.detectLanguage(file);
        analysis.summary.languages[lang] = (analysis.summary.languages[lang] || 0) + 1;

      } catch (error) {
        console.warn(`⚠️  Failed to analyze ${file}:`, error.message);
      }
    }

    return analysis;
  }

  scanDirectory(dir, files = []) {
    const items = fs.readdirSync(dir);

    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory() && !this.shouldSkipDirectory(item)) {
        this.scanDirectory(fullPath, files);
      } else if (stat.isFile() && this.isSupportedFile(item)) {
        files.push(fullPath);
      }
    }

    return files;
  }

  shouldSkipDirectory(dirName) {
    const skipDirs = ['node_modules', '.git', 'dist', 'build', 'coverage', '.next'];
    return skipDirs.includes(dirName);
  }

  isSupportedFile(filename) {
    const ext = path.extname(filename);
    return this.supportedExtensions.includes(ext);
  }

  async analyzeFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n').length;

    return {
      path: filePath,
      content: content,
      lines: lines,
      language: this.detectLanguage(filePath),
      entities: [], // Will be populated by AIDocumentationGenerator
      dependencies: [], // Will be populated by AIDocumentationGenerator
      complexity: this.calculateComplexity(content),
      quality: this.assessCodeQuality(content)
    };
  }

  detectLanguage(filePath) {
    const ext = path.extname(filePath);

    const langMap = {
      '.js': 'JavaScript',
      '.ts': 'TypeScript',
      '.jsx': 'React',
      '.tsx': 'React TypeScript',
      '.py': 'Python',
      '.java': 'Java'
    };

    return langMap[ext] || 'Unknown';
  }

  calculateComplexity(content) {
    // Simple complexity calculation
    const lines = content.split('\n');
    let complexity = 0;

    lines.forEach(line => {
      if (line.includes('if ')) complexity += 1;
      if (line.includes('for ') || line.includes('while ')) complexity += 1;
      if (line.includes('switch ')) complexity += 1;
      if (line.includes('catch ')) complexity += 1;
    });

    return complexity;
  }

  assessCodeQuality(content) {
    let score = 1.0;

    // Deduct for various code quality issues
    if (content.includes('console.log')) score -= 0.1;
    if (content.includes('TODO') || content.includes('FIXME')) score -= 0.1;
    if (content.includes('var ')) score -= 0.1; // Prefer const/let

    return Math.max(score, 0.0);
  }
}

module.exports = AIDocumentationGenerator;
