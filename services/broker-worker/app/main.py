import asyncio
import logging
from app.health import start_health_server
from app.consumer import start_consumer


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    await asyncio.gather(start_health_server(), start_consumer())


if __name__ == "__main__":
    asyncio.run(main())
