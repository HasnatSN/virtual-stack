import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect('postgresql://virtualstack:virtualstack@localhost:5433/virtualstack')
        result = await conn.fetch('SELECT email, is_superuser FROM iam.users;')
        print("Users in the database:")
        for row in result:
            print(f"Email: {row['email']}, Is Superuser: {row['is_superuser']}")
        await conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 