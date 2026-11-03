# 第6课：数据库层 —— Redis 客户端

> 🎯 **本课目标**：写Redis操作工具类，管理对话记忆、用户偏好、智能体状态。

---

## 6.1 MySQL vs Redis，为什么要两个数据库？

| 对比 | MySQL | Redis |
|------|-------|-------|
| **存储位置** | 硬盘 | 内存 |
| **速度** | 毫秒级 | 微秒级（快1000倍） |
| **数据持久化** | ✅ 永久保存 | ⚠️ 重启可能丢失（有AOF保护） |
| **适合存什么** | 重要数据（对话记录） | 临时数据（当前会话上下文） |
| **类比** | 你的文档柜 | 你桌上的便签纸 |

在我们的项目中：
- **MySQL**：存所有对话记录（历史归档）
- **Redis**：存当前会话的上下文（临时记忆，24小时后过期）

这样设计的好处：每次对话不需要从MySQL加载全部历史，从Redis快速取最近的上下文。

---

## 6.2 Redis数据结构速览

Redis有几种数据结构，我们项目中用到：

| 数据结构 | 比喻 | 我们用来存什么 |
|---------|------|-------------|
| **String** | 一个变量 | 对话摘要 |
| **List** | 一个队列 | 对话消息列表 |
| **Hash** | 一个字典 | 用户偏好设置 |
| **Key过期** | 定时删除 | 24小时后自动清除记忆 |

---

## 6.3 写代码：`src/database/redis_client.py`

```python
"""Redis 客户端 - 对话记忆和智能体状态管理"""
import json
from typing import Optional

import redis

from src.config import settings


class RedisClient:
    """Redis 操作封装 - 管理会话记忆和智能体状态
    
    数据在Redis中以Key-Value形式存储：
    每个session有自己的前缀 memory:{session_id}:xxx
    """

    def __init__(self):
        self._client = None

    @property
    def client(self) -> redis.Redis:
        """获取Redis连接（懒加载 + 自动重连）"""
        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,  # ⭐ 自动把bytes解码为字符串
            )
        try:
            self._client.ping()  # 测试连接
        except (redis.ConnectionError, redis.TimeoutError):
            # 连接断了，重新连接
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,
            )
        return self._client

    # ═══════════════════════════════════════════
    # 对话记忆（核心功能）
    # ═══════════════════════════════════════════

    def save_message(self, session_id: str, role: str, content: str):
        """保存一条消息到对话历史
        
        用Redis的List结构，每次在列表末尾追加一条消息
        Key: memory:{session_id}:messages
        Value: [{"role":"user","content":"你好"}, {"role":"assistant","content":"你好！"}, ...]
        """
        key = f"memory:{session_id}:messages"
        msg = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        self.client.rpush(key, msg)  # rpush = 从列表右边推入（追加到末尾）
        self.client.expire(key, settings.memory_ttl_seconds)  # 设置过期时间，到期自动删除

    def get_messages(self, session_id: str, limit: int = 20) -> list:
        """获取最近的对话消息
        
        lrange(key, -limit, -1) = 取列表最后 limit 个元素
        """
        key = f"memory:{session_id}:messages"
        raw = self.client.lrange(key, -limit, -1)  # 取最后20条
        return [json.loads(m) for m in raw]

    def clear_memory(self, session_id: str):
        """清除会话所有记忆
        
        用通配符 pattern 找到所有相关的key，一次性删除
        """
        pattern = f"memory:{session_id}:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)

    # ═══════════════════════════════════════════
    # 智能体工作区
    # ═══════════════════════════════════════════

    def save_agent_state(self, session_id: str, agent_name: str, state: dict):
        """保存智能体的工作状态（比如正在处理哪个步骤）"""
        key = f"memory:{session_id}:agent:{agent_name}"
        self.client.setex(key, settings.memory_ttl_seconds, json.dumps(state, ensure_ascii=False))

    def get_agent_state(self, session_id: str, agent_name: str) -> Optional[dict]:
        """获取智能体的工作状态"""
        key = f"memory:{session_id}:agent:{agent_name}"
        raw = self.client.get(key)
        return json.loads(raw) if raw else None

    # ═══════════════════════════════════════════
    # 会话元数据
    # ═══════════════════════════════════════════

    def save_metadata(self, session_id: str, metadata: dict):
        """保存会话元数据（如用户语言偏好、最后活动时间等）"""
        key = f"memory:{session_id}:metadata"
        self.client.setex(key, settings.memory_ttl_seconds, json.dumps(metadata, ensure_ascii=False))

    def get_metadata(self, session_id: str) -> Optional[dict]:
        """获取会话元数据"""
        key = f"memory:{session_id}:metadata"
        raw = self.client.get(key)
        return json.loads(raw) if raw else {}

    # ═══════════════════════════════════════════
    # 用户偏好
    # ═══════════════════════════════════════════

    def save_preference(self, session_id: str, key_name: str, value: str):
        """保存用户偏好（用Hash结构，方便存多个键值对）
        
        Redis Hash就像一个微型字典：
        Key: memory:{session_id}:prefs
        Field-Value:
            language: 中文
            tone: 正式
            favorite_color: 蓝色
        """
        key = f"memory:{session_id}:prefs"
        self.client.hset(key, key_name, value)
        self.client.expire(key, settings.memory_ttl_seconds)

    def get_preferences(self, session_id: str) -> dict:
        """获取所有用户偏好"""
        key = f"memory:{session_id}:prefs"
        return self.client.hgetall(key)

    # ═══════════════════════════════════════════
    # 对话摘要
    # ═══════════════════════════════════════════

    def save_summary(self, session_id: str, summary: str):
        """保存对话摘要（长对话自动压缩）"""
        key = f"memory:{session_id}:summary"
        self.client.setex(key, settings.memory_ttl_seconds, summary)

    def get_summary(self, session_id: str) -> Optional[str]:
        """获取对话摘要"""
        key = f"memory:{session_id}:summary"
        return self.client.get(key)


# 创建全局唯一实例
redis_client = RedisClient()
```

