"""网络搜索工具 - 使用 DuckDuckGo 搜索引擎"""
from src.tools.tool_registry import tool_registry


@tool_registry.register
def web_search(query: str) -> str:
    """在网上搜索最新信息。返回搜索结果的标题、URL 和摘要。"""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"- {r['title']}\n  链接: {r['href']}\n  摘要: {r['body']}")
        if not results:
            return "未找到搜索结果。"
        return "\n\n".join(results)
    except ImportError:
        return "网络搜索不可用：duckduckgo-search 未安装。"
    except Exception as e:
        return f"搜索出错：{e}"


@tool_registry.register
def web_fetch(url: str) -> str:
    """获取并提取网页的文本内容。用于从搜索结果中阅读完整的文章/页面。"""
    try:
        import httpx
        from bs4 import BeautifulSoup

        resp = httpx.get(url, timeout=10, follow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; DeepSeekAgent/1.0)"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:4000] + ("..." if len(text) > 4000 else "")
    except Exception as e:
        return f"获取网页出错：{e}"
