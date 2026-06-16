"""文件系统工具 - 智能体工作区文件操作"""
from pathlib import Path

from src.tools.tool_registry import tool_registry

WORKSPACE = Path(__file__).parent.parent.parent / "workspace"


def _ensure_workspace():
    """确保工作区目录存在"""
    WORKSPACE.mkdir(exist_ok=True)


@tool_registry.register
def read_file(filepath: str) -> str:
    """从工作区读取文件内容。参数 filepath 为相对路径。"""
    _ensure_workspace()
    path = (WORKSPACE / filepath).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "错误：不允许路径遍历攻击。"
    if not path.exists():
        return f"文件未找到：{filepath}"
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > 5000:
            content = content[:5000] + "\n...（已截断）"
        return content
    except Exception as e:
        return f"读取错误：{e}"


@tool_registry.register
def write_file(filepath: str, content: str) -> str:
    """将内容写入工作区文件。参数 filepath 为相对路径，content 为要写入的内容。"""
    _ensure_workspace()
    path = (WORKSPACE / filepath).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "错误：不允许路径遍历攻击。"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"文件已写入：{filepath}（{len(content)} 字符）"
    except Exception as e:
        return f"写入错误：{e}"


@tool_registry.register
def list_files(directory: str = ".") -> str:
    """列出工作区中的文件和目录。参数 directory 为相对路径，默认为当前目录。"""
    _ensure_workspace()
    path = (WORKSPACE / directory).resolve()
    if not str(path).startswith(str(WORKSPACE.resolve())):
        return "错误：不允许路径遍历攻击。"
    if not path.exists():
        return f"目录未找到：{directory}"
    items = []
    for item in sorted(path.iterdir()):
        t = "目录" if item.is_dir() else "文件"
        if item.is_file():
            size = item.stat().st_size
            items.append(f"  [{t}] {item.name}（{size:,} 字节）")
        else:
            items.append(f"  [{t}] {item.name}/")
    if not items:
        return f"目录 '{directory}' 为空。"
    return f"'{directory}' 的内容：\n" + "\n".join(items)
