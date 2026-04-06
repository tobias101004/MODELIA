"""
chatbot_app.py
Flask Blueprint for the Cárdenas Real Estate chatbot.
Can run standalone or be mounted into the main MODELIA app.
"""

import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Blueprint, Flask, Response, jsonify, render_template, request

from . import agent, database, property_sync

# Load .env from MODELIA root
_modelia_dir = Path(__file__).resolve().parent.parent
_env_file = _modelia_dir / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("chatbot")

chatbot_bp = Blueprint(
    "chatbot",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/chatbot",
)


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return key


# ── Pages ─────────────────────────────────────────────────────────────────────

@chatbot_bp.route("/")
def chat_page():
    return render_template("chat.html")


# ── Chat API ──────────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle a chat message. Supports streaming via SSE."""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    chat_id = data.get("chat_id", str(uuid.uuid4()))
    user_message = data["message"]
    history = data.get("history", [])

    api_key = _get_api_key()

    # Build messages from history + new message
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # Log user message
    database.log_message(chat_id, "user", user_message)

    # Stream response
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
                    # Log assistant response
                    if full_response:
                        database.log_message(chat_id, "assistant", full_response)
                    yield f"data: {json.dumps({'type': 'done', 'chat_id': chat_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            log.error(f"Chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Sync API ──────────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/sync", methods=["POST"])
def api_sync():
    """Sync properties from the Apinmo XML feed."""
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
    """Get last sync metadata."""
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
    """List all captured leads."""
    leads = database.get_all_leads()
    return jsonify({"leads": leads, "total": len(leads)})


# ── Standalone runner ─────────────────────────────────────────────────────────

def create_standalone_app() -> Flask:
    """Create a standalone Flask app for the chatbot."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    app.register_blueprint(chatbot_bp)

    # Redirect root to chatbot
    @app.route("/")
    def root():
        from flask import redirect
        return redirect("/chatbot/")

    return app


if __name__ == "__main__":
    app = create_standalone_app()
    print("\n  Cárdenas Real Estate Chatbot")
    print("  http://localhost:5001/chatbot/\n")
    app.run(debug=True, port=5001)
