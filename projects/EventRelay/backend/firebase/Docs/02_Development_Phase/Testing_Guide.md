# Testing Guide and Best Practices

## Overview
This comprehensive testing guide provides detailed procedures, examples, and best practices for implementing quality assurance throughout the development lifecycle.

## Testing Pyramid Strategy

```
End-to-End Tests (10-20%)
    ↗
Integration Tests (20-30%)
    ↗
Unit Tests (60-70%)
```

## Unit Testing

### Framework Setup
```javascript
// Jest configuration (jest.config.js)
module.exports = {
  testEnvironment: 'node',
  collectCoverageFrom: [
    'src/**/*.{js,ts}',
    '!src/**/*.d.ts',
    '!src/index.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(js|ts)',
    '<rootDir>/src/**/*.(test|spec).(js|ts)'
  ]
};
```

### Unit Test Examples

#### Service Layer Testing
```javascript
// src/services/__tests__/userService.test.ts
import { UserService } from '../userService';
import { UserRepository } from '../../repositories/userRepository';

jest.mock('../../repositories/userRepository');

describe('UserService', () => {
  let userService: UserService;
  let mockUserRepository: jest.Mocked<UserRepository>;

  beforeEach(() => {
    mockUserRepository = {
      findById: jest.fn(),
      findByEmail: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn()
    } as jest.Mocked<UserRepository>;

    userService = new UserService(mockUserRepository);
  });

  describe('createUser', () => {
    it('should create a user successfully', async () => {
      // Arrange
      const userData = {
        email: 'john@example.com',
        name: 'John Doe',
        password: 'SecurePass123!'
      };

      const expectedUser = {
        id: 'usr_123',
        ...userData,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      mockUserRepository.findByEmail.mockResolvedValue(null);
      mockUserRepository.create.mockResolvedValue(expectedUser);

      // Act
      const result = await userService.createUser(userData);

      // Assert
      expect(result).toEqual(expectedUser);
      expect(mockUserRepository.findByEmail).toHaveBeenCalledWith(userData.email);
      expect(mockUserRepository.create).toHaveBeenCalledWith(
        expect.objectContaining({
          email: userData.email,
          name: userData.name
        })
      );
    });

    it('should throw error for duplicate email', async () => {
      // Arrange
      const userData = {
        email: 'existing@example.com',
        name: 'John Doe',
        password: 'SecurePass123!'
      };

      mockUserRepository.findByEmail.mockResolvedValue({
        id: 'usr_456',
        email: userData.email
      });

      // Act & Assert
      await expect(userService.createUser(userData))
        .rejects
        .toThrow('User with this email already exists');
    });

    it('should validate email format', async () => {
      // Arrange
      const userData = {
        email: 'invalid-email',
        name: 'John Doe',
        password: 'SecurePass123!'
      };

      // Act & Assert
      await expect(userService.createUser(userData))
        .rejects
        .toThrow('Invalid email format');
    });
  });
});
```

#### Controller Layer Testing
```javascript
// src/controllers/__tests__/userController.test.ts
import request from 'supertest';
import express from 'express';
import { UserController } from '../userController';
import { UserService } from '../../services/userService';

describe('UserController', () => {
  let app: express.Application;
  let userController: UserController;
  let mockUserService: jest.Mocked<UserService>;

  beforeEach(() => {
    mockUserService = {
      createUser: jest.fn(),
      getUserById: jest.fn(),
      updateUser: jest.fn(),
      deleteUser: jest.fn()
    } as jest.Mocked<UserService>;

    userController = new UserController(mockUserService);

    app = express();
    app.use(express.json());
    app.post('/users', userController.createUser);
    app.get('/users/:id', userController.getUser);
  });

  describe('POST /users', () => {
    it('should create user and return 201', async () => {
      // Arrange
      const userData = {
        email: 'john@example.com',
        name: 'John Doe',
        password: 'SecurePass123!'
      };

      const createdUser = {
        id: 'usr_123',
        ...userData,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      mockUserService.createUser.mockResolvedValue(createdUser);

      // Act
      const response = await request(app)
        .post('/users')
        .send(userData)
        .expect(201);

      // Assert
      expect(response.body.success).toBe(true);
      expect(response.body.data).toEqual(createdUser);
      expect(mockUserService.createUser).toHaveBeenCalledWith(userData);
    });

    it('should return 400 for invalid data', async () => {
      // Arrange
      const invalidData = {
        email: 'invalid-email',
        name: '',
        password: '123'
      };

      mockUserService.createUser.mockRejectedValue(
        new ValidationError('Invalid user data')
      );

      // Act
      const response = await request(app)
        .post('/users')
        .send(invalidData)
        .expect(400);

      // Assert
      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('VALIDATION_ERROR');
    });
  });
});
```

