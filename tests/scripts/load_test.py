#!/usr/bin/env python3
"""
Script de test de charge pour ShotURL
Teste les performances avec plusieurs requetes simultanees
"""

import asyncio
import aiohttp
import time
from datetime import datetime
import json
import sys

# Configuration
VM_HOST = "192.168.56.102"
VM_PORT = 8000
BASE_URL = f"http://{VM_HOST}:{VM_PORT}"

# URLs de test
TEST_URLS = [
    "https://www.twitch.tv/gotaga",
]


async def capture_url(session, url, test_id):
    """Capture une URL et mesure le temps"""
    start_time = time.time()

    payload = {
        "url": url,
        "full_page": False,
        "device": "desktop",
        "delay": 0,
        "grab_html": False
    }

    try:
        print(f"[{test_id}] Starting capture: {url}")
        async with session.post(
            f"{BASE_URL}/api/capture",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            elapsed = time.time() - start_time

            if response.status == 200:
                data = await response.json()
                print(f"[{test_id}]  Completed in {elapsed:.2f}s: {url}")
                return {
                    "test_id": test_id,
                    "url": url,
                    "status": "success",
                    "elapsed": elapsed,
                    "screenshot_size": len(data.get("screenshot", "")),
                    "network_logs": len(data.get("network_logs", [])),
                }
            else:
                error_text = await response.text()
                print(f"[{test_id}]  Failed ({response.status}) in {elapsed:.2f}s: {url}")
                return {
                    "test_id": test_id,
                    "url": url,
                    "status": "error",
                    "elapsed": elapsed,
                    "error": f"HTTP {response.status}: {error_text[:100]}"
                }
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"[{test_id}]  Timeout after {elapsed:.2f}s: {url}")
        return {
            "test_id": test_id,
            "url": url,
            "status": "timeout",
            "elapsed": elapsed,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{test_id}]  Exception after {elapsed:.2f}s: {url} - {str(e)}")
        return {
            "test_id": test_id,
            "url": url,
            "status": "exception",
            "elapsed": elapsed,
            "error": str(e)
        }


async def run_concurrent_test(num_requests):
    """Lance plusieurs captures simultanees"""
    print(f"\n{'='*60}")
    print(f"Test de charge: {num_requests} requetes simultanees")
    print(f"Target: {BASE_URL}")
    print(f"{'='*60}\n")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        # Creer les taches
        tasks = []
        for i in range(num_requests):
            url = TEST_URLS[i % len(TEST_URLS)]
            tasks.append(capture_url(session, url, i + 1))

        # Executer toutes les taches en parallele
        results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    # Analyser les resultats
    print(f"\n{'='*60}")
    print("RESULTATS")
    print(f"{'='*60}\n")

    success = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]
    timeouts = [r for r in results if r["status"] == "timeout"]
    exceptions = [r for r in results if r["status"] == "exception"]

    print(f"Total requests: {num_requests}")
    print(f"Success: {len(success)} ({len(success)/num_requests*100:.1f}%)")
    print(f"Errors: {len(errors)} ({len(errors)/num_requests*100:.1f}%)")
    print(f"Timeouts: {len(timeouts)} ({len(timeouts)/num_requests*100:.1f}%)")
    print(f"Exceptions: {len(exceptions)} ({len(exceptions)/num_requests*100:.1f}%)")

    if success:
        times = [r["elapsed"] for r in success]
        print(f"\nTiming (successful requests):")
        print(f"  First completed: {min(times):.2f}s")
        print(f"  Last completed: {max(times):.2f}s")
        print(f"  Average: {sum(times)/len(times):.2f}s")
        print(f"  Total test time: {total_time:.2f}s")

    # Sauvegarder les resultats
    report = {
        "timestamp": datetime.now().isoformat(),
        "num_requests": num_requests,
        "total_time": total_time,
        "results": results,
        "summary": {
            "success": len(success),
            "errors": len(errors),
            "timeouts": len(timeouts),
            "exceptions": len(exceptions),
        }
    }

    filename = f"load_test_{num_requests}req_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nRapport sauvegarde: {filename}\n")

    return results


async def check_health():
    """Verifie que le service est disponible"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/health", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f" Service is healthy")
                    print(f"  Status: {data.get('status')}")
                    print(f"  Active sessions: {data.get('active_sessions')}")
                    return True
                else:
                    print(f" Service returned status {response.status}")
                    return False
    except Exception as e:
        print(f" Cannot reach service: {e}")
        return False


async def main():
    """Point d'entree principal"""
    # Verifier le nombre de requetes
    num_requests = 10
    if len(sys.argv) > 1:
        try:
            num_requests = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [num_requests]")
            sys.exit(1)

    # Verifier la sante du service
    print(f"Checking service at {BASE_URL}...\n")
    if not await check_health():
        print("\n Service is not available. Please check if Docker is running.")
        sys.exit(1)

    print("\nStarting load test in 3 seconds...")
    await asyncio.sleep(3)

    # Lancer le test
    await run_concurrent_test(num_requests)


if __name__ == "__main__":
    asyncio.run(main())
