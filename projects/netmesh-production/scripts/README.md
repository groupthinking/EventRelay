# Authentication Scripts

## Available Scripts

### create-test-account.mjs
Creates a test account for local development.

```bash
node scripts/create-test-account.mjs
```

**Default credentials**:
- Email: `garveyht@gmail.com`
- Password: `TestPassword123!`
- Name: Garvey

**Note**: If the account already exists, the script will inform you and exit successfully.

### create-test-account.sh
Bash version of the account creation script (Mac/Linux only).

```bash
./scripts/create-test-account.sh
```

### test-login.mjs
Tests login functionality with the test account.

```bash
# Use default password
node scripts/test-login.mjs

# Use custom password
node scripts/test-login.mjs YOUR_PASSWORD
```

## Quick Start

The easiest way to access the application:

1. Make sure the dev server is running: `npm run dev`
2. Open http://localhost:5173 in your browser
3. Login with:
   - Email: `garveyht@gmail.com`
   - Password: `TestPassword123!` (or your custom password)

## Troubleshooting

### Account already exists
This is expected! Just login with your existing credentials.

### CSRF validation errors
Use the browser UI instead of API scripts. The browser handles cookies automatically.

### Server not running
Start the development server:
```bash
npm run dev
```