#!/usr/bin/env python3
"""Замер скорости скачивания: N последовательных запросов к одному URL.

Использует только стандартную библиотеку Python 3.8+.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request

CHUNK_SIZE = 64 * 1024  # читаем ответ кусками по 64 КиБ
USER_AGENT = "download-speed-test/1.0"


def fetch(url: str, timeout: float) -> tuple[int, float]:
    """Скачивает URL целиком. Возвращает (байт получено, секунд затрачено)."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            # Просим не кешировать, чтобы каждый запрос реально шёл на сервер
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            # Без сжатия: считаем реальные байты, а не распакованные
            "Accept-Encoding": "identity",
        },
    )
    received = 0
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            received += len(chunk)
    elapsed = time.perf_counter() - start
    return received, elapsed


def human_bytes(n: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1000 or unit == "ГБ":
            return f"{n:.2f} {unit}" if unit != "Б" else f"{int(n)} {unit}"
        n /= 1000
    return f"{n:.2f} ГБ"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Делает N последовательных запросов к URL и считает скорость скачивания."
    )
    parser.add_argument("url", help="адрес, к которому стучаться (например, тяжёлая картинка)")
    parser.add_argument("-n", "--count", type=int, default=10,
                        help="сколько запросов сделать (по умолчанию 10)")
    parser.add_argument("-t", "--timeout", type=float, default=60.0,
                        help="таймаут одного запроса в секундах (по умолчанию 60)")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count должен быть >= 1")
    if not args.url.startswith(("http://", "https://")):
        parser.error("URL должен начинаться с http:// или https://")

    print(f"URL: {args.url}")
    print(f"Запросов: {args.count}\n")

    total_bytes = 0
    total_time = 0.0

    for i in range(1, args.count + 1):
        try:
            size, elapsed = fetch(args.url, args.timeout)
        except urllib.error.HTTPError as e:
            print(f"Запрос {i}: ошибка HTTP {e.code} {e.reason}", file=sys.stderr)
            return 1
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            print(f"Запрос {i}: не удалось выполнить запрос: {reason}", file=sys.stderr)
            return 1

        total_bytes += size
        total_time += elapsed
        speed = size / elapsed / 1_000_000 if elapsed > 0 else 0.0
        print(f"Запрос {i:>2}: {human_bytes(size):>10}  за {elapsed:7.3f} с  ({speed:.2f} МБ/с)")

    avg_time = total_time / args.count
    speed_mb_s = total_bytes / total_time / 1_000_000 if total_time > 0 else 0.0
    speed_mbit_s = speed_mb_s * 8

    print("\n--- Итог ---")
    print(f"Среднее время запроса: {avg_time:.3f} с")
    print(f"Всего скачано:         {total_bytes} байт ({human_bytes(total_bytes)})")
    print(f"Скорость скачивания:   {speed_mb_s:.2f} МБ/с ({speed_mbit_s:.2f} Мбит/с)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем", file=sys.stderr)
        sys.exit(130)
