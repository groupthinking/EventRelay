#!/usr/bin/env node

/**
 * Create Documentation Templates Script
 * Generates documentation templates for new code files
 */

const fs = require('fs');
const path = require('path');

class DocTemplateCreator {
  constructor() {
    this.docsDir = path.join(__dirname, '..', 'Docs');
    this.templates = {
      component: this.getComponentTemplate(),
      service: this.getServiceTemplate(),
      utility: this.getUtilityTemplate(),
      api: this.getApiTemplate()
    };
  }

  /**
   * Get component documentation template
   */
  getComponentTemplate() {
    return `# Component Documentation

## Overview
Brief description of the component's purpose and functionality.

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| propName | Type | Yes/No | defaultValue | Description of the prop |

## Usage

\`\`\`jsx
import ComponentName from './ComponentName';

// Basic usage
<ComponentName
  requiredProp="value"
  optionalProp="value"
/>
\`\`\`

## Examples

### Basic Example
\`\`\`jsx
<ComponentName prop="value">
  Child content
</ComponentName>
\`\`\`

### Advanced Example
\`\`\`jsx
<ComponentName
  prop="value"
  onEvent={handleEvent}
  className="custom-class"
>
  Complex child content
</ComponentName>
\`\`\`

## Accessibility
- Component meets WCAG 2.1 AA standards
- Keyboard navigation support
- Screen reader compatibility
- Focus management

## Testing

### Unit Tests
- [ ] Component renders without crashing
- [ ] Props are handled correctly
- [ ] Events are triggered appropriately
- [ ] Accessibility requirements met

### Integration Tests
- [ ] Component integrates with parent components
- [ ] State changes are handled correctly
- [ ] Error boundaries work as expected

## Performance Considerations
- Component is optimized for performance
- Minimal re-renders
- Efficient event handling
- Memory leak prevention

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Related Components
- RelatedComponent1
- RelatedComponent2

---

*Last Updated: ${new Date().toISOString().split('T')[0]}*`;
  }

  /**
   * Get service documentation template
   */
  getServiceTemplate() {
    return `# Service Documentation

## Overview
Brief description of the service's purpose and functionality.

## Methods

### methodName(parameters)
Description of what the method does.

**Parameters:**
- \`param1\` (Type): Description of parameter
- \`param2\` (Type, optional): Description of optional parameter

**Returns:** Type - Description of return value

**Throws:**
- \`ErrorType\`: When this error occurs

**Example:**
\`\`\`javascript
const result = await service.methodName(param1, param2);
\`\`\`

## Configuration

\`\`\`javascript
const service = new ServiceName({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.example.com',
  timeout: 5000
});
\`\`\`

## Error Handling

### Common Errors
- \`AuthenticationError\`: Invalid API credentials
- \`NetworkError\`: Network connectivity issues
- \`ValidationError\`: Invalid input parameters

### Error Recovery
\`\`\`javascript
try {
  const result = await service.methodName(params);
} catch (error) {
  if (error instanceof AuthenticationError) {
    // Handle authentication error
    await service.refreshToken();
  } else if (error instanceof NetworkError) {
    // Handle network error
    await retryWithBackoff(() => service.methodName(params));
  } else {
    // Handle other errors
    console.error('Service error:', error);
  }
}
\`\`\`

## Testing

### Mock Setup
\`\`\`javascript
const mockService = {
  methodName: jest.fn().mockResolvedValue(expectedResult)
};
\`\`\`

### Integration Tests
- [ ] Service connects to external APIs successfully
- [ ] Authentication works correctly
- [ ] Error handling is robust
- [ ] Rate limiting is respected

## Performance
- Average response time: < 200ms
- Error rate: < 1%
- Throughput: 1000 requests/second
- Memory usage: < 50MB

## Monitoring
- Health check endpoint: \`GET /health\`
- Metrics endpoint: \`GET /metrics\`
- Logs: Structured JSON logging
- Alerts: Error rate > 5%

## Dependencies
- External API: api.example.com
- Database: PostgreSQL
- Cache: Redis

---

*Last Updated: ${new Date().toISOString().split('T')[0]}*`;
  }

