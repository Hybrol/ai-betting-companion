import subprocess
import sys
import os
import signal
import time

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=" * 65)
    print(" STARTING PORTUGUESE AI BETTING COMPANION & DASHBOARD")
    print("=" * 65)
    print(" Backend API:  http://localhost:8000")
    print(" Swagger Docs: http://localhost:8000/docs")
    print(" Web UI:       http://localhost:3000")
    print("=" * 65)
    print(" Press Ctrl+C at any time to shut down both services.\n")

    # Start Backend
    print("[RUNNER] Launching Backend (FastAPI + AI Engine + 30-min Cron)...")
    backend_cmd = [sys.executable, "run.py"]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        shell=False
    )

    # Start Frontend
    print("[RUNNER] Launching Frontend (Next.js Dashboard)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir,
        shell=False
    )

    def shutdown(signum=None, frame=None):
        print("\n[RUNNER] Shutting down services cleanly...")
        try:
            if backend_proc.poll() is None:
                backend_proc.terminate()
        except Exception:
            pass
        try:
            if frontend_proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], stderr=subprocess.DEVNULL)
                else:
                    frontend_proc.terminate()
        except Exception:
            pass
        print("[RUNNER] Services stopped. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            b_poll = backend_proc.poll()
            f_poll = frontend_proc.poll()
            if b_poll is not None:
                print(f"[RUNNER] Backend exited with code {b_poll}")
                shutdown()
            if f_poll is not None:
                print(f"[RUNNER] Frontend exited with code {f_poll}")
                shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()
