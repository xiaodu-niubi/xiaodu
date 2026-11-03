"""Isolated code execution using an explicitly enabled Docker worker."""
import subprocess
import uuid
from src.config import settings


def run_python(code: str) -> str:
    if not settings.enable_code_execution:
        return "代码执行未启用。请由部署者配置 Docker 隔离环境并设置 ENABLE_CODE_EXECUTION=true。"
    if len(code) > 20000:
        return "代码不能超过 20000 字符。"
    name = "deepseek-code-" + uuid.uuid4().hex
    command = [
        "docker", "run", "--rm", "--pull=never", "--name", name,
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--memory=128m", "--cpus=0.5",
        "--pids-limit=64", "--user=65534:65534",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "-i",
        settings.code_container_image, "python", "-I", "-",
    ]
    try:
        result = subprocess.run(command, input=code, text=True, capture_output=True, timeout=20)
        output = (result.stdout + result.stderr).strip()[:12000]
        return output or ("执行完成（无输出）。" if result.returncode == 0 else "执行失败。")
    except subprocess.TimeoutExpired:
        return "代码执行超过 20 秒，已终止。"
    except FileNotFoundError:
        return "Docker 未安装，代码执行不可用。"
    finally:
        try:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
