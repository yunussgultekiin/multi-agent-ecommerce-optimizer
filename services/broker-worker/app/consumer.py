import asyncio
import json
import logging
import os

import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


async def start_consumer() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    agent_worker_url = os.getenv("AGENT_WORKER_URL", "http://agent-worker:8080")

    client = aioredis.from_url(redis_url)
    logger.info("broker-worker consumer connected to Redis, polling 'tasks' queue")

    while True:
        try:
            result = await client.blpop("tasks", timeout=5)
            if result is None:
                continue

            _, raw = result
            task: dict = json.loads(raw)
            task_id = task.get("task_id", "unknown")
            logger.info("Received task: task_id=%s", task_id)

            async with httpx.AsyncClient(timeout=5.0) as http:
                await http.post(f"{agent_worker_url}/run", json=task)

        except Exception as exc:
            logger.error("Consumer error: %s", exc)
            await asyncio.sleep(1)