#### Utility Function Testing
```javascript
// src/utils/__tests__/passwordUtils.test.ts
import bcrypt from 'bcrypt';
import { hashPassword, verifyPassword } from '../passwordUtils';

jest.mock('bcrypt');

describe('Password Utilities', () => {
  const mockPassword = 'SecurePass123!';
  const mockHash = '$2b$10$mockedHashValue';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('hashPassword', () => {
    it('should hash password with correct salt rounds', async () => {
      // Arrange
      (bcrypt.hash as jest.Mock).mockResolvedValue(mockHash);

      // Act
      const result = await hashPassword(mockPassword);

      // Assert
      expect(bcrypt.hash).toHaveBeenCalledWith(mockPassword, 12);
      expect(result).toBe(mockHash);
    });

    it('should throw error on hash failure', async () => {
      // Arrange
      (bcrypt.hash as jest.Mock).mockRejectedValue(new Error('Hash failed'));

      // Act & Assert
      await expect(hashPassword(mockPassword))
        .rejects
        .toThrow('Hash failed');
    });
  });

  describe('verifyPassword', () => {
    it('should return true for correct password', async () => {
      // Arrange
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      // Act
      const result = await verifyPassword(mockPassword, mockHash);

      // Assert
      expect(result).toBe(true);
      expect(bcrypt.compare).toHaveBeenCalledWith(mockPassword, mockHash);
    });

    it('should return false for incorrect password', async () => {
      // Arrange
      (bcrypt.compare as jest.Mock).mockResolvedValue(false);

      // Act
      const result = await verifyPassword('wrongPassword', mockHash);

      // Assert
      expect(result).toBe(false);
    });
  });
});
```

## Integration Testing

### Database Integration Tests
```javascript
// src/__tests__/integration/userRepository.test.ts
import { UserRepository } from '../../repositories/userRepository';
import { Database } from '../../database';
import { User } from '../../models/user';

describe('UserRepository Integration', () => {
  let db: Database;
  let userRepository: UserRepository;

  beforeAll(async () => {
    // Use test database
    db = new Database({
      host: process.env.TEST_DB_HOST || 'localhost',
      database: 'test_db',
      username: process.env.TEST_DB_USER,
      password: process.env.TEST_DB_PASSWORD
    });

    await db.connect();
    userRepository = new UserRepository(db);

    // Clean up before tests
    await db.query('DELETE FROM users');
  });

  afterAll(async () => {
    await db.disconnect();
  });

  beforeEach(async () => {
    // Clean up between tests
    await db.query('DELETE FROM users');
  });

  describe('create', () => {
    it('should create user in database', async () => {
      // Arrange
      const userData = {
        email: 'john@example.com',
        name: 'John Doe',
        passwordHash: 'hashed_password'
      };

      // Act
      const createdUser = await userRepository.create(userData);

      // Assert
      expect(createdUser).toMatchObject({
        email: userData.email,
        name: userData.name
      });
      expect(createdUser.id).toBeDefined();
      expect(createdUser.createdAt).toBeInstanceOf(Date);

      // Verify in database
      const dbUser = await userRepository.findById(createdUser.id);
      expect(dbUser).toEqual(createdUser);
    });

    it('should prevent duplicate emails', async () => {
      // Arrange
      const userData = {
        email: 'john@example.com',
        name: 'John Doe',
        passwordHash: 'hashed_password'
      };

      await userRepository.create(userData);

      // Act & Assert
      await expect(userRepository.create(userData))
        .rejects
        .toThrow('duplicate key value');
    });
  });

  describe('findByEmail', () => {
    it('should find user by email', async () => {
      // Arrange
      const userData = {
        email: 'jane@example.com',
        name: 'Jane Smith',
        passwordHash: 'hashed_password'
      };

      const createdUser = await userRepository.create(userData);

      // Act
      const foundUser = await userRepository.findByEmail(userData.email);

      // Assert
      expect(foundUser).toEqual(createdUser);
    });

    it('should return null for non-existent email', async () => {
      // Act
      const foundUser = await userRepository.findByEmail('nonexistent@example.com');

      // Assert
      expect(foundUser).toBeNull();
    });
  });
});
```

