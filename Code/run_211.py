"""
run_211.py
Script de ejecución del generador del Modelo 211.

Uso (desde la raíz del proyecto MODELIA/):
    python3 Code/run_211.py
    python3 Code/run_211.py Input/datos_211.json
    python3 Code/run_211.py Input/datos_211.json Output/
"""

import sys
from pathlib import Path

from modelo211_generator import (
    parse_csv_page,
    generar_modelo211,
    MODELIA_DIR,
)


# ─────────────────────────────────────────────────────────────
#  VERIFICACIÓN DE CSVs (primeros 5 campos de cada página)
# ─────────────────────────────────────────────────────────────

def verificar_csvs():
    print("\n" + "=" * 60)
    print("  VERIFICACIÓN DE CSVs")
    print("=" * 60)

    for pagina in ("010", "020", "030"):
        fields = parse_csv_page(pagina)
        print(f"\n  Página {pagina}  →  {len(fields)} campos")
        print(f"  {'Nº':>3}  {'Pos':>5}  {'Lon':>4}  {'Tipo':<4}  Descripción")
        print(f"  {'─'*3}  {'─'*5}  {'─'*4}  {'─'*4}  {'─'*40}")
        for f in fields[:5]:
            nota = (
                f"  ← '{f['valor_constante']}'" if f["es_constante"] else
                "  ← decimal"                    if f["es_decimal"]   else
                "  ← RESERVADO"                  if f["es_reservado"] else ""
            )
            print(
                f"  {f['num']:>3}  {f['posicion']:>5}  {f['longitud']:>4}  "
                f"{f['tipo']:<4}  {f['descripcion'][:45]}{nota}"
            )


# ─────────────────────────────────────────────────────────────
#  VERIFICACIONES SPOT (campos clave del fichero Poulsen-Perkins)
# ─────────────────────────────────────────────────────────────

def verificar_spot(texto_final: str, datos_json_path: Path):
    """
    Comprueba posiciones concretas contra valores esperados del caso
    Poulsen-Perkins (protocolo 02914). Solo ejecuta si el JSON activo
    es datos_211_poulsen_perkins.json.
    """
    if datos_json_path.name != "datos_211_poulsen_perkins.json":
        return  # checks específicos solo para ese caso

    print("\n" + "=" * 60)
    print("  VERIFICACIONES SPOT — Poulsen / Perkins")
    print("=" * 60)

    # Página 010 (chars 0-2399)
    p010 = texto_final[0:2400]
    # Página 020 (chars 2400-4599)
    p020 = texto_final[2400:4600]
    # Página 030 (chars 4600-6599)
    p030 = texto_final[4600:6600]

    checks = [
        # (desc, registro, pos_base1, lon, esperado)
        ("010 tag inicio",           p010, 1,    9,  "<T211010>"),
        ("010 tag fin",              p010, 2391, 10, "</T211010>"),
        ("010 fecha devengo",        p010, 14,   8,  "18092025"),
        ("010 NIF adquirente",       p010, 22,   9,  "Y5732237F"),
        ("010 importe transmision",  p010, 1733, 17, "00000000001020000000"[:17]),
        ("010 porcentaje retencion", p010, 1750, 5,  "00300"),
        ("020 tag inicio",           p020, 1,    9,  "<T211020>"),
        ("020 tag fin",              p020, 2191, 10, "</T211020>"),
        ("020 NIF slot1",            p020, 11,   9,  "Y5732237F"),
        ("020 F/J slot1",            p020, 20,   1,  "F"),
        ("020 C/O slot1",            p020, 161,  1,  "C"),
        ("020 coef_part slot1",      p020, 162,  5,  "10000"),
        ("030 tag inicio",           p030, 1,    9,  "<T211030>"),
        ("030 tag fin",              p030, 1991, 10, "</T211030>"),
        ("030 NIF slot1",            p030, 11,   9,  "Y2755912C"),
        ("030 C/O slot1",            p030, 146,  1,  "C"),
        ("030 coef_part slot1",      p030, 147,  5,  "10000"),
        ("030 fecha nac slot1",      p030, 152,  8,  "30081982"),
    ]

    todos_ok = True
    for desc, reg, pos1, lon, esperado in checks:
        pos0   = pos1 - 1
        actual = reg[pos0: pos0 + lon]
        ok     = actual == esperado
        if not ok:
            todos_ok = False
        estado = "✓" if ok else "✗"
        pad    = max(0, 35 - len(desc))
        line   = f"  [{estado}] {desc}{' '*pad}  '{actual}'"
        if not ok:
            line += f"  ← esperado '{esperado}'"
        print(line)

    print()
    if todos_ok:
        print("  Todos los checks spot son correctos.")
    else:
        print("  ATENCION: hay discrepancias.")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

def main():
    datos_path  = Path(sys.argv[1]) if len(sys.argv) > 1 \
                  else MODELIA_DIR / "Input" / "datos_211_poulsen_perkins.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 \
                  else MODELIA_DIR / "Output"

    # 1. Verificar parseo de CSVs
    verificar_csvs()

    # 2. Generar modelo
    texto_final = generar_modelo211(datos_path, output_path)

    # 3. Verificaciones spot (si aplica)
    verificar_spot(texto_final, datos_path)


if __name__ == "__main__":
    main()
