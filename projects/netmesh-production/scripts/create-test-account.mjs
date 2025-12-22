#!/usr/bin/env node

/**
 * Script to create a test account for local development
 * Usage: node scripts/create-test-account.mjs
 */

const BASE_URL = 'http://localhost:5173';
const EMAIL = 'garveyht@gmail.com';
const PASSWORD = 'TestPassword123!';
const NAME = 'Garvey';

async function createTestAccount() {
  console.log('🔐 Creating test account for netmesh-production...');
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
      throw new Error(`Failed to get CSRF token: ${csrfResponse.status} ${csrfResponse.statusText}`);
    }

    const csrfData = await csrfResponse.json();
    const csrfToken = csrfData.data?.token;

    if (!csrfToken) {
      throw new Error('CSRF token not found in response');
    }

    console.log(`✅ CSRF Token obtained: ${csrfToken.substring(0, 20)}...`);
    console.log('');

    // Extract cookies from the response
    const cookies = csrfResponse.headers.get('set-cookie');

    // Step 2: Register the account
    console.log('📝 Step 2: Registering account...');
    const registerResponse = await fetch(`${BASE_URL}/api/auth/register`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
        ...(cookies ? { 'Cookie': cookies } : {}),
      },
      body: JSON.stringify({
        email: EMAIL,
        password: PASSWORD,
        name: NAME,
      }),
    });

    const registerData = await registerResponse.json();

    if (registerData.success) {
      console.log('✅ Account created successfully!');
      console.log('');
      console.log('🎉 You can now login with:');
      console.log(`   Email: ${EMAIL}`);
      console.log(`   Password: ${PASSWORD}`);
      console.log('');
      console.log(`🌐 Visit: ${BASE_URL}`);
      console.log('');
      console.log('✨ Setup complete!');
    } else {
      const errorMessage = registerData.error?.message || registerData.message || 'Unknown error';
      
      // Check if user already exists
      if (errorMessage.includes('already registered')) {
        console.log('');
        console.log('ℹ️  Account already exists!');
        console.log('');
        console.log('✅ You can login with:');
        console.log(`   Email: ${EMAIL}`);
        console.log('   Password: (use your existing password)');
        console.log('');
        console.log(`🌐 Visit: ${BASE_URL}`);
        console.log('');
        console.log('💡 If you forgot your password, you can:');
        console.log('   1. Check the password you used when registering');
        console.log('   2. Or use the default: TestPassword123!');
        console.log('');
        process.exit(0); // Exit successfully since account exists
      }
      
      console.error('❌ Registration failed');
      console.error('Response:', JSON.stringify(registerData, null, 2));
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Error creating test account:', error.message);
    console.error('');
    console.error('💡 Make sure the development server is running at', BASE_URL);
    console.error('   Run: npm run dev');
    process.exit(1);
  }
}

createTestAccount();