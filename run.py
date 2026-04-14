#!/usr/bin/env python
"""
Launch the TracePilot backend and frontend together in one command.

Usage:
    python run.py
"""

import subprocess
import sys
import time
import signal
import os

BACKEND_CMD = [sys.executable, "-m", "uvicorn", "backend.main:app", "--reload", "--port", "8000"]
FRONTEND_CMD = [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.headless", "true"]

procs: list[subprocess.Popen] = []


def shutdown(sig=None, frame=None):
    print("\nShutting down...")
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    print("=" * 50)
    print("  TracePilot - Starting all services")
    print("=" * 50)

    # Start backend
    print("\n[1/2] Starting backend (FastAPI) on http://localhost:8000 ...")
    procs.append(subprocess.Popen(BACKEND_CMD))

    # Give backend a moment to bind the port
    time.sleep(2)

    # Start frontend
    print("[2/2] Starting frontend (Streamlit) on http://localhost:8501 ...")
    procs.append(subprocess.Popen(FRONTEND_CMD))

    print("\n" + "-" * 50)
    print("  Backend  -> http://localhost:8000")
    print("  Frontend -> http://localhost:8501")
    print("  API docs -> http://localhost:8000/docs")
    print("-" * 50)
    print("Press Ctrl+C to stop all services.\n")

    # Wait for either process to exit
    try:
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    print(f"Process exited with code {ret}, shutting down...")
                    shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()
