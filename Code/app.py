"""
app.py
Servidor Flask local que orquesta el pipeline:
  PDF → pdf_extractor → llm_extractor → normalizer → generar_modelo211 → descarga

Rutas:
  GET  /          → landing publica (landing.html)
  GET  /app       → interfaz web autenticada (generic.html)
  POST /process   → ejecuta el pipeline completo, devuelve JSON con preview
  GET  /download  → descarga Output/211.txt
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

# ── Rutas del proyecto ────────────────────────────────────────────────────────

MODELIA_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MODELIA_DIR / "Code"))

env_file = MODELIA_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file, override=False)

from llm_extractor import extraer_campos_llm          # noqa: E402
from modelo211_generator import generar_modelo211     # noqa: E402
from normalizer import normalizar_datos               # noqa: E402
from pdf_extractor import extraer_texto_pdf           # noqa: E402

# ── App Flask ─────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder=str(MODELIA_DIR / "templates"))

# Startup debug — shows in Railway deploy logs
import logging
logging.basicConfig(level=logging.INFO)
_key = os.environ.get("OPENAI_API_KEY", "")
logging.info(f"[MODELIA] OPENAI_API_KEY present: {bool(_key.strip())}, length: {len(_key)}")
logging.info(f"[MODELIA] ENV keys with KEY/OPENAI: {[k for k in os.environ if 'KEY' in k or 'OPENAI' in k]}")


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/app")
def index():
    return render_template("generic.html")


@app.route("/debug-env")
def debug_env():
    key = os.environ.get("OPENAI_API_KEY", "")
    return jsonify({
        "key_exists": bool(key.strip()),
        "key_length": len(key),
        "key_prefix": key[:10] + "..." if key else "(empty)",
        "all_env_keys": [k for k in os.environ.keys() if "KEY" in k or "OPENAI" in k or "RAILWAY" in k],
    })


@app.route("/process", methods=["POST"])
def process():
    # Validar que se recibe un PDF
    if "pdf" not in request.files:
        return jsonify({"error": "No se recibió ningún archivo PDF."}), 400

    pdf_file = request.files["pdf"]
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "El archivo debe tener extensión .pdf"}), 400

    # API key del servidor
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        try:
            import base64
            cfg_path = MODELIA_DIR / "config" / "key.txt"
            api_key = base64.b64decode(cfg_path.read_text().strip()).decode()
        except Exception:
            return jsonify({"error": "API Key no configurada en el servidor."}), 500

    # Guardar PDF en fichero temporal
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        pdf_file.save(tmp.name)
        tmp.close()
        pdf_path = Path(tmp.name)

        # Paso 1: Extraer texto del PDF
        texto = extraer_texto_pdf(pdf_path)
        if len(texto.strip()) < 100:
            return jsonify({
                "error": (
                    "El PDF tiene muy poco texto extraíble. "
                    "Puede ser un documento escaneado (imagen). "
                    f"Texto obtenido: '{texto[:300]}'"
                )
            }), 422

        # Paso 2: LLM → dict raw
        raw_data = extraer_campos_llm(texto, api_key)

        # Paso 3: Normalizar
        datos_limpios = normalizar_datos(raw_data)

        # Paso 4: Guardar JSON de entrada con timestamp (trazabilidad)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_dir = MODELIA_DIR / "Input"
        input_dir.mkdir(exist_ok=True)
        json_path = input_dir / f"datos_211_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(datos_limpios, f, ensure_ascii=False, indent=2)

        # Paso 5: Generar 211.txt
        output_dir = MODELIA_DIR / "Output"
        output_dir.mkdir(exist_ok=True)
        generar_modelo211(json_path, output_dir)

        return jsonify({
            "ok": True,
            "json_preview": datos_limpios,
            "json_guardado": json_path.name,
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/download")
def download():
    txt_path = MODELIA_DIR / "Output" / "211.txt"
    if not txt_path.exists():
        return jsonify({"error": "El fichero 211.txt no se ha generado todavía."}), 404
    return send_file(
        txt_path,
        as_attachment=True,
        download_name="211.txt",
        mimetype="text/plain",
    )


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  MODELIA dir : {MODELIA_DIR}")
    print(f"  Templates   : {MODELIA_DIR / 'templates'}")
    print(f"  .env        : {MODELIA_DIR / '.env'}")
    print(f"\n  Servidor en : http://localhost:5000\n")
    app.run(debug=False, port=5000)
