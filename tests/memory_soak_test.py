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
from payload_factory import PayloadFactory

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8081"
CONCURRENCY = 100
DURATION = 300 # 5 minutes
REPORT_FILE = "memory_soak_report.json"

class SoakOrchestrator:
    def __init__(self):
        self.factory = PayloadFactory()
        self.server_process = None

    def start_server(self):
        print("🚀 Starting CyberSentinel API for Memory Soak...")
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        self.server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8081", "--no-access-log"],
            env=env
        )
        for _ in range(60):
            try:
                resp = requests.get(f"{BASE_URL}/health", timeout=1.0)
                if resp.status_code == 200 and resp.json().get("pipeline_loaded"):
                    print("✅ API Server Ready.")
                    return True
            except: pass
            time.sleep(1)
        return False

    def stop_server(self):
        if self.server_process:
            self.server_process.terminate()

    def run_soak(self):
        print(f"⌛ Running Soak Test (CCU={CONCURRENCY}, Duration={DURATION}s)...")
        start_time = time.time()
        process = psutil.Process(self.server_process.pid)
        cpu_history = []
        mem_history = []
        
        def worker():
            session = requests.Session()
            while time.time() - start_time < DURATION:
                try:
                    payload = self.factory.generate_single()
                    session.post(f"{BASE_URL}/predict", json=payload, timeout=10)
                except: pass

        with ThreadPoolExecutor(max_workers=CONCURRENCY + 1) as executor:
            # Monitor
            def monitor():
                while time.time() - start_time < DURATION:
                    try:
                        cpu_history.append(process.cpu_percent(interval=1.0))
                        mem_history.append(process.memory_info().rss / (1024 * 1024))
                    except: break
                    time.sleep(1)
            
            executor.submit(monitor)
            [executor.submit(worker) for _ in range(CONCURRENCY)]
            
        return {
            "initial_mem": mem_history[0] if mem_history else 0,
            "final_mem": mem_history[-1] if mem_history else 0,
            "avg_cpu": sum(cpu_history)/len(cpu_history) if cpu_history else 0,
            "mem_growth": mem_history[-1] - mem_history[0] if len(mem_history) > 1 else 0
        }

def main():
    s = SoakOrchestrator()
    if s.start_server():
        res = s.run_soak()
        print(f"📊 Soak Complete: Growth={res['mem_growth']:.2f} MB | Final={res['final_mem']:.2f} MB")
        with open(REPORT_FILE, "w") as f:
            json.dump(res, f, indent=2)
        s.stop_server()

if __name__ == "__main__": main()
