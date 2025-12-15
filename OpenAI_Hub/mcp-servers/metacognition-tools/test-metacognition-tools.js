#!/usr/bin/env node

/**
 * Test script for metacognition-tools MCP server
 * 
 * This script demonstrates how to use the metacognition-tools MCP server
 * by making requests to the Fermi estimation and Red Team attack tools.
 * 
 * Usage:
 *   node test-metacognition-tools.js
 */

// Example problems for Fermi estimation
const fermiProblems = [
  "How many piano tuners are there in Chicago?",
  "How many trees are there on Earth?",
  "How many cups of coffee are consumed in the United States each day?"
];

// Example system designs for Red Team attack
const systemDesigns = [
  "A web application that allows users to upload and share files with others.",
  "A mobile banking app that allows users to transfer money between accounts.",
  "A smart home system that controls lights, thermostats, and door locks."
];

// Example project descriptions for pre-mortem generation
const projectDescriptions = [
  "Developing a new e-commerce platform for a retail company.",
  "Migrating a legacy system to a cloud-based architecture.",
  "Implementing a new customer relationship management system."
];

// Example texts for cognitive bias analysis
const biasTexts = [
  "We've always done it this way, so we should continue with the same approach. The last three projects were successful, so this one will be too.",
  "The competitor's product failed in the market, so our similar product will also fail. We should abandon this project immediately.",
  "Our team is the best in the industry, so we don't need to worry about quality assurance or testing. We never make mistakes."
];

// Example data descriptions for risk dashboard generation
const dataDescriptions = [
  "We have customer transaction data, including purchase amounts, dates, and product categories. We also have inventory levels, supplier delivery times, and website traffic metrics.",
  "We have employee performance data, project timelines, budget allocations, and client satisfaction scores for the past 5 years.",
  "We have system uptime metrics, error logs, user activity data, and security incident reports for our cloud infrastructure."
];

// Example predictions and outcomes for metacognition review
const predictionsAndOutcomes = [
  {
    predictions: "We predicted that the new feature would increase user engagement by 20% within the first month. We also predicted that it would be easy to implement, taking only 2 weeks of development time.",
    outcomes: "The feature increased user engagement by only 5% in the first month, and it took 6 weeks to implement due to unforeseen technical challenges."
  },
  {
    predictions: "We predicted that moving to a microservices architecture would reduce deployment times by 50% and improve system reliability.",
    outcomes: "Deployment times were reduced by 60%, exceeding our expectations. However, system reliability decreased initially due to the increased complexity of the distributed system."
  }
];

// Randomly select examples to demonstrate
const randomFermiProblem = fermiProblems[Math.floor(Math.random() * fermiProblems.length)];
const randomSystemDesign = systemDesigns[Math.floor(Math.random() * systemDesigns.length)];
const randomProjectDescription = projectDescriptions[Math.floor(Math.random() * projectDescriptions.length)];
const randomBiasText = biasTexts[Math.floor(Math.random() * biasTexts.length)];
const randomDataDescription = dataDescriptions[Math.floor(Math.random() * dataDescriptions.length)];
const randomPredictionOutcome = predictionsAndOutcomes[Math.floor(Math.random() * predictionsAndOutcomes.length)];

// Simulate MCP tool usage
console.log("=== Metacognition Tools MCP Server Test ===\n");

console.log("--- Fermi Estimation ---");
console.log(`Problem: ${randomFermiProblem}`);
console.log("To use with MCP:");
console.log(`
use_mcp_tool({
  server_name: "metacognition-tools",
  tool_name: "fermi_estimate",
  arguments: {
    problem: "${randomFermiProblem}"
  }
});
`);
console.log("\n");

console.log("--- Red Team Attack ---");
console.log(`System Design: ${randomSystemDesign}`);
console.log("To use with MCP:");
console.log(`
use_mcp_tool({
  server_name: "metacognition-tools",
  tool_name: "red_team_attack",
  arguments: {
    systemDesign: "${randomSystemDesign}"
  }
});
`);
console.log("\n");

console.log("--- Pre-Mortem Generation ---");
console.log(`Project Description: ${randomProjectDescription}`);
console.log("To use with MCP:");
console.log(`
use_mcp_tool({
  server_name: "metacognition-tools",
  tool_name: "generate_pre_mortem",
  arguments: {
    projectDescription: "${randomProjectDescription}"
  }
});
`);
console.log("\n");

console.log("--- Cognitive Bias Analysis ---");
console.log(`Text: ${randomBiasText}`);
console.log("To use with MCP:");
console.log(`
use_mcp_tool({
  server_name: "metacognition-tools",
  tool_name: "analyze_biases",
  arguments: {
    text: "${randomBiasText}"
  }
});
`);
console.log("\n");

console.log("--- Risk Dashboard Generation ---");
console.log(`Data Description: ${randomDataDescription}`);
console.log("To use with MCP:");
console.log(`
use_mcp_tool({
  server_name: "metacognition-tools",
  tool_name: "generate_risk_dashboard",
  arguments: {
    dataDescription: "${randomDataDescription}"
  }
});
`);
console.log("\n");

console.log("--- Metacognition Review ---");
console.log(`Predictions: ${randomPredictionOutcome.predictions}`);
console.log(`Outcomes: ${randomPredictionOutcome.outcomes}`);
console.log("To use with MCP:");
console.log(`
use_mcp_tool({
  server_name: "metacognition-tools",
  tool_name: "metacognition_review",
  arguments: {
    predictions: "${randomPredictionOutcome.predictions}",
    outcomes: "${randomPredictionOutcome.outcomes}"
  }
});
`);

console.log("\n=== Test Complete ===");
console.log("The metacognition-tools MCP server is now available for use.");
console.log("You can use the tools through the MCP interface as shown above.");