### API Integration Tests
```javascript
// src/__tests__/integration/authAPI.test.ts
import request from 'supertest';
import { createTestApp } from '../../test/testApp';
import { UserRepository } from '../../repositories/userRepository';
import { AuthService } from '../../services/authService';

describe('Authentication API Integration', () => {
  let app: any;
  let userRepository: UserRepository;
  let authService: AuthService;

  beforeAll(async () => {
    // Create test application with test database
    ({ app, userRepository, authService } = await createTestApp());
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    // Clean test data
    await userRepository.clearAll();
  });

  describe('POST /auth/register', () => {
    it('should register new user successfully', async () => {
      // Arrange
      const userData = {
        email: 'john@example.com',
        name: 'John Doe',
        password: 'SecurePass123!'
      };

      // Act
      const response = await request(app)
        .post('/auth/register')
        .send(userData)
        .expect(201);

      // Assert
      expect(response.body.success).toBe(true);
      expect(response.body.data.user).toMatchObject({
        email: userData.email,
        name: userData.name
      });
      expect(response.body.data.tokens).toBeDefined();
      expect(response.body.data.tokens.access_token).toBeDefined();
      expect(response.body.data.tokens.refresh_token).toBeDefined();
    });

    it('should return 400 for existing email', async () => {
      // Arrange
      const userData = {
        email: 'existing@example.com',
        name: 'John Doe',
        password: 'SecurePass123!'
      };

      // Create existing user
      await userRepository.create({
        email: userData.email,
        name: userData.name,
        passwordHash: await authService.hashPassword(userData.password)
      });

      // Act
      const response = await request(app)
        .post('/auth/register')
        .send(userData)
        .expect(400);

      // Assert
      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('USER_EXISTS');
    });
  });

  describe('POST /auth/login', () => {
    it('should login existing user', async () => {
      // Arrange
      const userData = {
        email: 'jane@example.com',
        name: 'Jane Smith',
        password: 'SecurePass123!'
      };

      // Create user
      await userRepository.create({
        email: userData.email,
        name: userData.name,
        passwordHash: await authService.hashPassword(userData.password)
      });

      // Act
      const response = await request(app)
        .post('/auth/login')
        .send({
          email: userData.email,
          password: userData.password
        })
        .expect(200);

      // Assert
      expect(response.body.success).toBe(true);
      expect(response.body.data.user.email).toBe(userData.email);
      expect(response.body.data.tokens).toBeDefined();
    });

    it('should return 401 for invalid credentials', async () => {
      // Act
      const response = await request(app)
        .post('/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'wrongpassword'
        })
        .expect(401);

      // Assert
      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('INVALID_CREDENTIALS');
    });
  });
});
```

## End-to-End Testing

### E2E Test Setup
```javascript
// e2e/test-setup.ts
import { chromium, Browser, Page } from 'playwright';
import { createTestApp } from '../src/test/testApp';

export class E2ETestHelper {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private testApp: any = null;

  async setup() {
    // Start test application
    this.testApp = await createTestApp();
    const appUrl = await this.testApp.listen(0);

    // Launch browser
    this.browser = await chromium.launch();
    this.page = await this.browser.newPage();

    // Configure page
    await this.page.setViewportSize({ width: 1280, height: 720 });
    this.page.setDefaultTimeout(10000);

    return {
      app: this.testApp,
      browser: this.browser,
      page: this.page,
      appUrl
    };
  }

  async teardown() {
    if (this.page) {
      await this.page.close();
    }
    if (this.browser) {
      await this.browser.close();
    }
    if (this.testApp) {
      await this.testApp.close();
    }
  }

  async loginUser(page: Page, email: string, password: string) {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', email);
    await page.fill('[data-testid="password-input"]', password);
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('/dashboard');
  }

  async createUser(page: Page, userData: { email: string; name: string; password: string }) {
    await page.goto('/register');
    await page.fill('[data-testid="email-input"]', userData.email);
    await page.fill('[data-testid="name-input"]', userData.name);
    await page.fill('[data-testid="password-input"]', userData.password);
    await page.click('[data-testid="register-button"]');
    await page.waitForURL('/dashboard');
  }
}
```

