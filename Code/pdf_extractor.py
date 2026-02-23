"""
pdf_extractor.py
Extrae texto limpio de un PDF notarial usando pdfplumber.
"""

import re
from pathlib import Path

import pdfplumber


def extraer_texto_pdf(pdf_path: Path) -> str:
    """
    Extrae todo el texto del PDF, página a página.

    Args:
        pdf_path: Ruta al fichero PDF.

    Returns:
        Texto plano concatenado de todas las páginas, listo para el LLM.
    """
    pdf_path = Path(pdf_path)
    partes = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            texto = page.extract_text(x_tolerance=3, y_tolerance=3)
            if texto and texto.strip():
                partes.append(f"--- Página {i} ---\n{texto}")

    texto_completo = "\n\n".join(partes)

    # Limpiar espacios múltiples y líneas vacías excesivas
    texto_completo = re.sub(r" {2,}", " ", texto_completo)
    texto_completo = re.sub(r"\n{3,}", "\n\n", texto_completo)

    return texto_completo.strip()
