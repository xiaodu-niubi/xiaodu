# 第5课：数据库层 —— MySQL 客户端

> 🎯 **本课目标**：写一个操作MySQL的工具类，实现对对话和消息的增删改查。

---

## 5.1 为什么需要数据库？

用户聊天的记录需要**持久化存储**（存到硬盘上），否则服务器重启后全部丢失。

我们需要存两种数据：
1. **对话列表**（有哪些对话）
2. **消息记录**（每个对话里说了什么）

用MySQL来存储，因为它可靠、功能强、生态好。

---

## 5.2 回顾一下表结构

在第2课启动Docker时，`init.sql` 已经自动执行，建好了3张表：

```sql
-- 对话表
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,        -- 对话ID（UUID）
    session_id VARCHAR(64) NOT NULL,   -- 会话ID（关联Redis）
    title VARCHAR(255),                -- 对话标题
    status ENUM('active','archived','deleted'),  -- 状态
    created_at TIMESTAMP,              -- 创建时间
    updated_at TIMESTAMP               -- 更新时间
);

-- 消息表
CREATE TABLE messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,  -- 消息ID（自增）
    conversation_id VARCHAR(36),           -- 属于哪个对话
    role ENUM('user','assistant','system','tool'),  -- 谁说的
    content TEXT,                          -- 消息内容
    tool_calls JSON,                       -- 工具调用记录
    metadata JSON,                         -- 额外信息
    created_at TIMESTAMP                   -- 时间
);

-- 知识文档表
CREATE TABLE knowledge_documents (
    id VARCHAR(36) PRIMARY KEY,        -- 文档ID
    filename VARCHAR(255),             -- 文件名
    file_type VARCHAR(20),             -- 文件类型
    chunk_count INT,                   -- 分了多少块
    status ENUM('processing','ready','error'),  -- 状态
    created_at TIMESTAMP               -- 时间
);
```

---

## 5.3 写代码：`src/database/mysql_client.py`

```python
"""MySQL 客户端 - 对话和消息持久化存储"""
import uuid
import json
from typing import Optional
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from src.config import settings


class MySQLClient:
    """MySQL 数据库操作封装
    
    这个类把所有数据库操作都封装好了，其他地方只需要：
        from src.database.mysql_client import mysql_client
        mysql_client.xxx()  # 调用对应方法
    
    不需要关心SQL怎么写、连接怎么管理。
    """

    def __init__(self):
        self._pool = None  # 数据库连接

    @property
    def pool(self):
        """获取数据库连接（懒加载 + 自动重连）"""
        if self._pool is None:
            self._pool = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset='utf8mb4',
                cursorclass=DictCursor,  # ⭐ 关键：查询结果返回字典而非元组
                autocommit=True,         # ⭐ 自动提交，不用手动commit
            )
        return self._pool

    @contextmanager
    def get_cursor(self):
        """获取数据库游标，自动处理重连
        
        contextmanager 的作用：
        - with self.get_cursor() as cur:
              cur.execute(...)
        - 执行完自动关闭游标
        """
        conn = self.pool
        try:
            conn.ping(reconnect=True)  # 检查连接，断了就重连
        except Exception:
            self._pool = None
            conn = self.pool
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    # ═══════════════════════════════════════════
    # 对话管理
    # ═══════════════════════════════════════════

    def create_conversation(self, title: str = "新对话") -> dict:
        """创建新的对话记录
        
        返回: {"id": "uuid", "session_id": "短id", "title": "新对话"}
        """
        conv_id = str(uuid.uuid4())          # 生成唯一ID，如 "a1b2c3d4-..."
        session_id = str(uuid.uuid4())[:12]  # 短ID用于Redis，取前12位
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (id, session_id, title) VALUES (%s, %s, %s)",
                (conv_id, session_id, title),
            )
        return {"id": conv_id, "session_id": session_id, "title": title}

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        """获取单个对话详情"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM conversations WHERE id = %s", (conv_id,))
            return cur.fetchone()  # 返回一行，没有则返回None

    def list_conversations(self, limit: int = 50, offset: int = 0) -> list:
        """获取对话列表（按更新时间倒序）"""
        with self.get_cursor() as cur:
            cur.execute(
                """SELECT * FROM conversations 
                   WHERE status != 'deleted' 
                   ORDER BY updated_at DESC 
                   LIMIT %s OFFSET %s""",
                (limit, offset),
            )
            return cur.fetchall()  # 返回所有行

    def update_conversation_title(self, conv_id: str, title: str):
        """更新对话标题"""
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE conversations SET title = %s WHERE id = %s",
                (title, conv_id),
            )

    def delete_conversation(self, conv_id: str):
        """软删除对话（不真删，只改状态）"""
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE conversations SET status = 'deleted' WHERE id = %s",
                (conv_id,),
            )

    # ═══════════════════════════════════════════
    # 消息管理
    # ═══════════════════════════════════════════

    def save_message(
        self,
        conversation_id: str,
        role: str,       # 'user' / 'assistant' / 'system' / 'tool'
        content: str,
        tool_calls: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """保存一条消息，返回消息ID"""
        with self.get_cursor() as cur:
            cur.execute(
                """INSERT INTO messages 
                   (conversation_id, role, content, tool_calls, metadata) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    conversation_id,
                    role,
                    content,
                    json.dumps(tool_calls) if tool_calls else None,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            return cur.lastrowid

    def get_messages(self, conversation_id: str, limit: int = 50) -> list:
        """获取对话的所有消息（按时间正序）"""
        with self.get_cursor() as cur:
            cur.execute(
                """SELECT * FROM messages 
                   WHERE conversation_id = %s 
                   ORDER BY created_at ASC 
                   LIMIT %s""",
                (conversation_id, limit),
            )
            return cur.fetchall()

    # ═══════════════════════════════════════════
    # 知识库文档管理
    # ═══════════════════════════════════════════

    def register_document(self, filename: str, file_type: str) -> str:
        """注册新文档，返回文档ID"""
        doc_id = str(uuid.uuid4())
        with self.get_cursor() as cur:
            cur.execute(
                """INSERT INTO knowledge_documents 
                   (id, filename, file_type, chunk_count) 
                   VALUES (%s, %s, %s, 0)""",
                (doc_id, filename, file_type),
            )
        return doc_id

    def update_document_status(self, doc_id: str, status: str, chunk_count: int = 0):
        """更新文档处理状态"""
        with self.get_cursor() as cur:
            cur.execute(
                """UPDATE knowledge_documents 
                   SET status = %s, chunk_count = %s 
                   WHERE id = %s""",
                (status, chunk_count, doc_id),
            )

    def list_documents(self) -> list:
        """列出所有知识库文档"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM knowledge_documents ORDER BY created_at DESC")
            return cur.fetchall()


# 创建全局唯一实例（单例模式）
# 其他文件通过 from src.database.mysql_client import mysql_client 来使用
mysql_client = MySQLClient()
```

