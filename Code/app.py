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
from comprobacion_extractor import (                  # noqa: E402
    extraer_datos_escritura, extraer_datos_211, extraer_datos_600,
)
from comprobacion_comparator import comparar_documentos  # noqa: E402
from hoja_extractor import (                                   # noqa: E402
    extraer_datos_hoja, verificar_hoja,
    extraer_datos_hoja_por_pagina, emparejar_hojas,
)

# ── App Flask ─────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder=str(MODELIA_DIR / "templates"))

# Startup debug — shows in Railway deploy logs
import logging
logging.basicConfig(level=logging.INFO)
_key = os.environ.get("OPENAI_API_KEY", "")
logging.info(f"[MODELIA] OPENAI_API_KEY present: {bool(_key.strip())}, length: {len(_key)}")
logging.info(f"[MODELIA] ENV keys with KEY/OPENAI: {[k for k in os.environ if 'KEY' in k or 'OPENAI' in k]}")


@app.route("/")
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


@app.route("/comprobacion", methods=["POST"])
def comprobacion():
    # Validar que se reciben los 3 PDFs
    for key in ("escritura", "modelo211", "modelo600"):
        if key not in request.files:
            return jsonify({"error": f"Falta el archivo: {key}"}), 400
        if not request.files[key].filename.lower().endswith(".pdf"):
            return jsonify({"error": f"El archivo '{key}' debe ser PDF."}), 400

    # API key
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        try:
            import base64
            cfg_path = MODELIA_DIR / "config" / "key.txt"
            api_key = base64.b64decode(cfg_path.read_text().strip()).decode()
        except Exception:
            return jsonify({"error": "API Key no configurada en el servidor."}), 500

    tmp_paths = []
    try:
        # Guardar los 3 PDFs en temporales
        textos = {}
        for key in ("escritura", "modelo211", "modelo600"):
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            request.files[key].save(tmp.name)
            tmp.close()
            tmp_paths.append(tmp.name)

            texto = extraer_texto_pdf(Path(tmp.name))
            if len(texto.strip()) < 100:
                return jsonify({
                    "error": f"El PDF '{key}' tiene muy poco texto extraíble. "
                             f"Puede ser un documento escaneado."
                }), 422
            textos[key] = texto

        # 3 llamadas GPT-4o para extracción estructurada
        datos_escritura = extraer_datos_escritura(textos["escritura"], api_key)
        datos_211 = extraer_datos_211(textos["modelo211"], api_key)
        datos_600 = extraer_datos_600(textos["modelo600"], api_key)

        # Comparación determinista
        resultado = comparar_documentos(datos_escritura, datos_211, datos_600)

        return jsonify({
            "ok": True,
            "resultado": resultado,
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    finally:
        for p in tmp_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass


@app.route("/verify-hoja", methods=["POST"])
def verify_hoja():
    """Receive a hoja de visita PDF + expected visit data, verify they match."""
    if "pdf" not in request.files:
        return jsonify({"error": "No se recibio ningun archivo PDF."}), 400

    pdf_file = request.files["pdf"]

    # Expected visit data from form fields
    expected = {
        "comercial": request.form.get("comercial", ""),
        "ref_propiedad": request.form.get("ref_propiedad", ""),
        "num_demanda": request.form.get("num_demanda", ""),
        "fecha_visita": request.form.get("fecha_visita", ""),
        "id_seguimiento": request.form.get("id_seguimiento", ""),
        "nombre_cliente": request.form.get("nombre_cliente", ""),
        "tipo_propiedad": request.form.get("tipo_propiedad", ""),
        "direccion_propiedad": request.form.get("direccion_propiedad", ""),
        "precio_propiedad": request.form.get("precio_propiedad", ""),
    }

    # API key
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        try:
            import base64
            cfg_path = MODELIA_DIR / "config" / "key.txt"
            api_key = base64.b64decode(cfg_path.read_text().strip()).decode()
        except Exception:
            return jsonify({"error": "API Key no configurada en el servidor."}), 500

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        pdf_file.save(tmp.name)
        tmp.close()

        extracted = extraer_datos_hoja(Path(tmp.name), api_key)
        result = verificar_hoja(extracted, expected)

        return jsonify({"ok": True, **result})

    except Exception as exc:
        return jsonify({"error": str(exc), "match": False}), 500

    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/verify-hojas-batch", methods=["POST"])
def verify_hojas_batch():
    """Receive a single PDF with multiple hojas + expected checks, verify matches.

    Expects:
        - pdf: The multi-page PDF file
        - checks: JSON string with list of expected check data
    """
    if "pdf" not in request.files:
        return jsonify({"error": "No se recibio ningun archivo PDF."}), 400

    pdf_file = request.files["pdf"]
    checks_raw = request.form.get("checks", "[]")
    try:
        checks = json.loads(checks_raw)
    except json.JSONDecodeError:
        return jsonify({"error": "JSON de checks invalido."}), 400

    # API key
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        try:
            import base64
            cfg_path = MODELIA_DIR / "config" / "key.txt"
            api_key = base64.b64decode(cfg_path.read_text().strip()).decode()
        except Exception:
            return jsonify({"error": "API Key no configurada en el servidor."}), 500

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        pdf_file.save(tmp.name)
        tmp.close()

        # Extract data from each page independently
        extractions = extraer_datos_hoja_por_pagina(Path(tmp.name), api_key)

        logging.info(f"[AUDIT] Extracted {len(extractions)} pages with data from PDF")
        for i, ext in enumerate(extractions):
            logging.info(
                f"[AUDIT]   Page {ext.get('_page', '?')}: "
                f"ref={ext.get('property_ref', '')}, "
                f"agent={ext.get('agent_name', '')}, "
                f"client={ext.get('client_name', '')}, "
                f"demand={ext.get('demand_number', '')}, "
                f"date={ext.get('visit_date', '')}"
            )

        logging.info(f"[AUDIT] Matching against {len(checks)} checks")
        for c in checks:
            logging.info(
                f"[AUDIT]   Check {c.get('id', '?')}: "
                f"ref={c.get('ref_propiedad', '')}, "
                f"agent={c.get('comercial', '')}, "
                f"client={c.get('nombre_cliente', '')}, "
                f"demand={c.get('num_demanda', '')}, "
                f"date={c.get('fecha_visita', '')}"
            )

        # Match extractions to expected checks
        results = emparejar_hojas(extractions, checks)

        return jsonify({
            "ok": True,
            "results": results,
            "total_pages": len(extractions),
            "extractions_debug": [
                {
                    "page": ext.get("_page"),
                    "property_ref": ext.get("property_ref", ""),
                    "agent_name": ext.get("agent_name", ""),
                    "client_name": ext.get("client_name", ""),
                    "demand_number": ext.get("demand_number", ""),
                    "visit_date": ext.get("visit_date", ""),
                }
                for ext in extractions
            ],
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
