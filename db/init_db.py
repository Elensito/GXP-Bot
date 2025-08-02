import aiosqlite
import asyncio

DB_PATH = "db/gxp_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS gxp (
            user_id TEXT,
            ign TEXT,
            date TEXT,
            daily_gxp INTEGER,
            weekly_gxp INTEGER,
            monthly_gxp INTEGER,
            lifetime_gxp INTEGER,
            activity_points REAL,
            PRIMARY KEY (user_id, date)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_map (
            discord_id TEXT PRIMARY KEY,
            uuid TEXT,
            ign TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS shop (
            user_id TEXT,
            item TEXT,
            amount INTEGER,
            PRIMARY KEY (user_id, item)
        )
        """)
        await db.commit()

if __name__ == "__main__":
    asyncio.run(init_db())
