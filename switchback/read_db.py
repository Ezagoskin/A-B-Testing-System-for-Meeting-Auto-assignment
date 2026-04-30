import aiosqlite
import asyncio

async def read():
    async with aiosqlite.connect("experiment_schedule.db") as db:
        query = f"SELECT * FROM experiment_schedule"
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            
            if rows:
                for row in rows:
                    print(row)  # Print each row
            else:
                print(f"No rows found in table {table_name}")

async def main():
    await read() 

# Run the async function
asyncio.run(main())
