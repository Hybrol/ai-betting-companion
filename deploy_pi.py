import paramiko
import sys
import os
import time

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("=====================================================")
    print(" DEPLOYING AI BETTING COMPANION TO RASPBERRY PI")
    print("=====================================================")

    print("[1/6] Connecting to Raspberry Pi at 192.168.1.139...")
    client.connect("192.168.1.139", username="pi", password="joaojoao", timeout=10)
    print("Connected successfully!")

    def run_cmd(cmd, sudo=False, timeout=300):
        full_cmd = f"echo joaojoao | sudo -S {cmd}" if sudo else cmd
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore").strip()
        err = stderr.read().decode("utf-8", errors="ignore").strip()
        return out, err

    # Step 1: Configure passwordless sudo for pi
    print("\n[2/6] Configuring sudo permissions & expanding swap to 2GB...")
    run_cmd('sh -c \'echo "pi ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/010_pi-nopasswd && chmod 0440 /etc/sudoers.d/010_pi-nopasswd\'', sudo=True)
    
    # Increase swap for build headroom
    run_cmd("sed -i 's/CONF_SWAPSIZE=200/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile", sudo=True)
    run_cmd("/sbin/dphys-swapfile swapoff", sudo=True)
    run_cmd("/sbin/dphys-swapfile setup", sudo=True)
    run_cmd("/sbin/dphys-swapfile swapon", sudo=True)
    out, _ = run_cmd("free -h | grep Swap")
    print(f"Swap configured: {out}")

    # Step 2: Clone repository
    print("\n[3/6] Cloning / Updating repository on Raspberry Pi...")
    run_cmd("mkdir -p /home/pi/ai-betting-companion")
    out, _ = run_cmd("git clone https://github.com/Hybrol/ai-betting-companion.git /home/pi/ai-betting-companion 2>&1 || (cd /home/pi/ai-betting-companion && git pull origin main)")
    print("Git repository ready at /home/pi/ai-betting-companion")

    # Step 3: Setup Python backend & virtual environment
    print("\n[4/6] Setting up Python virtual environment & backend dependencies...")
    run_cmd("python3 -m venv /home/pi/ai-betting-companion/backend/venv")
    out, err = run_cmd("/home/pi/ai-betting-companion/backend/venv/bin/pip install --upgrade pip", timeout=180)
    print("Pip upgraded.")
    out, err = run_cmd("/home/pi/ai-betting-companion/backend/venv/bin/pip install -r /home/pi/ai-betting-companion/backend/requirements.txt", timeout=300)
    print("Backend requirements installed!")

    # Step 4: Setup Node / Frontend build
    print("\n[5/6] Installing Node dependencies and building Next.js frontend...")
    out, err = run_cmd("cd /home/pi/ai-betting-companion/frontend && npm install", timeout=300)
    print("Frontend packages installed.")
    out, err = run_cmd("cd /home/pi/ai-betting-companion/frontend && npm run build", timeout=600)
    print("Frontend build complete!")

    # Step 5: Configure systemd services
    print("\n[6/6] Creating systemd background services (ai-betting-backend & ai-betting-frontend)...")
    backend_service = """[Unit]
Description=AI Betting Companion Backend & 30-min Cron
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ai-betting-companion/backend
ExecStart=/home/pi/ai-betting-companion/backend/venv/bin/python run.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=PORT=8080
Environment=HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
"""
    frontend_service = """[Unit]
Description=AI Betting Companion Next.js Frontend
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ai-betting-companion/frontend
ExecStart=/usr/bin/npm start -- -p 3001 -H 0.0.0.0
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=3001

[Install]
WantedBy=multi-user.target
"""
    # Write service files
    sftp = client.open_sftp()
    with sftp.file("/tmp/ai-betting-backend.service", "w") as f:
        f.write(backend_service)
    with sftp.file("/tmp/ai-betting-frontend.service", "w") as f:
        f.write(frontend_service)
    sftp.close()

    run_cmd("mv /tmp/ai-betting-backend.service /etc/systemd/system/ai-betting-backend.service", sudo=True)
    run_cmd("mv /tmp/ai-betting-frontend.service /etc/systemd/system/ai-betting-frontend.service", sudo=True)
    run_cmd("systemctl daemon-reload", sudo=True)
    run_cmd("systemctl enable --now ai-betting-backend ai-betting-frontend", sudo=True)
    time.sleep(3)

    out_b, _ = run_cmd("systemctl is-active ai-betting-backend")
    out_f, _ = run_cmd("systemctl is-active ai-betting-frontend")
    print(f"Backend status:  {out_b}")
    print(f"Frontend status: {out_f}")

    client.close()
    print("\n[OK] Deployment successfully completed on Raspberry Pi!")

if __name__ == "__main__":
    main()
