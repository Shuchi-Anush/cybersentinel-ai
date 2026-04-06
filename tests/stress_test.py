import time
import json
import statistics
import psutil
import requests
import sys
import subprocess
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tests.payload_factory import PayloadFactory

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
from src.core.paths import TESTING_ARTIFACTS_DIR

BASE_URL = "http://127.0.0.1:8081"
CONCURRENCY_LEVELS = [10, 50, 100, 250, 500]
DURATION_PER_LEVEL = 15

TESTING_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = TESTING_ARTIFACTS_DIR / "simulation_report.json"
SERVER_LOG = TESTING_ARTIFACTS_DIR / "server_test.log"

class StressOrchestrator:
    def __init__(self):
        self.factory = PayloadFactory()
        self.results = []
        self.server_process = None
        self.log_file = None

    def start_server(self):
        print(f"🚀 Starting CyberSentinel API on port 8081 (logging to {SERVER_LOG})...")
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        
        self.log_file = open(SERVER_LOG, "w")
        self.server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8081", "--no-access-log"],
            env=env,
            stdout=self.log_file,
            stderr=subprocess.STDOUT
        )
        
        for _ in range(60):
            try:
                resp = requests.get(f"{BASE_URL}/health", timeout=1.0)
                if resp.status_code == 200 and resp.json().get("pipeline_loaded"):
                    print("✅ API Server Ready.")
                    return True
            except:
                pass
            time.sleep(1)
        print("❌ Server failed to start.")
        return False

    def stop_server(self):
        if self.server_process:
            print("🛑 Stopping API Server...")
            self.server_process.terminate()
            self.server_process.wait()
            if self.log_file:
                self.log_file.close()

    def run_level(self, concurrency: int, duration: int):
        print(f"🔥 Simulating {concurrency} CCU for {duration}s...")
        
        latencies = []
        errors = 0
        total_req = 0
        start_time = time.time()
        
        process = psutil.Process(self.server_process.pid)
        cpu_usage = []
        mem_usage = []

        def worker_loop():
            nonlocal errors, total_req
            session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(pool_connections=concurrency, pool_maxsize=concurrency)
            session.mount("http://", adapter)
            
            while time.time() - start_time < duration:
                payload = self.factory.generate_single()
                t_req = time.time()
                try:
                    resp = session.post(f"{BASE_URL}/predict", json=payload, timeout=20.0)
                    if resp.status_code == 200:
                        latencies.append((time.time() - t_req) * 1000)
                    else:
                        errors += 1
                except Exception:
                    errors += 1
                total_req += 1

        def monitor():
            while time.time() - start_time < duration:
                try:
                    cpu_usage.append(process.cpu_percent(interval=0.5))
                    mem_usage.append(process.memory_info().rss / (1024 * 1024))
                except:
                    break

        with ThreadPoolExecutor(max_workers=concurrency + 1) as executor:
            executor.submit(monitor)
            worker_futures = [executor.submit(worker_loop) for _ in range(concurrency)]
            for _ in as_completed(worker_futures): pass
        
        total_duration = time.time() - start_time
        if not latencies:
            return {
                "concurrency_level": concurrency,
                "throughput": round(total_req / total_duration, 2),
                "latency_p50": 0, "latency_p95": 0, "latency_p99": 0,
                "error_rate_pct": 100, "cpu_usage_avg_pct": 0, "memory_usage_mb": 0
            }
            
        metrics = {
            "concurrency_level": concurrency,
            "throughput": round(total_req / total_duration, 2),
            "latency_p50": round(statistics.median(latencies), 2),
            "latency_p95": round(statistics.quantiles(latencies, n=20)[18], 2),
            "latency_p99": round(statistics.quantiles(latencies, n=100)[98], 2),
            "error_rate_pct": round((errors / (total_req or 1)) * 100, 2),
            "cpu_usage_avg_pct": round(sum(cpu_usage)/len(cpu_usage), 2) if cpu_usage else 0,
            "memory_usage_mb": round(sum(mem_usage)/len(mem_usage), 2) if mem_usage else 0
        }
        return metrics

def main():
    orchestrator = StressOrchestrator()
    if not orchestrator.start_server():
        return
    try:
        results = []
        for ccu in CONCURRENCY_LEVELS:
            m = orchestrator.run_level(ccu, DURATION_PER_LEVEL)
            results.append(m)
            print(f"📊 {ccu} CCU → {m['throughput']} req/s | p95: {m['latency_p95']}ms | Errors: {m['error_rate_pct']}% | CPU: {m['cpu_usage_avg_pct']}%")
            time.sleep(5)
        with open(REPORT_FILE, "w") as f:
            json.dump(results, f, indent=2)
    finally:
        orchestrator.stop_server()

if __name__ == "__main__":
    main()