---

## 6.4 关键概念解释

### 为什么用 `memory:{session_id}:messages` 这样的Key命名？

Redis是一个扁平的Key-Value存储，用冒号分隔的命名方式：
- 看起来像目录结构，方便管理
- 可以用通配符删除：`memory:abc123:*` 删除该session全部相关数据
- 这是Redis社区的最佳实践

### `expire` 是干什么的？

```python
self.client.expire(key, 86400)  # 86400秒 = 24小时后自动删除
```

对话记忆不需要永久保存（MySQL里已有永久记录），24小时后Redis自动清除，释放内存。

### `rpush` vs `lpush`

```python
# rpush = 追加到列表末尾
rpush("list", "a") → ["a"]
rpush("list", "b") → ["a", "b"]

# lpush = 插入到列表开头
lpush("list", "a") → ["a"]
lpush("list", "b") → ["b", "a"]
```

我们用 `rpush`，保持时间顺序（最早的在前面，最新的在后面）。

---

## 6.5 测试Redis连接

创建 `test_redis.py`：

```python
"""测试Redis连接和基本操作"""
from src.database.redis_client import redis_client

session_id = "test_session_123"

# 1. 保存消息
redis_client.save_message(session_id, "user", "你好，这是一条测试")
redis_client.save_message(session_id, "assistant", "你好！收到了")
redis_client.save_message(session_id, "user", "再问一个问题")
print(f"✅ 保存了3条消息")

# 2. 读取消息
messages = redis_client.get_messages(session_id)
print(f"✅ 读取到 {len(messages)} 条消息:")
for m in messages:
    print(f"   [{m['role']}] {m['content'][:40]}")

# 3. 保存偏好
redis_client.save_preference(session_id, "language", "中文")
redis_client.save_preference(session_id, "tone", "正式")
prefs = redis_client.get_preferences(session_id)
print(f"✅ 用户偏好: {prefs}")

# 4. 保存摘要
redis_client.save_summary(session_id, "用户问了测试问题，助手回复了")
summary = redis_client.get_summary(session_id)
print(f"✅ 摘要: {summary}")

# 5. 保存智能体状态
redis_client.save_agent_state(session_id, "rag_agent", {"step": "searching", "query": "公司产品"})
state = redis_client.get_agent_state(session_id, "rag_agent")
print(f"✅ 智能体状态: {state}")

# 6. 清除记忆
redis_client.clear_memory(session_id)
after_clear = redis_client.get_messages(session_id)
print(f"✅ 清除后消息数: {len(after_clear)}")

print("\n🎉 Redis客户端测试全部通过！")
```

运行：
```bash
python test_redis.py
```

预期全部 ✅。

---

## 6.6 Redis Key 命名规范总结

```
memory:{session_id}:messages     →  对话消息列表（List）
memory:{session_id}:summary      →  对话摘要（String）
memory:{session_id}:metadata     →  会话元数据（String，JSON）
memory:{session_id}:prefs        →  用户偏好（Hash）
memory:{session_id}:agent:{name} →  智能体状态（String，JSON）
```

---

> **下一课**：[第7课：向量数据库](./07-数据库层-向量数据库.md) —— 写本地向量存储，支持语义搜索。

> ✅ **检验清单**：
> - [ ] `src/database/redis_client.py` 已创建
> - [ ] `python test_redis.py` 全部通过
> - [ ] 理解了List、Hash、expire等Redis概念
