
This file provides guidance to Claude Code when working inside this repository.

Scope
Claude may only read or use files inside:
~/Desktop/MODELIA/
Do not inspect or reference anything outside this folder.

Project Overview
Python system that generates fixed-width .txt files for Modelo 211 (AEAT).
Form: IRNR — Retención en la adquisición de bienes inmuebles a no residentes sin establecimiento permanente.
The goal is to generate a TXT file fully compliant with AEAT official fixed-width record design, importable without validation errors.

Folder Structure
MODELIA/
├── KB/
│   ├── 21101-Table1.csv
│   ├── 21102-Table1.csv
│   ├── 21103-Table1.csv
│   └── (normative documentation, specs)
│
├── Input/
│   └── datos_211.json
│
├── Code/
│   ├── modelo211_generator.py
│   └── run_211.py
│
└── Output/
    ├── 211.txt
    ├── diagnostico_010.json
    ├── diagnostico_020.json
    └── diagnostico_030.json

Execution Commands
From project root:
python3 Code/run_211.py Input/datos_211.json Output/
Default behavior:
* Reads JSON from /Input
* Reads CSV specifications from /KB
* Writes final TXT and diagnostics to /Output

Architecture
Pipeline implemented in Code/modelo211_generator.py.
1️⃣ parse_csv_page(pagina)
Reads CSV specification from /KB.
Rules:
* Separator: ;
* Skip first 4 rows
* Filter rows where Nº is numeric
* Extract:
    * num
    * posicion
    * longitud
    * tipo
    * es_constante
    * valor_constante
    * es_decimal
    * es_reservado
Constants extracted via: Constante "VALUE"

2️⃣ formatear_campo(definicion, valor)
Formats exactly to required fixed length.
Rules:
Alphanumeric (A, An)
* Left aligned
* Right padded with spaces
Numeric (Num)
* Right aligned
* Left padded with zeros
Decimals
* If "ent." in Contenido → multiply by 100 and convert to integer
Reserved
* Fill with spaces
Raise ValueError if final length ≠ defined length.

3️⃣ generar_json_formateado()
Maps JSON input fields to CSV field numbers.
Produces diagnostic JSON:
{
  field_num,
  valor_raw,
  valor_formateado,
  ok
}
Field 105 (complementaria) handled explicitly.

4️⃣ json_a_registro()
Builds fixed-length string using:
posicion - 1 (base 0)
Validations:
* Exact total length
* Correct start tag <T211XXX>
* Correct end tag </T211XXX>
No line breaks in final file.

5️⃣ generar_modelo211()
Orchestrator.
Pages:
* 010 → always
* 020 → if num_adquirentes > 1
* 030 → if num_transmitentes > 1
Final Output:
* Output/211.txt
* One diagnostic JSON per generated page

Input JSON Rules
Located in /Input/datos_211.json
Structure:
pagina_010
  header
  adquirente
  representante_adquirente
  transmitente
  inmueble
  liquidacion
  complementaria
  pago
  contacto
Monetary example:
* 168000.00 → 16800000 → padded to 17 chars
Percentages:
* 3.00 → 300 → padded to 5 chars
Empty:
* An → spaces
* Num → zeros

Strict Compliance Rules
1. All fields must match fixed length exactly.
2. No separators in numeric fields.
3. No line breaks in final TXT.
4. Do not modify files inside /KB.
5. Do not manually edit files inside /Output.
6. All business logic must live in /Code.

Primary Objective
Generate a legally valid AEAT Modelo 211 TXT file that passes official validation without errors.

