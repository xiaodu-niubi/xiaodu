"""Editable Markdown artifacts stored with their originating messages."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.database.mysql_client import mysql_client

router = APIRouter(prefix="/api/artifacts", tags=["成果"])


class ArtifactUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(max_length=200000)


@router.get("")
async def list_artifacts():
    return {"artifacts": await asyncio.to_thread(mysql_client.list_artifacts)}


@router.put("/{conversation_id}/{message_id}")
async def save_artifact(conversation_id: str, message_id: int, body: ArtifactUpdate):
    result = await asyncio.to_thread(mysql_client.save_artifact, conversation_id, message_id,
                                    {"title": body.title.strip(), "content": body.content})
    if result is None:
        raise HTTPException(404, "成果对应的消息不存在。")
    return result
