import asyncio
import aiohttp
import time
import argparse
from pathlib import Path

DEFAULT_URL_PATH = "/predict"


async def load_dataset(path: str) -> list[str]:
    p = Path(path)
    lines = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    if not lines:
        raise RuntimeError("Dataset file is empty")
    return lines


async def worker(
    worker_id: int,
    session: aiohttp.ClientSession,
    url: str,
    lines: list[str],
    delay_ms: int,
    total_requests: int,
    sent_lock: asyncio.Lock,
    sent_ref: dict,
    ok_ref: dict,
    responses_path: Path,
):
    idx = 0
    n = len(lines)
    delay_sec = delay_ms / 1000.0

    while True:
        async with sent_lock:
            if sent_ref["sent"] >= total_requests:
                break
            sent_ref["sent"] += 1
            current_num = sent_ref["sent"]

        ai_ipc_value = lines[idx]
        idx = (idx + 1) % n

        payload = {
            "patent_id": "RU-123",
            "ai_ipc": ai_ipc_value,
        }

        try:
            async with session.post(url, json=payload) as resp:
                text = await resp.text()
                if 200 <= resp.status < 300:
                    ok_ref["ok"] += 1

                with responses_path.open("a", encoding="utf-8") as rf:
                    rf.write(
                        f"#{current_num} worker={worker_id} "
                        f"status={resp.status} "
                        f"req_ai_ipc={ai_ipc_value!r} "
                        f"resp={text[:2000]}\n"
                    )
        except Exception as e:
            with responses_path.open("a", encoding="utf-8") as rf:
                rf.write(
                    f"#{current_num} worker={worker_id} ERR {type(e).__name__}: {e}\n"
                )

        if delay_sec > 0:
            await asyncio.sleep(delay_sec)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        required=True,
        help="host:port балансера или локального проброса, напр. 127.0.0.1:8002",
    )
    parser.add_argument(
        "--path",
        default=DEFAULT_URL_PATH,
        help="Путь эндпоинта, по умолчанию /predict",
    )
    parser.add_argument(
        "--dataset",
        default="ai-ipc.txt",
        help="Путь к файлу с наборами ai_ipc",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=10,
        help="Количество параллельных воркеров",
    )
    parser.add_argument(
        "--delay_ms",
        type=int,
        default=0,
        help="Задержка между вызовами в миллисекундах для каждого воркера",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=1000,
        help="Сколько всего запросов отправить (по всем воркерам суммарно)",
    )
    parser.add_argument(
        "--responses_file",
        default="out/responses.log",
        help="Файл для логирования ответов",
    )
    args = parser.parse_args()

    url = f"http://{args.host}{args.path}"
    lines = await load_dataset(args.dataset)

    responses_path = Path(args.responses_file)
    if responses_path.exists():
        responses_path.unlink()

    sent_ref = {"sent": 0}
    ok_ref = {"ok": 0}
    sent_lock = asyncio.Lock()

    start = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            asyncio.create_task(
                worker(
                    worker_id=i,
                    session=session,
                    url=url,
                    lines=lines,
                    delay_ms=args.delay_ms,
                    total_requests=args.total,
                    sent_lock=sent_lock,
                    sent_ref=sent_ref,
                    ok_ref=ok_ref,
                    responses_path=responses_path,
                )
            )
            for i in range(args.threads)
        ]
        await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    print(f"Total sent: {sent_ref['sent']}")
    print(f"Total ok responses (2xx): {ok_ref['ok']}")
    print(f"Total time: {elapsed:.2f} s")
    if elapsed > 0:
        print(f"RPS: {sent_ref['sent'] / elapsed:.2f}")


if __name__ == "__main__":
    asyncio.run(main())