  /**
   * Get utility documentation template
   */
  getUtilityTemplate() {
    return `# Utility Documentation

## Overview
Brief description of the utility's purpose and functionality.

## Functions

### functionName(parameters)
Description of what the function does.

**Parameters:**
- \`param1\` (Type): Description of parameter
- \`param2\` (Type, optional): Description of optional parameter

**Returns:** Type - Description of return value

**Example:**
\`\`\`javascript
import { functionName } from './utils';

const result = functionName(param1, param2);
\`\`\`

## Type Definitions

\`\`\`typescript
interface InputType {
  property1: string;
  property2: number;
}

interface OutputType {
  result: string;
  metadata: {
    timestamp: Date;
    version: string;
  };
}
\`\`\`

## Error Handling

### Validation Errors
- \`TypeError\`: Invalid parameter types
- \`RangeError\`: Parameter values out of acceptable range
- \`ReferenceError\`: Required dependencies not available

## Performance Characteristics
- Time Complexity: O(n) - Linear time
- Space Complexity: O(1) - Constant space
- Memory Usage: Minimal heap allocation
- CPU Usage: Efficient algorithms used

## Browser Compatibility
- ES6+ features used
- Polyfills required for IE11 support
- Tree-shaking friendly
- Side-effect free

## Testing

### Unit Tests
\`\`\`javascript
describe('functionName', () => {
  test('should handle normal inputs', () => {
    const result = functionName('input');
    expect(result).toBe('expected');
  });

  test('should handle edge cases', () => {
    expect(() => functionName(null)).toThrow(TypeError);
  });
});
\`\`\`

### Edge Cases Covered
- [ ] Null/undefined inputs
- [ ] Empty arrays/objects
- [ ] Large datasets
- [ ] Unicode characters
- [ ] Special characters

## Dependencies
- None (pure utility)
- Uses only standard library functions
- No external dependencies

## Migration Guide
If migrating from a previous version:

1. Update import statements
2. Check for breaking changes
3. Update type definitions
4. Run existing tests

---

*Last Updated: ${new Date().toISOString().split('T')[0]}*`;
  }

  /**
   * Get API documentation template
   */
  getApiTemplate() {
    return `# API Documentation

## Overview
Brief description of the API endpoint's purpose and functionality.

## Endpoint
\`METHOD /api/path\`

## Authentication
- **Type:** Bearer Token
- **Header:** \`Authorization: Bearer <token>\`
- **Scopes Required:** \`read:resource\`, \`write:resource\`

## Request

### Headers
\`\`\`
Content-Type: application/json
Authorization: Bearer <token>
X-API-Version: 1.0
\`\`\`

### Parameters

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | Yes | Resource identifier |

#### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| limit | number | No | 20 | Number of items to return |
| offset | number | No | 0 | Number of items to skip |

### Body
\`\`\`json
{
  "name": "Resource Name",
  "description": "Resource description",
  "metadata": {
    "tags": ["tag1", "tag2"],
    "category": "example"
  }
}
\`\`\`

## Response

### Success Response (200)
\`\`\`json
{
  "success": true,
  "data": {
    "id": "resource_id",
    "name": "Resource Name",
    "description": "Resource description",
    "created_at": "2025-01-20T10:30:00Z",
    "updated_at": "2025-01-20T10:30:00Z"
  },
  "meta": {
    "request_id": "req_123456789",
    "timestamp": "2025-01-20T10:30:00Z"
  }
}
\`\`\`

### Error Responses

#### 400 Bad Request
\`\`\`json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "name",
      "reason": "Name is required"
    }
  }
}
\`\`\`

#### 401 Unauthorized
\`\`\`json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid or expired token"
  }
}
\`\`\`

#### 403 Forbidden
\`\`\`json
{
  "success": false,
  "error": {
    "code": "AUTHORIZATION_ERROR",
    "message": "Insufficient permissions"
  }
}
\`\`\`

#### 404 Not Found
\`\`\`json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
\`\`\`

## Rate Limiting
- **Limit:** 100 requests per minute
- **Headers:**
  - \`X-RateLimit-Limit: 100\`
  - \`X-RateLimit-Remaining: 95\`
  - \`X-RateLimit-Reset: 1640995200\`

## Examples

### cURL
\`\`\`bash
curl -X POST \\
  https://api.example.com/api/resource \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer your-token" \\
  -d '{
    "name": "Example Resource",
    "description": "This is an example"
  }'
\`\`\`

### JavaScript (fetch)
\`\`\`javascript
const response = await fetch('/api/resource', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': \`Bearer \${token}\`
  },
  body: JSON.stringify({
    name: 'Example Resource',
    description: 'This is an example'
  })
});

const data = await response.json();
\`\`\`

### Python (requests)
\`\`\`python
import requests

response = requests.post('/api/resource',
  headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
  },
  json={
    'name': 'Example Resource',
    'description': 'This is an example'
  }
)

data = response.json()
\`\`\`

## Testing

### Unit Tests
- [ ] Request validation works correctly
- [ ] Authentication is properly verified
- [ ] Business logic executes as expected
- [ ] Error responses are formatted correctly

### Integration Tests
- [ ] Database operations work correctly
- [ ] External service calls succeed
- [ ] Caching layers function properly
- [ ] Monitoring and logging are captured

### Load Tests
- [ ] Handles 100 concurrent requests
- [ ] Response time < 200ms under normal load
- [ ] Graceful degradation under high load
- [ ] Memory usage remains stable

## Monitoring
- **Response Time:** < 200ms average
- **Error Rate:** < 1%
- **Availability:** 99.9% uptime
- **Logs:** Structured JSON logging

## Related Endpoints
- \`GET /api/resource\` - List resources
- \`GET /api/resource/{id}\` - Get specific resource
- \`PUT /api/resource/{id}\` - Update resource
- \`DELETE /api/resource/{id}\` - Delete resource

---

*Last Updated: ${new Date().toISOString().split('T')[0]}*`;
  }

