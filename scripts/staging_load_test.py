import argparse
import asyncio
import collections
import statistics
import time

import httpx
from redis import Redis


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18020/max/webhook")
    parser.add_argument("--secret", default="staging-secret")
    parser.add_argument("--broker", default="redis://127.0.0.1:16379/1")
    parser.add_argument("--metrics", default="http://127.0.0.1:19001/metrics")
    parser.add_argument("--messages", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--drain-timeout", type=float, default=180.0)
    return parser.parse_args()


async def submit_messages(args):
    semaphore = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(30.0, connect=10.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        async def send_message(index: int):
            payload = {
                "update_type": "message_created",
                "timestamp": 1_800_000_000_000 + index,
                "message": {
                    "sender": {"user_id": 10_000 + index, "is_bot": False},
                    "recipient": {"chat_id": 20_000 + index, "chat_type": "dialog"},
                    "body": {"mid": f"staging-{index}", "text": "Какая программа?"},
                },
            }
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.post(
                        args.url,
                        headers={"X-Max-Bot-Api-Secret": args.secret},
                        json=payload,
                    )
                    return response.status_code, time.perf_counter() - started, None
                except httpx.HTTPError as exc:
                    return None, time.perf_counter() - started, type(exc).__name__

        started = time.perf_counter()
        results = await asyncio.gather(
            *(send_message(index) for index in range(args.messages))
        )
        submit_seconds = time.perf_counter() - started

    return results, submit_seconds


async def wait_for_drain(args, broker: Redis):
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.perf_counter() - started < args.drain_timeout:
            metrics = (await client.get(args.metrics)).json()
            queue_length = broker.llen("answers")
            if (
                queue_length == 0
                and metrics.get("openai_responses") == args.messages
                and metrics.get("max_actions") == args.messages
                and metrics.get("max_messages") == args.messages
            ):
                return time.perf_counter() - started, metrics
            await asyncio.sleep(0.2)
    raise TimeoutError("staging queues did not drain before timeout")


async def main():
    args = parse_args()
    broker = Redis.from_url(args.broker, decode_responses=True)
    results, submit_seconds = await submit_messages(args)

    statuses = collections.Counter(
        status for status, _, _ in results if status is not None
    )
    errors = collections.Counter(error for _, _, error in results if error)
    latencies = sorted(latency for _, latency, _ in results)

    drain_seconds, metrics = await wait_for_drain(args, broker)
    total_seconds = submit_seconds + drain_seconds

    def percentile(fraction: float) -> float:
        index = round((len(latencies) - 1) * fraction)
        return latencies[index]

    print(f"messages={args.messages} concurrency={args.concurrency}")
    print(f"statuses={dict(statuses)} errors={dict(errors)}")
    print(
        f"submit_seconds={submit_seconds:.3f} "
        f"submit_rps={args.messages / submit_seconds:.1f}"
    )
    print(
        f"webhook_latency_p50={statistics.median(latencies):.4f}s "
        f"p95={percentile(0.95):.4f}s p99={percentile(0.99):.4f}s"
    )
    print(f"drain_seconds={drain_seconds:.3f} total_seconds={total_seconds:.3f}")
    print(f"stub_metrics={metrics}")
    print(f"answers_queue={broker.llen('answers')}")


if __name__ == "__main__":
    asyncio.run(main())
