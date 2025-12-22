#!/usr/bin/env node

/**
 * Script to test login with the test account
 * Usage: node scripts/test-login.mjs [password]
 */

const BASE_URL = 'http://localhost:5173';
const EMAIL = 'garveyht@gmail.com';
const DEFAULT_PASSWORD = 'TestPassword123!';

async function testLogin() {
  const password = process.argv[2] || DEFAULT_PASSWORD;
  
  console.log('🔐 Testing login for netmesh-production...');
  console.log(`📧 Email: ${EMAIL}`);
  console.log('');

  try {
    // Step 1: Get CSRF token
    console.log('📝 Step 1: Getting CSRF token...');
    const csrfResponse = await fetch(`${BASE_URL}/api/auth/csrf-token`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!csrfResponse.ok) {
      throw new Error(`Failed to get CSRF token: ${csrfResponse.status}`);
    }

    const csrfData = await csrfResponse.json();
    const csrfToken = csrfData.data?.token;

    if (!csrfToken) {
      throw new Error('CSRF token not found in response');
    }

    console.log(`✅ CSRF Token obtained`);
    console.log('');

    // Step 2: Login
    console.log('📝 Step 2: Attempting login...');
    const loginResponse = await fetch(`${BASE_URL}/api/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify({
        email: EMAIL,
        password: password,
      }),
    });

    const loginData = await loginResponse.json();

    if (loginData.success) {
      console.log('✅ Login successful!');
      console.log('');
      console.log('👤 User Info:');
      console.log(`   ID: ${loginData.data.user.id}`);
      console.log(`   Email: ${loginData.data.user.email}`);
      console.log(`   Name: ${loginData.data.user.displayName}`);
      console.log(`   Provider: ${loginData.data.user.provider}`);
      console.log('');
      console.log('🎉 Authentication is working correctly!');
      console.log(`🌐 Visit: ${BASE_URL}`);
    } else {
      console.error('❌ Login failed');
      console.error('Response:', JSON.stringify(loginData, null, 2));
      
      if (loginData.error?.message?.includes('Invalid credentials')) {
        console.log('');
        console.log('💡 The password might be incorrect. Try:');
        console.log('   1. Using the password you set when registering');
        console.log('   2. Running: node scripts/test-login.mjs YOUR_PASSWORD');
      }
      
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Error testing login:', error.message);
    console.error('');
    console.error('💡 Make sure the development server is running at', BASE_URL);
    process.exit(1);
  }
}

testLogin();