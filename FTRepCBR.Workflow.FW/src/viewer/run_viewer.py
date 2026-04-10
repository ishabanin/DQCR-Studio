"""Launch script for FW Workflow Viewer."""
import subprocess
import sys
import os
import time
from pathlib import Path


def kill_port(port):
    """Kill process on given port (Windows)."""
    try:
        result = subprocess.run('netstat -ano', capture_output=True, text=True, shell=True)
        for line in result.stdout.strip().split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    print(f'Killed process {pid} on port {port}')
    except:
        pass


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    frontend_dir = script_dir / "frontend"
    backend_port = 9001
    frontend_port = 3000
    
    print("=" * 50)
    print("FW Workflow Viewer")
    print("=" * 50)
    
    # Kill existing processes
    print("\nCleaning up ports...")
    kill_port(frontend_port)
    kill_port(backend_port)
    time.sleep(1)
    
    # Start backend
    print(f"\nStarting backend on port {backend_port}...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", 
        "FW.viewer.backend.main:app",
        "--port", str(backend_port),
        "--host", "127.0.0.1"
    ]
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(project_root)
    
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=str(project_root),
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    time.sleep(3)
    
    # Start frontend
    print(f"\nStarting frontend on port {frontend_port}...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "npm", "run", "dev", "--", "--port", str(frontend_port)],
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    print("\n" + "=" * 50)
    print(f"Frontend: http://localhost:{frontend_port}")
    print(f"Backend:  http://localhost:{backend_port}")
    print(f"API Docs: http://localhost:{backend_port}/docs")
    print("=" * 50)
    print("\nPress Ctrl+C to stop...")
    
    try:
        # Monitor processes
        while True:
            if backend_process.poll() is not None:
                print("\nBackend process died!")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        backend_process.terminate()
        frontend_process.terminate()
        kill_port(backend_port)
        kill_port(frontend_port)
        print("Done.")


if __name__ == "__main__":
    main()
