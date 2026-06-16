"""内置工具：计算器、时间日期、单位转换、代码执行、令牌计数"""
import math
import datetime
from typing import Optional

from src.tools.tool_registry import tool_registry


@tool_registry.register
def calculator(expression: str) -> str:
    """安全地计算数学表达式。支持 +, -, *, /, **, %, sqrt, sin, cos, tan, log, abs, pow, pi, e。"""
    allowed_names = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "abs": abs, "pow": pow, "pi": math.pi, "e": math.e,
        "ceil": math.ceil, "floor": math.floor, "round": round,
    }
    try:
        code = compile(expression, "<calculator>", "eval")
        for name in code.co_names:
            if name not in allowed_names:
                raise NameError(f"不允许使用 '{name}'")
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算错误：{e}"


@tool_registry.register
def get_current_time(timezone: Optional[str] = None) -> str:
    """获取当前日期和时间。可选参数 timezone 指定时区，如 'Asia/Shanghai'、'UTC'。"""
    try:
        if timezone:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone)
            now = datetime.datetime.now(tz)
        else:
            now = datetime.datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return now.strftime(f"%Y年%m月%d日 %H:%M:%S %Z（{weekdays[now.weekday()]}，第W%W周）")
    except Exception as e:
        return f"时间获取错误：{e}。本地时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool_registry.register
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """在常用单位之间转换。支持长度（m, km, cm, mm, mi, ft, in, yd）、重量（kg, g, lb, oz）、温度（C, F, K）。"""
    # 长度 → 米
    length_to_m = {
        "m": 1, "km": 1000, "cm": 0.01, "mm": 0.001,
        "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144,
    }
    # 重量 → 千克
    weight_to_kg = {"kg": 1, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}

    from_u = from_unit.lower()
    to_u = to_unit.lower()

    # 温度转换
    if from_u in ("c", "f", "k") and to_u in ("c", "f", "k"):
        if from_u == "c":
            celsius = value
        elif from_u == "f":
            celsius = (value - 32) * 5 / 9
        elif from_u == "k":
            celsius = value - 273.15
        if to_u == "c":
            result = celsius
        elif to_u == "f":
            result = celsius * 9 / 5 + 32
        elif to_u == "k":
            result = celsius + 273.15
        return f"{value} {from_u} = {result:.4f} {to_u}"

    # 长度转换
    if from_u in length_to_m and to_u in length_to_m:
        meters = value * length_to_m[from_u]
        result = meters / length_to_m[to_u]
        return f"{value} {from_u} = {result:.6f} {to_u}"

    # 重量转换
    if from_u in weight_to_kg and to_u in weight_to_kg:
        kg = value * weight_to_kg[from_u]
        result = kg / weight_to_kg[to_u]
        return f"{value} {from_u} = {result:.6f} {to_u}"

    return f"无法将 {from_unit} 转换为 {to_unit}。支持的类型：长度、重量、温度。"


@tool_registry.register
def python_repl(code: str) -> str:
    """在沙盒环境中执行 Python 代码。用于计算、数据处理、字符串操作。返回标准输出。"""
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(code, {"__builtins__": {
            "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
            "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
            "filter": filter, "float": float, "format": format, "frozenset": frozenset,
            "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
            "len": len, "list": list, "map": map, "max": max, "min": min,
            "oct": oct, "ord": ord, "pow": pow, "print": print, "range": range,
            "reversed": reversed, "round": round, "set": set, "slice": slice,
            "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
            "zip": zip, "complex": complex, "bytes": bytes, "bytearray": bytearray,
        }})
        output = sys.stdout.getvalue()
        return output if output.strip() else "（无输出）"
    except Exception as e:
        return f"执行错误：{e}"
    finally:
        sys.stdout = old_stdout


@tool_registry.register
def count_tokens(text: str) -> str:
    """估算文本的令牌（token）数量（4个字符 ≈ 1个令牌）。"""
    chars = len(text)
    words = len(text.split())
    approx_tokens = chars // 4
    return f"文本长度：{chars}字符，{words}词，约{approx_tokens}个令牌"