  /**
   * Create documentation template for a code file
   */
  createTemplate(filePath, templateType = 'auto') {
    const fileName = path.basename(filePath, path.extname(filePath));
    const relativePath = path.relative(process.cwd(), filePath);

    // Determine template type based on file path and content
    let detectedType = templateType;
    if (templateType === 'auto') {
      if (filePath.includes('/components/') || filePath.includes('\\components\\')) {
        detectedType = 'component';
      } else if (filePath.includes('/services/') || filePath.includes('\\services\\')) {
        detectedType = 'service';
      } else if (filePath.includes('/utils/') || filePath.includes('\\utils\\') ||
                 filePath.includes('/helpers/') || filePath.includes('\\helpers\\')) {
        detectedType = 'utility';
      } else if (filePath.includes('/api/') || filePath.includes('\\api\\') ||
                 filePath.includes('/routes/') || filePath.includes('\\routes\\')) {
        detectedType = 'api';
      } else {
        detectedType = 'utility'; // Default fallback
      }
    }

    const template = this.templates[detectedType];
    if (!template) {
      console.error(`Unknown template type: ${detectedType}`);
      return null;
    }

    // Customize template with file-specific information
    const customizedTemplate = template
      .replace(/ComponentName/g, fileName)
      .replace(/ServiceName/g, fileName)
      .replace(/functionName/g, fileName.toLowerCase())
      .replace(/Resource Name/g, fileName);

    return {
      content: customizedTemplate,
      type: detectedType,
      fileName: `${fileName}.md`,
      path: path.join(this.docsDir, '02_Development_Phase', `${fileName}.md`)
    };
  }

  /**
   * Process files and create documentation templates
   */
  processFiles(filePaths) {
    const results = [];

    filePaths.forEach(filePath => {
      if (!fs.existsSync(filePath)) {
        console.warn(`File not found: ${filePath}`);
        return;
      }

      const template = this.createTemplate(filePath);
      if (template) {
        // Check if documentation already exists
        if (fs.existsSync(template.path)) {
          console.log(`Documentation already exists: ${template.path}`);
          return;
        }

        // Create documentation file
        fs.writeFileSync(template.path, template.content);
        console.log(`✅ Created documentation: ${template.path}`);

        results.push({
          file: filePath,
          doc: template.path,
          type: template.type
        });
      }
    });

    return results;
  }
}

// CLI interface
function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('Usage: node create-doc-templates.js <file1> [file2] ...');
    console.log('Example: node create-doc-templates.js src/components/Button.js src/services/UserService.js');
    process.exit(1);
  }

  const creator = new DocTemplateCreator();
  const results = creator.processFiles(args);

  if (results.length > 0) {
    console.log(`\n📝 Created ${results.length} documentation templates:`);
    results.forEach(result => {
      console.log(`  ${result.file} → ${result.doc} (${result.type})`);
    });
  } else {
    console.log('\n📝 No new documentation templates created.');
  }
}

if (require.main === module) {
  main();
}

module.exports = DocTemplateCreator;
