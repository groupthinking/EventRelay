#!/usr/bin/env node

const https = require('https');

const token = 'YOUR_GITHUB_TOKEN_HERE';

const options = {
  hostname: 'api.github.com',
  path: '/user',
  method: 'GET',
  headers: {
    'User-Agent': 'GitHub-MCP-Server-Test',
    'Authorization': `token ${token}`,
    'Accept': 'application/vnd.github.v3+json'
  }
};

const req = https.request(options, (res) => {
  console.log(`Status: ${res.statusCode}`);
  
  let data = '';
  
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    if (res.statusCode === 200) {
      console.log('GitHub token is valid!');
      const userData = JSON.parse(data);
      console.log(`Authenticated as: ${userData.login}`);
      console.log(`User ID: ${userData.id}`);
    } else {
      console.log('GitHub token validation failed:');
      console.log(data);
    }
  });
});

req.on('error', (error) => {
  console.error('Error testing GitHub token:', error);
});

req.end();
