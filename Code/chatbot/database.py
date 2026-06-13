"""
database.py
Supabase storage for leads and chat logs.
"""

import os
import uuid
from datetime import datetime

from supabase import create_client

# Las credenciales se leen de env vars (Railway). Si por accidente no
# estuvieran definidas, caemos al valor publico actual para no romper el
# arranque, pero hay que dejarlas configuradas en Railway.
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://pntipdspiivffvxfyshg.supabase.co",
).strip()
SUPABASE_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBudGlwZHNwaWl2ZmZ2eGZ5c2hnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3OTg5NzYsImV4cCI6MjA4NzM3NDk3Nn0.2n0YukribUPyIcaWcercFEzpStq-VhQTzFpE69Pnv2M",
).strip()


class _LazyClient:
    """Defers create_client until first use so a bad supabase install can
    never crash the whole app at import time."""
    _real = None

    def __getattr__(self, name):
        if _LazyClient._real is None:
            _LazyClient._real = create_client(SUPABASE_URL, SUPABASE_KEY)
        return getattr(_LazyClient._real, name)


_client = _LazyClient()


def save_lead(
    chat_id: str,
    name: str = "",
    email: str = "",
    phone: str = "",
    intent: str = "",
    operation: str = "",
    property_type: str = "",
    location: str = "",
    bedrooms: int = 0,
    budget: float = 0,
    matched_refs: str = "",
    summary: str = "",
) -> str:
    """Save a lead and return its ID."""
    lead_id = str(uuid.uuid4())
    _client.table("leads").insert({
        "id": lead_id,
        "chat_id": chat_id,
        "created_at": datetime.now().isoformat(),
        "name": name,
        "email": email,
        "phone": phone,
        "intent": intent,
        "operation": operation,
        "property_type": property_type,
        "location": location,
        "bedrooms": bedrooms,
        "budget": budget,
        "matched_refs": matched_refs,
        "summary": summary,
    }).execute()
    return lead_id


def log_message(chat_id: str, role: str, content: str):
    """Append a message to the chat log."""
    _client.table("chat_logs").insert({
        "chat_id": chat_id,
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
    }).execute()


def get_chat_history(chat_id: str) -> list[dict]:
    """Get all messages for a chat session."""
    result = (
        _client.table("chat_logs")
        .select("role, content")
        .eq("chat_id", chat_id)
        .order("id")
        .execute()
    )
    return result.data


def get_all_leads() -> list[dict]:
    """Get all leads, most recent first."""
    result = (
        _client.table("leads")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
