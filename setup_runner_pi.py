import paramiko
import urllib.request
import json
import os
import sys

def get_runner_token():
    token = os.getenv('GITHUB_TOKEN') or (sys.argv[1] if len(sys.argv) > 1 else '')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable or command-line argument required")
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'DeployRunner'
    }
    req = urllib.request.Request(
        'https://api.github.com/repos/Hybrol/ai-betting-companion/actions/runners/registration-token',
        data=b'',
        headers=headers
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        return data.get('token')

def main():
    reg_token = get_runner_token()
    print("Obtained GitHub Runner Registration Token:", reg_token[:8] + "...")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.1.139", username="pi", password="joaojoao", timeout=10)

    def run_cmd(cmd, sudo=False, timeout=300):
        full_cmd = f"sudo {cmd}" if sudo else cmd
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore").strip()
        err = stderr.read().decode("utf-8", errors="ignore").strip()
        return out, err

    print("Configuring GitHub Actions Self-Hosted Runner on Raspberry Pi...")
    run_cmd("mkdir -p /home/pi/actions-runner")
    
    # Download ARM64 runner package if missing
    run_cmd("cd /home/pi/actions-runner && [ -f actions-runner.tar.gz ] || curl -o actions-runner.tar.gz -L https://github.com/actions/runner/releases/download/v2.338.2/actions-runner-linux-arm64-2.338.2.tar.gz")
    run_cmd("cd /home/pi/actions-runner && tar xzf actions-runner.tar.gz")
    
    # Install dependencies
    run_cmd("cd /home/pi/actions-runner && sudo ./bin/installdependencies.sh", sudo=True)
    
    # Configure runner
    cfg_cmd = f"cd /home/pi/actions-runner && ./config.sh --url https://github.com/Hybrol/ai-betting-companion --token {reg_token} --name raspberrypi --unattended --replace"
    out, err = run_cmd(cfg_cmd)
    print("Config result:", out)
    if err:
        print("Config err/notice:", err)

    # Install & start as systemd service
    run_cmd("cd /home/pi/actions-runner && sudo ./svc.sh install pi", sudo=True)
    run_cmd("cd /home/pi/actions-runner && sudo ./svc.sh start", sudo=True)
    out, _ = run_cmd("cd /home/pi/actions-runner && sudo ./svc.sh status", sudo=True)
    print("Runner service status:\n", out)

    client.close()
    print("\n[OK] GitHub Actions Self-Hosted Runner installed and active on Raspberry Pi!")

if __name__ == "__main__":
    main()
