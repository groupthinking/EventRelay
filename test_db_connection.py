import os
import asyncio
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check_connection():
    db_url = os.getenv("DATABASE_URL")
    print(f"Testing connection to: {db_url}")
    try:
        conn = await asyncpg.connect(db_url)
        print("Successfully connected!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_connection())
