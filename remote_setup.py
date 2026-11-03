# -*- coding: utf-8 -*-
"""远程连接Linux服务器，检查并安装Docker，启动MySQL/Redis/Chroma容器"""
import paramiko
import sys
import os
import io

# 强制UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = "192.168.150.104"
USERS = [
    ("xiaodu", "123456"),
    ("root", "123456"),
]

def try_connect(host, username, password):
    """尝试SSH连接"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\n>>> 尝试连接 {username}@{host} ...")
    try:
        client.connect(
            host,
            username=username,
            password=password,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
        print(f"[OK] 连接成功! 当前用户: {username}")
        return client
    except paramiko.AuthenticationException as e:
        print(f"[FAIL] 认证失败: {e}")
        return None
    except Exception as e:
        print(f"[FAIL] 连接失败 ({type(e).__name__}): {e}")
        return None

def run_cmd(client, cmd, desc=""):
    """执行命令并打印输出"""
    if desc:
        print(f"\n--- {desc} ---")
    print(f"    $ {cmd[:100]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        # 打印前500字符
        lines = out.split('\n')
        for line in lines[:20]:
            print(f"    {line}")
        if len(lines) > 20:
            print(f"    ... (共{len(lines)}行)")
    if err:
        print(f"    [stderr] {err[:200]}")
    return out, err

def run_sudo(client, cmd, desc="", password="123456"):
    """执行sudo命令"""
    if desc:
        print(f"\n--- {desc} ---")
    print(f"    $ sudo {cmd[:100]}")

    full_cmd = f"echo '{password}' | sudo -S {cmd}"
    stdin, stdout, stderr = client.exec_command(full_cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    # 过滤掉sudo的密码提示
    if err and 'password' not in err.lower():
        print(f"    [stderr] {err[:200]}")
    lines = out.split('\n')
    for line in lines[:20]:
        print(f"    {line}")
    if len(lines) > 20:
        print(f"    ... (共{len(lines)}行)")
    return out, err

# ==================== 主流程 ====================

print("=" * 60)
print("远程服务器环境检测")
print("=" * 60)

client = None
for username, password in USERS:
    client = try_connect(HOST, username, password)
    if client:
        break

if not client:
    print("\n[FAIL] 无法连接到服务器，请检查：")
    print("   1. IP地址是否正确")
    print("   2. SSH服务是否启动（默认端口22）")
    print("   3. 用户名和密码是否正确")
    print("   4. 防火墙是否允许SSH连接")
    sys.exit(1)

# 检测系统信息
run_cmd(client, "whoami", "当前用户")
run_cmd(client, "cat /etc/os-release | head -5", "操作系统信息")
run_cmd(client, "uname -a", "内核信息")

# 检查Docker
docker_ver, _ = run_cmd(client, "docker --version 2>&1 || echo 'NOT_INSTALLED'", "Docker状态")
docker_installed = "NOT_INSTALLED" not in docker_ver

# 检查Docker Compose
run_cmd(client, "docker compose version 2>&1 || docker-compose --version 2>&1 || echo 'NOT_INSTALLED'", "Docker Compose状态")

client.close()

print("\n" + "=" * 60)
if docker_installed:
    print("[OK] Docker已安装，可直接部署容器")
else:
    print("[TODO] Docker未安装，需要先安装Docker")
print("=" * 60)
