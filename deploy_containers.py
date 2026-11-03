# -*- coding: utf-8 -*-
"""在远程Linux服务器上部署MySQL、Redis容器"""
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = "192.168.150.104"
PASS = "123456"

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="xiaodu", password=PASS, timeout=15, look_for_keys=False, allow_agent=False)
    return client

def run(client, cmd, desc="", timeout=300):
    if desc:
        print(f"\n>>> {desc}")
    print(f"    $ {cmd[:150]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[-30:]:
            print(f"    {line}")
    if err:
        el = err.lower()
        if 'warning' not in el and 'warn' not in el:
            print(f"    [err] {err[:300]}")
    return out, err

def put_file(client, local_content, remote_path):
    sftp = client.open_sftp()
    sftp.putfo(io.BytesIO(local_content.encode('utf-8')), remote_path)
    sftp.close()
    print(f"    [OK] -> {remote_path}")

# ======== 主流程 ========
print("=" * 60)
print("远程部署 MySQL + Redis 容器")
print(f"目标: {HOST}")
print("=" * 60)

user = connect()
print(f"[OK] SSH连接成功")

# 1. 创建目录
run(user, "mkdir -p ~/deepseek-app/mysql_data ~/deepseek-app/redis_data", "创建目录")

# 2. 上传文件
docker_compose = """services:
  mysql:
    image: mysql:8.0
    container_name: deepseek-mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: deepseek123
      MYSQL_DATABASE: deepseek
      MYSQL_USER: deepseek
      MYSQL_PASSWORD: deepseek123
    ports:
      - "3306:3306"
    volumes:
      - ./mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis:
    image: redis:7-alpine
    container_name: deepseek-redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - ./redis_data:/data
    command: redis-server --appendonly yes --requirepass deepseek-redis-2024
"""

put_file(user, docker_compose, '/home/xiaodu/deepseek-app/docker-compose.yml')

init_sql = """CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) DEFAULT 'New Conversation',
    status ENUM('active', 'archived', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant', 'system', 'tool') NOT NULL,
    content TEXT,
    tool_calls JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20),
    chunk_count INT DEFAULT 0,
    status ENUM('processing', 'ready', 'error') DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_filename (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

put_file(user, init_sql, '/home/xiaodu/deepseek-app/init.sql')

# 3. 停止旧容器
run(user, "cd ~/deepseek-app && docker compose down 2>&1 || true", "清理旧容器")

# 4. 拉取镜像（分别拉取，避免并发超时）
print("\n>>> 拉取MySQL镜像（约500MB，需几分钟）...")
out, err = run(user, "docker pull mysql:8.0 2>&1", "MySQL", timeout=600)
if 'Downloaded' in out or 'Image is up to date' in out or 'Pull complete' in out:
    print("    [OK] MySQL镜像就绪")

print("\n>>> 拉取Redis镜像（约30MB）...")
out, err = run(user, "docker pull redis:7-alpine 2>&1", "Redis", timeout=300)

# 5. 检查镜像
run(user, "docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -E 'mysql|redis'", "已下载镜像")

# 6. 启动容器
print("\n>>> 启动容器...")
run(user, "cd ~/deepseek-app && docker compose up -d 2>&1", "docker compose up -d", timeout=120)

# 7. 等待就绪
print("\n>>> 等待容器启动（MySQL初始化需要约30秒）...")
for i in range(15):
    time.sleep(10)
    out, _ = run(user, "docker ps --format '{{.Names}} {{.Status}}' 2>&1", f"检查({(i+1)*10}s)")
    if 'deepseek-mysql' in out and ('healthy' in out or 'Up' in out):
        if 'deepseek-redis' in out and ('healthy' in out or 'Up' in out):
            print("\n    [OK] 所有容器已启动!")
            break

# 8. 最终验证
print("\n" + "=" * 60)
print("最终验证")
print("=" * 60)

run(user, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态")

# 测试MySQL
print("\n>>> 测试MySQL连接...")
m, _ = run(user, "docker exec deepseek-mysql mysql -u deepseek -pdeepseek123 -e 'SELECT 1 AS test;' deepseek 2>&1", "MySQL查询测试")

# 测试Redis
print("\n>>> 测试Redis连接...")
r, _ = run(user, "docker exec deepseek-redis redis-cli -a deepseek-redis-2024 ping 2>&1", "Redis PING测试")

# 检查端口
run(user, "netstat -tlnp 2>/dev/null | grep -E '3306|6379' || echo '端口检查完成'", "端口监听")

# 9. 输出配置信息
user.close()

mysql_ok = '1' in m or 'test' in m.lower()
redis_ok = 'PONG' in r

print("\n" + "=" * 60)
print("部署结果")
print("=" * 60)
print(f"  MySQL: {'[OK] 运行正常' if mysql_ok else '[CHECK] 请稍后再试'}")
print(f"  Redis: {'[OK] 运行正常' if redis_ok else '[CHECK] 请稍后再试'}")
print()
print("===== 在你的Windows项目 .env 文件中这样配置 =====")
print(f"MYSQL_HOST={HOST}")
print(f"MYSQL_PORT=3306")
print(f"MYSQL_USER=deepseek")
print(f"MYSQL_PASSWORD=deepseek123")
print(f"MYSQL_DATABASE=deepseek")
print(f"REDIS_HOST={HOST}")
print(f"REDIS_PORT=6379")
print(f"REDIS_PASSWORD=deepseek-redis-2024")
print(f"REDIS_DB=0")
print("===============================================")