---

## 5.4 关键概念解释

### `contextmanager` 是什么？

Python的上下文管理器让我们可以用 `with` 语句自动管理资源：

```python
# 不用上下文管理器（容易忘记关闭）
cur = conn.cursor()
cur.execute(...)
cur.close()  # ← 容易忘

# 用上下文管理器（自动关闭）
with self.get_cursor() as cur:
    cur.execute(...)
# 离开with块时自动关闭，即使出错了也会关闭
```

### `DictCursor` 是什么？

```python
# 默认游标：查询结果是无组
cur.execute("SELECT id, title FROM conversations")
result = cur.fetchone()
print(result)  # ('abc123', '新对话')   ← 怎么拿到title？result[1] 不好理解

# DictCursor：查询结果是字典
cur.execute("SELECT id, title FROM conversations")
result = cur.fetchone()
print(result)  # {'id': 'abc123', 'title': '新对话'}  ← print(result['title']) 清晰！
```

### `uuid.uuid4()` 是什么？

生成一个**全球唯一的随机ID**，比如 `a1b2c3d4-e5f6-7890-abcd-ef1234567890`。

用它当主键的好处：多个系统产生的ID不会冲突。用自增数字当主键的话，分库分表时容易冲突。

---

## 5.5 测试MySQL连接

创建 `test_mysql.py`（项目根目录）：

```python
"""测试MySQL连接和基本操作"""
from src.database.mysql_client import mysql_client

# 1. 创建对话
conv = mysql_client.create_conversation(title="测试对话")
print(f"✅ 创建对话: {conv}")

# 2. 保存一条用户消息
msg_id = mysql_client.save_message(conv["id"], "user", "你好，这是一条测试消息")
print(f"✅ 保存消息，ID={msg_id}")

# 3. 保存一条助手消息
mysql_client.save_message(conv["id"], "assistant", "你好！我收到了你的测试消息")

# 4. 查询消息
messages = mysql_client.get_messages(conv["id"])
print(f"✅ 对话中有 {len(messages)} 条消息:")
for m in messages:
    print(f"   [{m['role']}] {m['content'][:50]}")

# 5. 查询对话列表
convs = mysql_client.list_conversations()
print(f"✅ 共有 {len(convs)} 个对话")

# 6. 查询单个对话
detail = mysql_client.get_conversation(conv["id"])
print(f"✅ 查询对话: {detail['title']}")

# 7. 更新标题
mysql_client.update_conversation_title(conv["id"], "更新后的标题")
updated = mysql_client.get_conversation(conv["id"])
print(f"✅ 更新后标题: {updated['title']}")

# 8. 软删除
mysql_client.delete_conversation(conv["id"])
convs_after = mysql_client.list_conversations()
print(f"✅ 删除后还有 {len(convs_after)} 个活跃对话")

print("\n🎉 MySQL客户端测试全部通过！")
```

运行：
```bash
python test_mysql.py
```

如果全部显示 ✅，说明MySQL客户端工作正常！

---

## 5.6 常见错误处理

| 错误 | 原因 | 解决 |
|------|------|------|
| `Can't connect to MySQL server on 'localhost'` | MySQL没启动 | `docker ps` 确认容器在运行 |
| `Access denied for user` | 密码不对 | 检查 `.env` 中 MySQL密码是否和 `docker-compose.yml` 一致 |
| `Unknown database 'deepseek'` | 数据库没创建 | `docker compose down -v && docker compose up -d` 重新初始化 |

---

> **下一课**：[第6课：数据库层 —— Redis](./06-数据库层-Redis.md) —— 写Redis客户端，管理对话记忆。

> ✅ **检验清单**：
> - [ ] `src/database/mysql_client.py` 已创建
> - [ ] `python test_mysql.py` 全部通过
> - [ ] 理解了 `DictCursor`、`contextmanager`、`uuid` 的用法