### User Workflow E2E Tests
```javascript
// e2e/user-registration-flow.test.ts
import { test, expect } from '@playwright/test';
import { E2ETestHelper } from './test-setup';

test.describe('User Registration Flow', () => {
  let helper: E2ETestHelper;

  test.beforeEach(async () => {
    helper = new E2ETestHelper();
    await helper.setup();
  });

  test.afterEach(async () => {
    await helper.teardown();
  });

  test('should complete full user registration and login flow', async ({ page }) => {
    // Navigate to registration page
    await page.goto('/register');
    await expect(page).toHaveTitle('Register - MyApp');

    // Fill registration form
    await page.fill('[data-testid="email-input"]', 'john.doe@example.com');
    await page.fill('[data-testid="name-input"]', 'John Doe');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.fill('[data-testid="confirm-password-input"]', 'SecurePass123!');

    // Submit registration
    await page.click('[data-testid="register-button"]');

    // Verify success message
    await expect(page.locator('[data-testid="success-message"]'))
      .toContainText('Registration successful!');

    // Should redirect to login page
    await page.waitForURL('/login');

    // Login with new credentials
    await page.fill('[data-testid="email-input"]', 'john.doe@example.com');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.click('[data-testid="login-button"]');

    // Verify successful login
    await page.waitForURL('/dashboard');
    await expect(page.locator('[data-testid="welcome-message"]'))
      .toContainText('Welcome, John Doe');
  });

  test('should validate registration form', async ({ page }) => {
    await page.goto('/register');

    // Try to submit empty form
    await page.click('[data-testid="register-button"]');

    // Check validation messages
    await expect(page.locator('[data-testid="email-error"]'))
      .toContainText('Email is required');
    await expect(page.locator('[data-testid="name-error"]'))
      .toContainText('Name is required');
    await expect(page.locator('[data-testid="password-error"]'))
      .toContainText('Password is required');

    // Test invalid email
    await page.fill('[data-testid="email-input"]', 'invalid-email');
    await page.click('[data-testid="register-button"]');
    await expect(page.locator('[data-testid="email-error"]'))
      .toContainText('Please enter a valid email');

    // Test weak password
    await page.fill('[data-testid="password-input"]', '123');
    await page.click('[data-testid="register-button"]');
    await expect(page.locator('[data-testid="password-error"]'))
      .toContainText('Password must be at least 8 characters');
  });

  test('should prevent duplicate email registration', async ({ page }) => {
    // First registration
    await page.goto('/register');
    await page.fill('[data-testid="email-input"]', 'duplicate@example.com');
    await page.fill('[data-testid="name-input"]', 'User One');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.fill('[data-testid="confirm-password-input"]', 'SecurePass123!');
    await page.click('[data-testid="register-button"]');

    await page.waitForURL('/dashboard');
    await page.click('[data-testid="logout-button"]');

    // Second registration attempt with same email
    await page.goto('/register');
    await page.fill('[data-testid="email-input"]', 'duplicate@example.com');
    await page.fill('[data-testid="name-input"]', 'User Two');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.fill('[data-testid="confirm-password-input"]', 'SecurePass123!');
    await page.click('[data-testid="register-button"]');

    // Should show error
    await expect(page.locator('[data-testid="error-message"]'))
      .toContainText('Email already exists');
  });
});
```

### Shopping Cart E2E Test
```javascript
// e2e/shopping-cart-flow.test.ts
test.describe('Shopping Cart Flow', () => {
  test('should complete full purchase flow', async ({ page }) => {
    // Login
    await helper.loginUser(page, 'buyer@example.com', 'password123');

    // Navigate to products
    await page.goto('/products');

    // Add first product to cart
    await page.click('[data-testid="product-1-add-to-cart"]');
    await expect(page.locator('[data-testid="cart-count"]')).toContainText('1');

    // Add second product
    await page.click('[data-testid="product-2-add-to-cart"]');
    await expect(page.locator('[data-testid="cart-count"]')).toContainText('2');

    // View cart
    await page.click('[data-testid="cart-icon"]');
    await expect(page.locator('[data-testid="cart-item-1"]')).toBeVisible();
    await expect(page.locator('[data-testid="cart-item-2"]')).toBeVisible();

    // Update quantity
    await page.fill('[data-testid="quantity-input-1"]', '2');
    await page.click('[data-testid="update-cart"]');

    // Verify total calculation
    const total = await page.locator('[data-testid="cart-total"]').textContent();
    expect(parseFloat(total.replace('$', ''))).toBeGreaterThan(0);

    // Proceed to checkout
    await page.click('[data-testid="checkout-button"]');
    await page.waitForURL('/checkout');

    // Fill shipping information
    await page.fill('[data-testid="shipping-name"]', 'John Doe');
    await page.fill('[data-testid="shipping-address"]', '123 Main St');
    await page.fill('[data-testid="shipping-city"]', 'Anytown');
    await page.selectOption('[data-testid="shipping-state"]', 'CA');
    await page.fill('[data-testid="shipping-zip"]', '12345');

    // Fill payment information
    await page.fill('[data-testid="card-number"]', '4111111111111111');
    await page.fill('[data-testid="expiry-date"]', '12/25');
    await page.fill('[data-testid="cvv"]', '123');

    // Complete purchase
    await page.click('[data-testid="complete-order"]');

    // Verify success
    await expect(page.locator('[data-testid="order-confirmation"]'))
      .toContainText('Order placed successfully');
    await expect(page.locator('[data-testid="order-number"]')).toBeVisible();

    // Verify cart is empty
    await page.goto('/cart');
    await expect(page.locator('[data-testid="empty-cart"]')).toBeVisible();
  });
});
```

