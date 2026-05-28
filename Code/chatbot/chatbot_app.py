"""
chatbot_app.py
Flask Blueprint — API routes for the Cárdenas Real Estate chatbot.
UI is integrated into the main MODELIA dashboard (generic.html).
"""

import csv
import io
import json
import logging
import os
import uuid

from flask import Blueprint, Response, jsonify, request

from . import agent, database, property_sync

log = logging.getLogger("chatbot")

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return key


# ── Chat API ──────────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    chat_id = data.get("chat_id", str(uuid.uuid4()))
    user_message = data["message"]
    history = data.get("history", [])

    api_key = _get_api_key()

    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    database.log_message(chat_id, "user", user_message)

    def generate():
        full_response = ""
        try:
            for event in agent.chat_stream(api_key, chat_id, messages):
                if event["type"] == "text":
                    full_response += event["content"]
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                elif event["type"] == "properties":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                elif event["type"] == "done":
                    if full_response:
                        database.log_message(chat_id, "assistant", full_response)
                    yield f"data: {json.dumps({'type': 'done', 'chat_id': chat_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            log.error(f"Chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Sync API ──────────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/sync", methods=["POST"])
def api_sync():
    data = request.get_json() or {}
    url = data.get("url", property_sync.DEFAULT_XML_URL)
    try:
        meta = property_sync.sync_from_url(url)
        log.info(f"[SYNC] Synced {meta['total_properties']} properties from {url}")
        return jsonify({"ok": True, **meta})
    except Exception as e:
        log.error(f"Sync error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@chatbot_bp.route("/api/sync/status")
def api_sync_status():
    meta = property_sync.load_sync_meta()
    properties = property_sync.load_properties()
    return jsonify({
        "synced": meta is not None,
        "meta": meta,
        "property_count": len(properties),
    })


# ── Leads API ─────────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/leads")
def api_leads():
    leads = database.get_all_leads()
    return jsonify({"leads": leads, "total": len(leads)})


@chatbot_bp.route("/api/leads/csv")
def api_leads_csv():
    leads = database.get_all_leads()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Fecha", "Nombre", "Email", "Telefono", "Intencion",
        "Operacion", "Tipo", "Zona", "Dormitorios", "Presupuesto",
        "Refs mostradas", "Resumen",
    ])
    for l in leads:
        writer.writerow([
            l.get("created_at", ""), l.get("name", ""), l.get("email", ""),
            l.get("phone", ""), l.get("intent", ""), l.get("operation", ""),
            l.get("property_type", ""), l.get("location", ""),
            l.get("bedrooms", ""), l.get("budget", ""),
            l.get("matched_refs", ""), l.get("summary", ""),
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_cardenas.csv"},
    )
