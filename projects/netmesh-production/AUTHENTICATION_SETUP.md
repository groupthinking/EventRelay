# Authentication Setup Guide

## 🎉 Quick Start - You're Ready to Login!

**Your test account is already set up!**

1. **Open**: http://localhost:5173
2. **Login with**:
   - Email: `garveyht@gmail.com`
   - Password: `TestPassword123!` (or your custom password)
3. **Done!** You should now have access to the application

---

## Detailed Setup Information

The netmesh-production app is configured for email/password authentication in development mode.

### ✅ ACCOUNT STATUS

A test account already exists for `garveyht@gmail.com`. You can login directly!

### Prerequisites

- Development server running at `http://localhost:5173`
- Email whitelist configured: `garveyht@gmail.com`

### Option 1: Login via Web UI (Easiest - Recommended)

1. Open http://localhost:5173 in your browser
2. Click "Sign Up" or "Register" button
3. Fill in the form:
   - Email: `garveyht@gmail.com`
   - Password: (choose a secure password)
   - Name: (optional)
4. Click "Create account"
5. You'll be automatically logged in

### Option 3: Manual API Registration

```bash
# Step 1: Get CSRF token
curl -c cookies.txt http://localhost:5173/api/auth/csrf-token

# Step 2: Register (replace CSRF_TOKEN with the token from step 1)
curl -b cookies.txt -X POST http://localhost:5173/api/auth/register \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: YOUR_CSRF_TOKEN" \
  -d '{
    "email": "garveyht@gmail.com",
    "password": "YourSecurePassword123!",
    "name": "Garvey"
  }'
```

## Current Configuration

### Authentication Methods

| Method | Status | Notes |
|--------|--------|-------|
| Email/Password | ✅ Enabled | Only `garveyht@gmail.com` allowed |
| Google OAuth | ❌ Disabled | Not configured in `.dev.vars` |
| GitHub OAuth | ❌ Disabled | Not configured in `.dev.vars` |

### Environment Variables

From `.dev.vars`:
```bash
ALLOWED_EMAIL="garveyht@gmail.com"  # Email whitelist
JWT_SECRET="dev-secret-key-change-in-prod-73289"
WEBHOOK_SECRET="dev-webhook-secret-89230"
```

## Production Setup (uvai.io)

### Domain Configuration

The app is configured to deploy to `uvai.io`:
- Production domain: `https://uvai.io`
- Cloudflare Zone ID: `a4ca65a8ca06e5d4de9b55f7b9a9a58c`

### OAuth Setup for Production

To enable OAuth in production:

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add authorized redirect URI: `https://uvai.io/api/auth/callback/google`
4. Add to Cloudflare Workers secrets:
   ```bash
   wrangler secret put GOOGLE_CLIENT_ID
   wrangler secret put GOOGLE_CLIENT_SECRET
   ```

#### GitHub OAuth
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Set callback URL: `https://uvai.io/api/auth/callback/github`
4. Add to Cloudflare Workers secrets:
   ```bash
   wrangler secret put GITHUB_CLIENT_ID
   wrangler secret put GITHUB_CLIENT_SECRET
   ```

## Security Features

- **CSRF Protection**: Double-submit cookie pattern
- **Email Whitelist**: Only allowed emails can register
- **Password Validation**: Enforced complexity requirements
- **Session Management**: 24-hour cookie-based sessions
- **Redirect Validation**: Prevents open redirect attacks

## Troubleshooting

### "Email already registered" error
The account already exists. Try logging in instead of registering.

### CSRF token errors
Make sure you're including cookies in your requests and using the latest CSRF token.

### Server not running
Start the development server:
```bash
cd projects/netmesh-production
npm run dev
```

### Port 5173 already in use
The server might be running on a different port (e.g., 5174). Check the terminal output for the actual port.

## API Endpoints

- `GET /api/auth/csrf-token` - Get CSRF token
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/profile` - Get current user profile
- `POST /api/auth/logout` - Logout current user
- `GET /api/auth/providers` - Get available auth providers