## Performance Testing

### Load Testing with Artillery
```yaml
# performance/load-test.yml
config:
  target: 'http://localhost:3000'
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 10
      rampTo: 50
      name: "Load testing"
    - duration: 60
      arrivalRate: 50
      name: "Peak load"
  defaults:
    headers:
      Authorization: 'Bearer {{token}}'

scenarios:
  - name: 'User authentication flow'
    weight: 30
    flow:
      - post:
          url: '/auth/login'
          json:
            email: 'user{{id}}@example.com'
            password: 'password123'
          capture:
            json: '$.data.tokens.access_token'
            as: 'token'
      - get:
          url: '/api/users/profile'
          headers:
            Authorization: 'Bearer {{token}}'

  - name: 'API data retrieval'
    weight: 40
    flow:
      - post:
          url: '/auth/login'
          json:
            email: 'user{{id}}@example.com'
            password: 'password123'
          capture:
            json: '$.data.tokens.access_token'
            as: 'token'
      - get:
          url: '/api/posts'
          headers:
            Authorization: 'Bearer {{token}}'
      - get:
          url: '/api/posts/{{randomInt}}'
          headers:
            Authorization: 'Bearer {{token}}'

  - name: 'Data creation and update'
    weight: 30
    flow:
      - post:
          url: '/auth/login'
          json:
            email: 'user{{id}}@example.com'
            password: 'password123'
          capture:
            json: '$.data.tokens.access_token'
            as: 'token'
      - post:
          url: '/api/posts'
          headers:
            Authorization: 'Bearer {{token}}'
          json:
            title: 'Test Post {{id}}'
            content: 'Test content for performance testing'
      - put:
          url: '/api/posts/{{id}}'
          headers:
            Authorization: 'Bearer {{token}}'
          json:
            title: 'Updated Test Post {{id}}'
            content: 'Updated content for performance testing'
```

### Performance Test Analysis
```javascript
// performance/performance-test.js
const artillery = require('artillery');
const fs = require('fs');

async function runPerformanceTest() {
  const testConfig = {
    config: {
      target: 'http://localhost:3000',
      phases: [
        { duration: 60, arrivalRate: 10, name: 'Warm up' },
        { duration: 120, arrivalRate: 50, name: 'Load testing' }
      ]
    },
    scenarios: [
      {
        name: 'API Performance Test',
        weight: 100,
        flow: [
          {
            post: {
              url: '/auth/login',
              json: {
                email: 'test@example.com',
                password: 'password123'
              }
            }
          },
          {
            get: {
              url: '/api/users/profile'
            }
          }
        ]
      }
    ]
  };

  try {
    const results = await artillery.run(testConfig);

    // Analyze results
    const analysis = {
      timestamp: new Date(),
      summary: results.report.summary,
      metrics: {
        responseTime: {
          min: results.report.aggregate.latency.min,
          max: results.report.aggregate.latency.max,
          median: results.report.aggregate.latency.median,
          p95: results.report.aggregate.latency.p95,
          p99: results.report.aggregate.latency.p99
        },
        throughput: results.report.aggregate.rps,
        errorRate: (results.report.aggregate.errors / results.report.aggregate.requests) * 100
      },
      thresholds: {
        maxResponseTime: 500, // ms
        maxErrorRate: 1, // percentage
        minThroughput: 100 // requests per second
      }
    };

    // Check against thresholds
    const passed = (
      analysis.metrics.responseTime.p95 <= analysis.thresholds.maxResponseTime &&
      analysis.metrics.errorRate <= analysis.thresholds.maxErrorRate &&
      analysis.metrics.throughput >= analysis.thresholds.minThroughput
    );

    analysis.result = passed ? 'PASS' : 'FAIL';

    // Save results
    fs.writeFileSync(
      `./performance-results/${Date.now()}-performance-test.json`,
      JSON.stringify(analysis, null, 2)
    );

    console.log('Performance Test Results:', analysis.result);
    console.log(`Response Time (P95): ${analysis.metrics.responseTime.p95}ms`);
    console.log(`Error Rate: ${analysis.metrics.errorRate}%`);
    console.log(`Throughput: ${analysis.metrics.throughput} RPS`);

    return analysis;

  } catch (error) {
    console.error('Performance test failed:', error);
    throw error;
  }
}

// Run test
runPerformanceTest()
  .then(() => process.exit(0))
  .catch(() => process.exit(1));
```

