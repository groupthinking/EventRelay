# API Documentation

## Overview
This document provides comprehensive documentation for all API endpoints, authentication methods, data schemas, and integration patterns.

## Base URL
```
Production: https://api.yourapp.com/v1
Staging: https://api-staging.yourapp.com/v1
Development: https://api-dev.yourapp.com/v1
```

## Authentication

### JWT Bearer Token Authentication
All API requests require authentication using JWT tokens.

#### Obtaining Access Token
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 7200,
    "token_type": "Bearer"
  }
}
```

#### Using Access Token
Include the token in the Authorization header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Refreshing Tokens
```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### API Key Authentication (Admin Endpoints)
Some administrative endpoints require API key authentication:
```http
X-API-Key: your-api-key-here
```

## Rate Limiting

### Standard Limits
- **Authenticated Users**: 1000 requests per hour
- **Anonymous Users**: 100 requests per hour
- **Admin Endpoints**: 5000 requests per hour

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 60
```

### Rate Limit Exceeded Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2025-01-20T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  },
  "meta": {
    "timestamp": "2025-01-20T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

## Core API Endpoints

### Authentication Endpoints

#### POST /auth/login
Authenticate user and return access tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_123",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "user"
    },
    "tokens": {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi...",
      "expires_in": 7200
    }
  }
}
```

**Error Responses:**
- `400`: Invalid credentials
- `429`: Too many login attempts

#### POST /auth/refresh
Refresh access token using refresh token.

#### POST /auth/logout
Invalidate current session.

#### POST /auth/register
Register new user account.

### User Management Endpoints

#### GET /users
Retrieve paginated list of users.

**Query Parameters:**
- `page` (integer, default: 1): Page number
- `limit` (integer, default: 20): Items per page
- `search` (string): Search by name or email
- `role` (string): Filter by user role

**Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "usr_123",
        "email": "user@example.com",
        "name": "John Doe",
        "role": "user",
        "created_at": "2025-01-15T08:30:00Z",
        "last_login": "2025-01-20T10:15:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "total_pages": 8
    }
  }
}
```

#### GET /users/{user_id}
Get detailed user information.

#### PUT /users/{user_id}
Update user information.

#### DELETE /users/{user_id}
Delete user account (admin only).

### Data Models

#### User Schema
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^usr_[a-zA-Z0-9]+$",
      "description": "Unique user identifier"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "User's email address"
    },
    "name": {
      "type": "string",
      "minLength": 2,
      "maxLength": 100,
      "description": "User's full name"
    },
    "role": {
      "type": "string",
      "enum": ["admin", "moderator", "user"],
      "default": "user",
      "description": "User's role in the system"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Account creation timestamp"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Last update timestamp"
    }
  },
  "required": ["email", "name"]
}
```

#### Error Schema
```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string",
      "enum": [
        "VALIDATION_ERROR",
        "AUTHENTICATION_ERROR",
        "AUTHORIZATION_ERROR",
        "NOT_FOUND",
        "RATE_LIMIT_EXCEEDED",
        "INTERNAL_SERVER_ERROR"
      ]
    },
    "message": {
      "type": "string",
      "description": "Human-readable error message"
    },
    "details": {
      "type": "object",
      "description": "Additional error details"
    }
  },
  "required": ["code", "message"]
}
```

## WebSocket Integration

### Connection
```javascript
const ws = new WebSocket('wss://api.yourapp.com/v1/ws?token=<access_token>');
```

### Message Format
```json
{
  "type": "notification",
  "data": {
    "title": "New Message",
    "body": "You have received a new message",
    "user_id": "usr_123"
  },
  "timestamp": "2025-01-20T10:30:00Z"
}
```

### Supported Message Types
- `notification`: General notifications
- `user_update`: User data changes
- `system_alert`: System-wide alerts

## File Upload Endpoints

### POST /upload/avatar
Upload user avatar image.

**Content-Type:** `multipart/form-data`
**Max File Size:** 5MB
**Supported Formats:** JPEG, PNG, WebP

**Request:**
```http
POST /upload/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data

Form Data:
- file: [image file]
- user_id: usr_123
```

**Response:**
```json
{
  "success": true,
  "data": {
    "url": "https://cdn.yourapp.com/avatars/usr_123.jpg",
    "filename": "usr_123.jpg",
    "size": 245760,
    "mime_type": "image/jpeg"
  }
}
```

## Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing credentials |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |

## SDKs and Libraries

### JavaScript SDK
```bash
npm install @yourapp/sdk
```

```javascript
import { YourAppAPI } from '@yourapp/sdk';

const api = new YourAppAPI({
  baseURL: 'https://api.yourapp.com/v1',
  apiKey: 'your-api-key'
});

// Authenticate
const tokens = await api.auth.login('user@example.com', 'password');

// Make authenticated requests
const users = await api.users.list({ page: 1, limit: 10 });
```

### Python SDK
```bash
pip install yourapp-sdk
```

```python
from yourapp_sdk import YourAppAPI

api = YourAppAPI(
    base_url='https://api.yourapp.com/v1',
    api_key='your-api-key'
)

# Authenticate
tokens = api.auth.login('user@example.com', 'password')

# Make requests
users = api.users.list(page=1, limit=10)
```

## Testing and Development

### API Testing with Postman
Import the collection: `docs/postman_collection.json`

### Development Environment
```bash
# Start local API server
npm run dev

# Run tests
npm test

# Generate API documentation
npm run docs
```

### Mock Data for Testing
Use the following endpoints for testing without affecting production data:
- `/mock/users` - Mock user data
- `/mock/posts` - Mock content data
- `/mock/notifications` - Mock notification data

## Version Management

### API Versioning Strategy
- URL-based versioning: `/v1/`, `/v2/`
- Backward compatibility maintained for 12 months
- Deprecation warnings sent 3 months before removal
- Major version changes announced 6 months in advance

### Changelog
- **v1.2.0** (2025-01-20): Added WebSocket support
- **v1.1.0** (2025-01-10): Enhanced rate limiting
- **v1.0.0** (2025-01-01): Initial release

## Support and Contact

### Getting Help
- **Documentation**: [docs.yourapp.com](https://docs.yourapp.com)
- **Community Forum**: [community.yourapp.com](https://community.yourapp.com)
- **Support Email**: api-support@yourapp.com
- **Status Page**: [status.yourapp.com](https://status.yourapp.com)

### Service Level Agreement (SLA)
- **Uptime Guarantee**: 99.9%
- **Response Time**: < 200ms for 95% of requests
- **Support Response**: < 4 hours for critical issues

---

*This API documentation is automatically generated and should be kept up-to-date with code changes. Last updated: 2025-01-20*
