from src.automation import BrightDataFullAutomation
import asyncio


async def main():
    automation = BrightDataFullAutomation()
    await automation.run()


if __name__ == "__main__":
    asyncio.run(main())