## Security Testing

### Automated Security Scanning
```javascript
// security/security-test.js
const { scan } = require('security-scanner');
const fs = require('fs');

async function runSecurityTests() {
  console.log('Starting security tests...');

  const vulnerabilities = [];

  // 1. Dependency vulnerability scan
  console.log('Scanning dependencies...');
  const dependencyResults = await scan.dependencies();
  vulnerabilities.push(...dependencyResults);

  // 2. Code security scan
  console.log('Scanning code for security issues...');
  const codeResults = await scan.code({
    paths: ['src/**/*.js', 'src/**/*.ts'],
    rules: [
      'no-sql-injection',
      'no-xss',
      'secure-headers',
      'input-validation',
      'authentication-checks'
    ]
  });
  vulnerabilities.push(...codeResults);

  // 3. Configuration security scan
  console.log('Scanning configuration files...');
  const configResults = await scan.configuration({
    files: ['.env', 'config/*.json', 'config/*.js']
  });
  vulnerabilities.push(...configResults);

  // Categorize vulnerabilities
  const categorized = {
    critical: vulnerabilities.filter(v => v.severity === 'critical'),
    high: vulnerabilities.filter(v => v.severity === 'high'),
    medium: vulnerabilities.filter(v => v.severity === 'medium'),
    low: vulnerabilities.filter(v => v.severity === 'low'),
    info: vulnerabilities.filter(v => v.severity === 'info')
  };

  // Generate report
  const report = {
    timestamp: new Date(),
    summary: {
      total: vulnerabilities.length,
      critical: categorized.critical.length,
      high: categorized.high.length,
      medium: categorized.medium.length,
      low: categorized.low.length,
      info: categorized.info.length
    },
    vulnerabilities: categorized,
    recommendations: generateRecommendations(categorized)
  };

  // Save report
  fs.writeFileSync(
    `./security-reports/${Date.now()}-security-scan.json`,
    JSON.stringify(report, null, 2)
  );

  // Check if build should fail
  const shouldFail = categorized.critical.length > 0 || categorized.high.length > 5;

  if (shouldFail) {
    console.error('❌ Security test failed - critical vulnerabilities found');
    console.error(`Critical: ${categorized.critical.length}`);
    console.error(`High: ${categorized.high.length}`);
    process.exit(1);
  } else {
    console.log('✅ Security test passed');
    console.log(`Total issues: ${vulnerabilities.length}`);
  }

  return report;
}

function generateRecommendations(categorized) {
  const recommendations = [];

  if (categorized.critical.length > 0) {
    recommendations.push('IMMEDIATE: Address all critical security vulnerabilities');
  }

  if (categorized.high.length > 0) {
    recommendations.push('URGENT: Fix high-severity security issues within 1 week');
  }

  if (categorized.medium.length > 0) {
    recommendations.push('PLAN: Address medium-severity issues in next sprint');
  }

  return recommendations;
}

// Run security tests
runSecurityTests()
  .then(() => process.exit(0))
  .catch(() => process.exit(1));
```

