# 📋 File Usage Guide for AI Assistants

## 🎯 **Purpose**
This guide tells you **exactly when and why** to use each documentation file. Use this as your primary reference for determining which documents to consult for any given task.

---

## 📊 **QUICK REFERENCE - When to Use Which File**

| **Scenario** | **Primary File** | **Secondary Files** | **Why** |
|-------------|------------------|-------------------|---------|
| **Analyzing a PRD** | `01_Planning_Phase/PRD_Implementation_Plan_Generator.md` | `03_Risk_Management/Risk_Register.md` | Comprehensive analysis framework |
| **Starting Development** | `02_Development_Phase/Development_Agent_Workflow.md` | `02_Development_Phase/Testing_Guide.md` | Step-by-step development process |
| **Writing Tests** | `02_Development_Phase/Testing_Guide.md` | `02_Development_Phase/Development_Agent_Workflow.md` | Testing procedures and examples |
| **Risk Assessment** | `03_Risk_Management/Risk_Register.md` | `03_Risk_Management/Common_Risk_Patterns.md` | Risk identification and mitigation |
| **API Development** | `04_Deployment_Operations/API_documentation.md` | `02_Development_Phase/Testing_Guide.md` | API design and testing |
| **Deployment** | `04_Deployment_Operations/Deployment_guide.md` | `03_Risk_Management/Risk_Register.md` | Deployment procedures and risks |
| **Bug Investigation** | `02_Development_Phase/Bug_tracking.md` | `03_Risk_Management/Common_Risk_Patterns.md` | Issue tracking and patterns |

---

## 📁 **DETAILED FILE USAGE BY CATEGORY**

## **1. PLANNING PHASE TASKS**

### **When analyzing a Product Requirements Document (PRD):**
```markdown
🎯 PRIMARY: 01_Planning_Phase/PRD_Implementation_Plan_Generator.md
   - Use the complete PRD analysis framework
   - Follow the 6-step analysis process
   - Generate implementation plan with risk assessment
   - Create feature categorization and prioritization

🎯 SECONDARY: 03_Risk_Management/Risk_Register.md
   - Identify potential risks early in planning
   - Assess technical feasibility
   - Consider external dependencies
```

### **When creating implementation plans:**
```markdown
🎯 PRIMARY: 01_Planning_Phase/PRD_Implementation_Plan_Generator.md
   - Use the implementation stages template
   - Apply risk mitigation checklists
   - Follow technology stack research guidelines

🎯 SECONDARY: 03_Risk_Management/Risk_Register.md
   - Integrate risk assessment into plan
   - Add risk mitigation strategies
```

## **2. DEVELOPMENT PHASE TASKS**

### **When starting any development task:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Development_Agent_Workflow.md
   - Follow the 10-step task execution protocol
   - Use the pre-implementation checklist
   - Complete all testing checklists (7a-7e)
   - Follow documentation update requirements

🎯 SECONDARY: 02_Development_Phase/Testing_Guide.md
   - Reference appropriate testing procedures
   - Use testing examples and templates
```

### **When writing unit tests:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Testing_Guide.md
   - Follow unit testing best practices
   - Use Jest configuration examples
   - Apply mocking strategies for dependencies
   - Ensure 80%+ code coverage

🎯 SECONDARY: 02_Development_Phase/Development_Agent_Workflow.md
   - Complete unit testing checklist (7a)
   - Follow testing standards and guidelines
```

### **When writing integration tests:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Testing_Guide.md
   - Use database integration test patterns
   - Follow API integration testing procedures
   - Apply test data management strategies

🎯 SECONDARY: 02_Development_Phase/Development_Agent_Workflow.md
   - Complete integration testing checklist (7b)
   - Reference testing standards
```

### **When writing end-to-end tests:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Testing_Guide.md
   - Use Playwright examples for E2E testing
   - Follow user workflow testing patterns
   - Implement test helper utilities

🎯 SECONDARY: 02_Development_Phase/Development_Agent_Workflow.md
   - Complete E2E testing checklist (7c)
   - Follow testing automation guidelines
```

### **When implementing security measures:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Testing_Guide.md
   - Use security testing procedures
   - Follow authentication testing patterns
   - Implement input validation testing

🎯 SECONDARY: 03_Risk_Management/Common_Risk_Patterns.md
   - Reference security vulnerability patterns
   - Apply security mitigation strategies
```

### **When optimizing performance:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Testing_Guide.md
   - Use performance testing with Artillery
   - Follow load testing procedures
   - Implement performance monitoring

🎯 SECONDARY: 02_Development_Phase/Development_Agent_Workflow.md
   - Complete performance testing checklist (7e)
   - Follow performance benchmarking guidelines
```

## **3. RISK MANAGEMENT TASKS**

### **When conducting risk assessment:**
```markdown
🎯 PRIMARY: 03_Risk_Management/Risk_Register.md
   - Use the risk assessment methodology
   - Follow risk scoring (Probability × Impact)
   - Document risks in the active register

🎯 SECONDARY: 03_Risk_Management/Common_Risk_Patterns.md
   - Check for similar risk patterns
   - Apply proven mitigation strategies
```

