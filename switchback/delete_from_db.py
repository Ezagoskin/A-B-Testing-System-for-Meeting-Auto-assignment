import aiosqlite
import asyncio

async def delete_row() -> None:
    async with aiosqlite.connect("experiment_schedule.db") as db:
        query = f"DELETE FROM experiment_schedule WHERE region_id = 72 AND group_id = 0 LIMIT 1"
        async with db.execute(query) as cursor:
            await db.commit()
            
            print(cursor.rowcount == 1)

async def main():
    await delete_row()

asyncio.run(main())
