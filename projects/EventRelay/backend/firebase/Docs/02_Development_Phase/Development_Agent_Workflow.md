---
alwaysApply: true
---

# Development Agent Workflow - Cursor Rules

## Primary Directive
You are a development agent implementing a project. Follow established documentation and maintain consistency.

## Core Workflow Process

### Before Starting Any Task
- Consult `/Docs/Implementation.md` for current stage and available tasks
- Check task dependencies and prerequisites
- Verify scope understanding

### Task Execution Protocol

#### 1. Task Assessment
- Read subtask from `/Docs/Implementation.md`
- Assess subtask complexity:
  - **Simple subtask:** Implement directly
  - **Complex subtask:** Create a todo list

#### 2. Pre-Implementation Checklist
- Verify all dependencies are met
- Check for related tasks in other stages
- Review risk mitigation strategies
- Ensure required resources are available
- Confirm alignment with project architecture

#### 3. Documentation Research
- Check `/Docs/Implementation.md` for relevant documentation links in the subtask
- Read and understand documentation before implementing

#### 4. UI/UX Implementation
- Consult `/Docs/UI_UX_doc.md` before implementing any UI/UX elements
- Follow design system specifications and responsive requirements

#### 5. Project Structure Compliance
- Check `/Docs/project_structure.md` before:
  - Running commands
  - Creating files/folders
  - Making structural changes
  - Adding dependencies

#### 6. Error Handling
- Check `/Docs/Bug_tracking.md` for similar issues before fixing
- Document all errors and solutions in Bug_tracking.md
- Include error details, root cause, and resolution steps

#### 7. Testing and Validation
- Run unit tests for new functionality
- Perform integration testing if applicable
- Test edge cases and error scenarios
- Validate against acceptance criteria
- Update API documentation for any changes
- Verify performance requirements are met

#### 7a. Unit Testing Checklist
- [ ] All public methods have unit tests
- [ ] Edge cases and error conditions tested
- [ ] Mock external dependencies properly
- [ ] Test coverage meets minimum threshold (80%)
- [ ] Tests run successfully in CI/CD pipeline
- [ ] Test names are descriptive and follow naming conventions

#### 7b. Integration Testing Checklist
- [ ] API endpoints tested with realistic data
- [ ] Database operations tested (CRUD operations)
- [ ] External service integrations verified
- [ ] Authentication and authorization tested
- [ ] Cross-component data flow validated
- [ ] Error handling between components tested

#### 7c. End-to-End Testing Checklist
- [ ] Complete user workflows tested from start to finish
- [ ] Different user roles and permissions validated
- [ ] Data persistence across sessions verified
- [ ] Error recovery and fallback scenarios tested
- [ ] Performance under normal load conditions checked
- [ ] Mobile responsiveness tested on target devices

#### 7d. Security Testing Checklist
- [ ] Input validation prevents common attacks (SQL injection, XSS)
- [ ] Authentication mechanisms properly implemented
- [ ] Authorization controls enforce proper access levels
- [ ] Sensitive data properly encrypted
- [ ] Security headers configured correctly
- [ ] No hardcoded secrets or credentials

#### 7e. Performance Testing Checklist
- [ ] Response times meet defined SLAs (< 500ms for most operations)
- [ ] Memory usage stays within acceptable limits
- [ ] Database queries optimized and indexed
- [ ] Static assets properly cached and compressed
- [ ] Load testing performed with expected concurrent users
- [ ] Scalability tested for future growth projections

#### 8. Documentation Update
- Update relevant documentation files
- Add code comments and inline documentation
- Document any architectural decisions made
- Update deployment guide if infrastructure changes
- Record any lessons learned or best practices discovered

#### 9. Testing Standards and Guidelines

##### Code Coverage Requirements
- **Unit Tests**: Minimum 80% coverage for business logic
- **Integration Tests**: All critical API endpoints and data flows
- **E2E Tests**: All primary user workflows
- **Performance Tests**: All high-traffic operations

##### Test Naming Conventions
- **Unit Tests**: `describe('ComponentName', () => { it('should do something', () => {}) })`
- **Integration Tests**: `test/integration/component-name.test.js`
- **E2E Tests**: `test/e2e/workflow-name.test.js`

##### Test Data Management
- Use factories for consistent test data creation
- Avoid hardcoded test data in favor of dynamic generation
- Clean up test data after each test run
- Use realistic data that matches production patterns

##### Automated Testing Integration
- All tests must run in CI/CD pipeline
- Test failures block deployments to production
- Performance regression tests run automatically
- Security tests integrated into build process

#### 10. Task Completion
Mark tasks complete only when:
- All functionality implemented correctly
- Code follows project structure guidelines
- UI/UX matches specifications (if applicable)
- **All unit tests pass** (minimum 80% coverage)
- **Integration tests pass** for all affected components
- **E2E tests pass** for modified user workflows
- **Security tests pass** with no vulnerabilities
- **Performance tests pass** against defined benchmarks
- Documentation is updated with testing procedures
- No errors or warnings remain in test suite
- All task list items completed (if applicable)
- Peer code review completed (if required)
- Testing sign-off obtained from QA team

### File Reference Priority
1. `/Docs/Bug_tracking.md` - Check for known issues first
2. `/Docs/Implementation.md` - Main task reference
3. `/Docs/project_structure.md` - Structure guidance
4. `/Docs/UI_UX_doc.md` - Design requirements

## Critical Rules
- **NEVER** skip documentation consultation
- **NEVER** mark tasks complete without proper testing
- **NEVER** ignore project structure guidelines
- **NEVER** implement UI without checking UI_UX_doc.md
- **NEVER** fix errors without checking Bug_tracking.md first
- **ALWAYS** document errors and solutions
- **ALWAYS** follow the established workflow process

Remember: Build a cohesive, well-documented, and maintainable project. Every decision should support overall project goals and maintain consistency with established patterns.