### **When identifying new risks:**
```markdown
🎯 PRIMARY: 03_Risk_Management/Risk_Register.md
   - Add new risks to the active register
   - Assess probability and impact
   - Create mitigation strategies

🎯 SECONDARY: 03_Risk_Management/Common_Risk_Patterns.md
   - Compare against known patterns
   - Use similar mitigation approaches
```

### **When implementing risk mitigation:**
```markdown
🎯 PRIMARY: 03_Risk_Management/Common_Risk_Patterns.md
   - Use specific mitigation strategies
   - Follow code examples and procedures
   - Apply proven solutions

🎯 SECONDARY: 03_Risk_Management/Risk_Register.md
   - Update risk status after mitigation
   - Document mitigation effectiveness
```

## **4. DEPLOYMENT & OPERATIONS TASKS**

### **When setting up deployment infrastructure:**
```markdown
🎯 PRIMARY: 04_Deployment_Operations/Deployment_guide.md
   - Follow environment setup procedures
   - Use infrastructure configuration examples
   - Apply security and monitoring setup

🎯 SECONDARY: 03_Risk_Management/Risk_Register.md
   - Assess deployment-related risks
   - Implement risk mitigation for deployment
```

### **When deploying to production:**
```markdown
🎯 PRIMARY: 04_Deployment_Operations/Deployment_guide.md
   - Follow deployment procedures and checklists
   - Use rollback strategies if needed
   - Complete post-deployment verification

🎯 SECONDARY: 03_Risk_Management/Risk_Register.md
   - Monitor for deployment-related risks
   - Update risk status post-deployment
```

### **When documenting APIs:**
```markdown
🎯 PRIMARY: 04_Deployment_Operations/API_documentation.md
   - Follow API documentation standards
   - Use authentication and schema examples
   - Document rate limiting and error handling

🎯 SECONDARY: 02_Development_Phase/Testing_Guide.md
   - Reference API testing procedures
   - Use API testing examples
```

### **When setting up monitoring:**
```markdown
🎯 PRIMARY: 04_Deployment_Operations/Deployment_guide.md
   - Follow monitoring setup procedures
   - Configure alerting and logging
   - Implement performance monitoring

🎯 SECONDARY: 02_Development_Phase/Testing_Guide.md
   - Use performance testing integration
   - Follow monitoring best practices
```

## **5. BUG TRACKING & ISSUE MANAGEMENT**

### **When investigating bugs:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Bug_tracking.md
   - Use issue classification system
   - Follow investigation procedures
   - Document root cause analysis

🎯 SECONDARY: 03_Risk_Management/Common_Risk_Patterns.md
   - Check for similar known patterns
   - Apply pattern-based solutions
```

### **When documenting new issues:**
```markdown
🎯 PRIMARY: 02_Development_Phase/Bug_tracking.md
   - Use the issue reporting template
   - Follow priority classification
   - Document reproduction steps

🎯 SECONDARY: 02_Development_Phase/Development_Agent_Workflow.md
   - Follow error handling procedures
   - Update relevant documentation
```

## **6. REFERENCE & QUICK LOOKUPS**

### **When you need a quick reference:**
```markdown
🎯 PRIMARY: 05_References/Enhanced_System_Quick_Reference.md
   - Use for quick overviews and reminders
   - Check what's new in the system
   - Find pro tips and shortcuts

🎯 SECONDARY: 05_References/Review_Summary_and_Recommendations.md
   - Reference for comprehensive reviews
   - Check implementation recommendations
   - Review system enhancements
```

### **When researching system changes:**
```markdown
🎯 PRIMARY: 05_References/Review_Summary_and_Recommendations.md
   - Understand recent system enhancements
   - Review implementation recommendations
   - Check success metrics and outcomes

🎯 SECONDARY: 05_References/Enhanced_System_Quick_Reference.md
   - Get quick overview of changes
   - Find practical usage examples
```

---

## ⚠️ **CRITICAL AI GUIDELINES**

### **Always:**
- ✅ **Check this guide first** when deciding which files to reference
- ✅ **Read the PRIMARY file** completely for your task type
- ✅ **Reference SECONDARY files** for additional context
- ✅ **Cross-reference** between related documents when needed
- ✅ **Update relevant documentation** after making changes

### **Never:**
- ❌ **Skip this guide** - always determine correct file usage first
- ❌ **Use files outside** your determined scope
- ❌ **Make changes** without consulting required documentation
- ❌ **Ignore** the primary/secondary file hierarchy

### **When Uncertain:**
- 🔄 **Re-read this guide** for your specific scenario
- 🔄 **Check the main README** for overall structure
- 🔄 **Ask for clarification** from the user if still unclear
- 🔄 **Document the uncertainty** for future improvement

---

## 🎯 **File Usage Decision Framework**

```markdown
1. Identify the task type from user's request
2. Match task to PRIMARY file in the table above
3. Note any SECONDARY files for additional context
4. Read PRIMARY file completely
5. Reference SECONDARY files as needed
6. Cross-reference between documents when making decisions
7. Update relevant documentation after task completion
```

**Remember: Correct file usage ensures you work effectively within this comprehensive documentation system!** 📚

---

*This guide ensures AI assistants can make informed decisions about documentation usage, maximizing effectiveness and maintaining system integrity.*
