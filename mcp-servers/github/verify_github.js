const https = require('https');

const token = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;

if (!token) {
    console.error('Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable is not set.');
    process.exit(1);
}

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
      process.exit(1);
    }
  });
});

req.on('error', (error) => {
  console.error('Error testing GitHub token:', error);
  process.exit(1);
});

req.end();
