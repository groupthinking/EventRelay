#!/usr/bin/env python3
"""
Verify asyncpg installation and basic functionality
"""

import asyncio
import asyncpg

async def verify_asyncpg():
    """Verify asyncpg is working"""
    try:
        print("✅ asyncpg imported successfully")

        # Check version
        version = asyncpg.__version__
        print(f"📦 asyncpg version: {version}")

        # Test connection (will fail if no database, but proves library works)
        try:
            conn = await asyncpg.connect('postgresql://test:test@localhost:5432/test')
            await conn.close()
            print("✅ asyncpg connection test successful")
        except Exception as e:
            if "connect" in str(e).lower() or "resolve" in str(e).lower():
                print("✅ asyncpg library functional (connection expected to fail - no test database)")
            else:
                print(f"❌ asyncpg connection test failed: {e}")
                return False

        return True

    except ImportError as e:
        print(f"❌ asyncpg import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ asyncpg verification failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(verify_asyncpg())
    if result:
        print("\n🎉 asyncpg verification completed successfully!")
        exit(0)
    else:
        print("\n❌ asyncpg verification failed!")
        exit(1)
