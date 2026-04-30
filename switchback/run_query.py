import aiosqlite
import asyncio

async def delete_rows():
    async with aiosqlite.connect("experiment_schedule.db") as db:
        query = f"DELETE FROM experiment_schedule WHERE region_id = 8938 or region_id = 9044"
        
        await db.execute(query)
        await db.commit()

async def main():
    await delete_rows() 

asyncio.run(main())

