"""天气查询工具 - 使用 wttr.in 免费天气 API"""
from src.tools.tool_registry import tool_registry


def _format_weather(city: str, data: dict) -> str:
    """将 wttr.in JSON 数据格式化为可读的天气报告"""
    current = data.get("current_condition", [{}])[0]
    weather_info = data.get("weather", [])

    lines = [f"## {city} 天气\n"]

    lines.append("### 当前实况")
    lines.append(f"- 温度：{current.get('temp_C', 'N/A')}°C（体感 {current.get('FeelsLikeC', 'N/A')}°C）")
    lines.append(f"- 天气：{current.get('weatherDesc', [{}])[0].get('value', 'N/A')}")
    lines.append(f"- 风向风速：{current.get('winddir16Point', 'N/A')} {current.get('windspeedKmph', 'N/A')} km/h")
    lines.append(f"- 湿度：{current.get('humidity', 'N/A')}%")
    lines.append(f"- 能见度：{current.get('visibility', 'N/A')} km")
    lines.append(f"- 气压：{current.get('pressure', 'N/A')} hPa")
    lines.append(f"- 紫外线指数：{current.get('uvIndex', 'N/A')}")

    if weather_info:
        lines.append("\n### 未来天气预报")
        for day in weather_info[:3]:
            date = day.get("date", "N/A")
            max_temp = day.get("maxtempC", "N/A")
            min_temp = day.get("mintempC", "N/A")
            hourly = day.get("hourly", [])
            day_desc = hourly[4].get("weatherDesc", [{}])[0].get("value", "N/A") if len(hourly) > 4 else "N/A"
            lines.append(f"- {date}：{min_temp}°C ~ {max_temp}°C，{day_desc}")

    return "\n".join(lines)


@tool_registry.register
def get_weather(city: str) -> str:
    """查询指定城市的实时天气信息。返回温度、体感温度、湿度、风速、天气状况等。支持中文城市名，如'北京'、'重庆'、'上海'、'Tokyo'、'London'。"""
    import json
    import httpx
    from urllib.parse import quote

    encoded_city = quote(city)

    # 尝试 httpx（HTTPS → HTTP 依次回退）
    last_error = None
    for scheme in ("https", "http"):
        try:
            url = f"{scheme}://wttr.in/{encoded_city}?format=j1"
            resp = httpx.get(url, headers={"User-Agent": "DeepSeekAgent/1.0"}, timeout=15.0)
            resp.raise_for_status()
            return _format_weather(city, resp.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"未找到城市「{city}」的天气信息，请检查城市名称是否正确（支持中文名和英文名）。"
            last_error = f"HTTP {e.response.status_code}"
        except Exception as e:
            last_error = str(e)

    # 兜底：subprocess 调用系统 curl（解决某些环境下 Python HTTP 的 SSL/代理问题）
    try:
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "--max-time", "15",
             f"http://wttr.in/{encoded_city}?format=j1"],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0 and result.stdout.strip():
            return _format_weather(city, json.loads(result.stdout))
    except Exception:
        pass

    return f"天气查询出错：{last_error}"