### Common Security Test Cases
```javascript
// security/auth-security.test.js
describe('Authentication Security', () => {
  test('should prevent brute force attacks', async () => {
    // Attempt multiple failed logins
    for (let i = 0; i < 10; i++) {
      await request(app)
        .post('/auth/login')
        .send({
          email: 'user@example.com',
          password: 'wrongpassword'
        })
        .expect(401);
    }

    // Next attempt should be rate limited
    const response = await request(app)
      .post('/auth/login')
      .send({
        email: 'user@example.com',
        password: 'wrongpassword'
      });

    expect([401, 429]).toContain(response.status);
  });

  test('should use secure password hashing', async () => {
    const userData = {
      email: 'test@example.com',
      password: 'SecurePass123!'
    };

    await request(app)
      .post('/auth/register')
      .send(userData)
      .expect(201);

    // Verify password is hashed (not stored in plain text)
    const db = getTestDatabase();
    const user = await db.query(
      'SELECT password_hash FROM users WHERE email = ?',
      [userData.email]
    );

    expect(user[0].password_hash).not.toBe(userData.password);
    expect(user[0].password_hash).toMatch(/^\$2[ayb]\$.{56}$/); // bcrypt format
  });

  test('should prevent SQL injection', async () => {
    const maliciousInput = "'; DROP TABLE users; --";

    const response = await request(app)
      .post('/auth/login')
      .send({
        email: maliciousInput,
        password: 'password'
      })
      .expect(401);

    // Verify users table still exists and has data
    const db = getTestDatabase();
    const users = await db.query('SELECT COUNT(*) as count FROM users');
    expect(users[0].count).toBeGreaterThan(0);
  });
});
```

## Test Automation and CI/CD Integration

### GitHub Actions Testing Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [16.x, 18.x]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linting
        run: npm run lint

      - name: Run unit tests
        run: npm run test:unit

      - name: Run integration tests
        run: npm run test:integration

      - name: Run security tests
        run: npm run test:security

      - name: Generate coverage report
        run: npm run test:coverage

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage/lcov.info

  e2e:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Setup test database
        run: npm run db:test:setup

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-artifacts
          path: test-results/

  performance:
    runs-on: ubuntu-latest
    needs: e2e

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Setup performance test environment
        run: npm run perf:setup

      - name: Run performance tests
        run: npm run test:performance

      - name: Compare with baseline
        run: npm run perf:compare
```

### Test Data Management
```javascript
// test/testDataFactory.js
class TestDataFactory {
  constructor() {
    this.createdUsers = [];
    this.createdPosts = [];
  }

  async createUser(overrides = {}) {
    const defaultUser = {
      email: `user${Date.now()}@example.com`,
      name: `Test User ${Date.now()}`,
      password: 'TestPass123!'
    };

    const userData = { ...defaultUser, ...overrides };
    const user = await userService.createUser(userData);

    this.createdUsers.push(user);
    return user;
  }

  async createPost(userId, overrides = {}) {
    const defaultPost = {
      title: `Test Post ${Date.now()}`,
      content: `Test content ${Date.now()}`,
      userId
    };

    const postData = { ...defaultPost, ...overrides };
    const post = await postService.createPost(postData);

    this.createdPosts.push(post);
    return post;
  }

  async cleanup() {
    // Clean up in reverse order to handle dependencies
    for (const post of this.createdPosts.reverse()) {
      await postService.deletePost(post.id);
    }

    for (const user of this.createdUsers.reverse()) {
      await userService.deleteUser(user.id);
    }

    this.createdUsers = [];
    this.createdPosts = [];
  }
}

// Usage in tests
describe('PostService', () => {
  let factory;

  beforeEach(() => {
    factory = new TestDataFactory();
  });

  afterEach(async () => {
    await factory.cleanup();
  });

  test('should create post for user', async () => {
    const user = await factory.createUser();
    const post = await factory.createPost(user.id, {
      title: 'Custom Title',
      content: 'Custom Content'
    });

    expect(post.title).toBe('Custom Title');
    expect(post.userId).toBe(user.id);
  });
});
```

## Test Reporting and Analytics

### Coverage Reporting
```javascript
// test/coverageReporter.js
const fs = require('fs');
const path = require('path');

class CoverageReporter {
  constructor() {
    this.coverageDir = './coverage';
    this.historyFile = path.join(this.coverageDir, 'coverage-history.json');
  }

  generateReport(coverageData) {
    const report = {
      timestamp: new Date(),
      summary: {
        lines: coverageData.lines.pct,
        functions: coverageData.functions.pct,
        branches: coverageData.branches.pct,
        statements: coverageData.statements.pct
      },
      files: this.processFileCoverage(coverageData),
      trends: this.calculateTrends(coverageData)
    };

    // Save to history
    this.saveToHistory(report);

    // Generate HTML report
    this.generateHtmlReport(report);

    return report;
  }

