#!/usr/bin/env python3
"""
Setup script for deployment tokens.
This script helps configure environment variables for testing real deployments.
"""

import getpass
import os
from pathlib import Path


def setup_vercel_token():
    """Set up Vercel API token"""
    print("\n🔧 Setting up Vercel Token")
    print("   1. Go to: https://vercel.com/account/tokens")
    print("   2. Create a new token with deployment permissions")
    print("   3. Copy the token value")

    token = getpass.getpass("   Enter your Vercel token (or press Enter to skip): ").strip()

    if token:
        os.environ['VERCEL_TOKEN'] = token
        print("   ✅ VERCEL_TOKEN set for this session")
        return True
    else:
        print("   ⏭️  Skipped Vercel token setup")
        return False

def setup_github_token():
    """Set up GitHub API token"""
    print("\n🔧 Setting up GitHub Token")
    print("   1. Go to: https://github.com/settings/tokens")
    print("   2. Create a new token with 'repo' permissions")
    print("   3. Copy the token value")

    token = getpass.getpass("   Enter your GitHub token (or press Enter to skip): ").strip()

    if token:
        os.environ['GITHUB_TOKEN'] = token
        print("   ✅ GITHUB_TOKEN set for this session")
        return True
    else:
        print("   ⏭️  Skipped GitHub token setup")
        return False

def save_env_file():
    """Save tokens to a local .env file for persistence"""
    env_file = Path('.env')

    print("\n💾 Saving tokens to .env file...")
    print("   ⚠️  WARNING: This will create a .env file in your project root")
    print("   ⚠️  Make sure to add .env to your .gitignore file!")
    print("   ⚠️  Never commit .env files to version control!")

    save = input("   Do you want to save tokens to .env file? (y/N): ").strip().lower()

    if save == 'y':
        env_content = "# UVAI Deployment Tokens\n"
        env_content += "# WARNING: Never commit this file to version control!\n\n"

        for var in ['VERCEL_TOKEN', 'GITHUB_TOKEN', 'NETLIFY_AUTH_TOKEN', 'FLY_API_TOKEN']:
            value = os.environ.get(var)
            if value:
                env_content += f"{var}={value}\n"

        with open(env_file, 'w') as f:
            f.write(env_content)

        # Set proper permissions (readable only by owner)
        env_file.chmod(0o600)

        print("   ✅ Tokens saved to .env file")
        print("   📝 Don't forget to add .env to .gitignore!")
    else:
        print("   ⏭️  Skipped saving to .env file")

def check_gitignore():
    """Check if .env is in .gitignore"""
    gitignore = Path('.gitignore')

    if gitignore.exists():
        with open(gitignore, 'r') as f:
            content = f.read()

        if '.env' in content:
            print("   ✅ .env is already in .gitignore")
        else:
            print("   ⚠️  .env is NOT in .gitignore - you should add it!")
            print("   Run: echo '.env' >> .gitignore")
    else:
        print("   ⚠️  No .gitignore file found")
        print("   Create one with: echo '.env' > .gitignore")

def show_current_status():
    """Show current token status"""
    print("\n📊 Current Token Status:")

    tokens = {
        'VERCEL_TOKEN': 'Vercel deployments',
        'GITHUB_TOKEN': 'GitHub repository creation',
        'NETLIFY_AUTH_TOKEN': 'Netlify deployments',
        'FLY_API_TOKEN': 'Fly.io deployments'
    }

    ready_platforms = []

    for token, purpose in tokens.items():
        status = "✅ SET" if os.environ.get(token) else "❌ MISSING"
        print(f"   {token}: {status} ({purpose})")
        if os.environ.get(token):
            ready_platforms.append(token.split('_')[0].lower())

    print(f"\n🚀 Ready for deployments: {', '.join(ready_platforms) if ready_platforms else 'None'}")

    if ready_platforms:
        print("\n🎯 You can now test real deployments!")
        print("   Run: python3 scripts/test_live_deployment.py")
    else:
        print("\n💡 No tokens configured yet.")
        print("   Run this setup script again or set environment variables manually")

def main():
    """Main setup function"""
    print("🔐 UVAI Deployment Token Setup")
    print("=" * 40)
    print("This script will help you configure API tokens for deployment testing.")
    print("Tokens are only stored in memory for this session unless you choose to save them.")
    print()

    # Setup tokens
    vercel_ready = setup_vercel_token()
    github_ready = setup_github_token()

    # Show status
    show_current_status()

    # Save option
    if vercel_ready or github_ready:
        save_env_file()

    # Check gitignore
    check_gitignore()

    print("\n" + "=" * 40)
    print("🎉 Setup complete!")
    print()
    print("Next steps:")
    print("1. Test with: python3 scripts/test_live_deployment.py")
    print("2. For real deployments, make sure tokens have proper permissions")
    print("3. Monitor your API usage on each platform's dashboard")
    print()
    print("Security reminder:")
    print("- Never commit API tokens to version control")
    print("- Use environment variables in production")
    print("- Rotate tokens regularly")

if __name__ == '__main__':
    main()