  processFileCoverage(coverageData) {
    return Object.entries(coverageData).map(([filePath, fileCoverage]) => ({
      path: filePath,
      lines: fileCoverage.lines.pct,
      functions: fileCoverage.functions.pct,
      branches: fileCoverage.branches.pct,
      statements: fileCoverage.statements.pct
    })).sort((a, b) => a.lines - b.lines); // Sort by lowest coverage
  }

  calculateTrends(currentCoverage) {
    const history = this.loadHistory();
    if (history.length < 2) return null;

    const previous = history[history.length - 2];
    return {
      lines: currentCoverage.lines.pct - previous.summary.lines,
      functions: currentCoverage.functions.pct - previous.summary.functions,
      branches: currentCoverage.branches.pct - previous.summary.branches,
      statements: currentCoverage.statements.pct - previous.summary.statements
    };
  }

  loadHistory() {
    try {
      const data = fs.readFileSync(this.historyFile, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      return [];
    }
  }

  saveToHistory(report) {
    const history = this.loadHistory();
    history.push(report);

    // Keep only last 30 days
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const filteredHistory = history.filter(
      entry => new Date(entry.timestamp) > thirtyDaysAgo
    );

    fs.writeFileSync(this.historyFile, JSON.stringify(filteredHistory, null, 2));
  }

  generateHtmlReport(report) {
    const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Test Coverage Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
    .metric { display: inline-block; margin: 10px; text-align: center; }
    .metric-value { font-size: 24px; font-weight: bold; color: #2c5aa0; }
    .metric-label { font-size: 12px; color: #666; }
    .file-list { margin-top: 20px; }
    .file-item { padding: 10px; border-bottom: 1px solid #eee; }
    .file-path { font-weight: bold; }
    .coverage-bar { height: 20px; background: #eee; border-radius: 10px; overflow: hidden; }
    .coverage-fill { height: 100%; background: linear-gradient(to right, #ff6b6b, #ffd93d, #6bcf7f); }
    .low-coverage { background: #ff6b6b !important; }
    .medium-coverage { background: #ffd93d !important; }
    .high-coverage { background: linear-gradient(to right, #ffd93d, #6bcf7f) !important; }
  </style>
</head>
<body>
  <h1>Test Coverage Report</h1>
  <p><strong>Generated:</strong> ${new Date(report.timestamp).toLocaleString()}</p>

  <div class="summary">
    <h2>Coverage Summary</h2>
    <div class="metric">
      <div class="metric-value">${report.summary.lines}%</div>
      <div class="metric-label">Lines</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.summary.functions}%</div>
      <div class="metric-label">Functions</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.summary.branches}%</div>
      <div class="metric-label">Branches</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.summary.statements}%</div>
      <div class="metric-label">Statements</div>
    </div>
  </div>

  ${report.trends ? `
  <div class="summary">
    <h2>Coverage Trends (vs Previous)</h2>
    <div class="metric">
      <div class="metric-value">${report.trends.lines > 0 ? '+' : ''}${report.trends.lines.toFixed(1)}%</div>
      <div class="metric-label">Lines</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.trends.functions > 0 ? '+' : ''}${report.trends.functions.toFixed(1)}%</div>
      <div class="metric-label">Functions</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.trends.branches > 0 ? '+' : ''}${report.trends.branches.toFixed(1)}%</div>
      <div class="metric-label">Branches</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.trends.statements > 0 ? '+' : ''}${report.trends.statements.toFixed(1)}%</div>
      <div class="metric-label">Statements</div>
    </div>
  </div>
  ` : ''}

  <div class="file-list">
    <h2>File Coverage Details</h2>
    ${report.files.map(file => `
      <div class="file-item">
        <div class="file-path">${file.path}</div>
        <div class="coverage-bar">
          <div class="coverage-fill ${file.lines < 50 ? 'low-coverage' : file.lines < 80 ? 'medium-coverage' : 'high-coverage'}" style="width: ${file.lines}%"></div>
        </div>
        <div style="margin-top: 5px; font-size: 12px; color: #666;">
          Lines: ${file.lines}% | Functions: ${file.functions}% | Branches: ${file.branches}% | Statements: ${file.statements}%
        </div>
      </div>
    `).join('')}
  </div>
</body>
</html>`;

    fs.writeFileSync(path.join(this.coverageDir, 'coverage-report.html'), html);
  }
}

module.exports = CoverageReporter;
```

---

*This comprehensive testing guide provides practical examples and best practices for implementing quality assurance throughout the development lifecycle. Regular testing and monitoring are essential for maintaining high-quality, reliable software.*
