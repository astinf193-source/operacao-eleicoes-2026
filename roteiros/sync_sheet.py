"""Sincroniza a planilha do Google Sheets (CSV via gviz) com dados/ocorrencias.json.

Variáveis de ambiente:
  SHEET_GVIZ_URL       (obrigatória) URL gviz com tqx=out:csv
  INCLUDE_RESPONSAVEL  "true"/"false" (padrão true) — publicar o campo "responsavel"
  ALLOW_EMPTY          "true" permite sobrescrever com lista vazia (padrão false)
  DEST                 caminho de saída (padrão dados/ocorrencias.json)
"""
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("SHEET_GVIZ_URL")
if not BASE_URL:
    sys.exit("ERRO: defina a variável SHEET_GVIZ_URL.")

def flag(name, default):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "sim", "yes")

INCLUDE_RESPONSAVEL = flag("INCLUDE_RESPONSAVEL", "true")
ALLOW_EMPTY = flag("ALLOW_EMPTY", "false")
DEST = Path(os.environ.get("DEST", "dados/ocorrencias.json"))


def fetch_csv(retries=3):
    last_error = None
    for attempt in range(1, retries + 1):
        url = f"{BASE_URL}&_={int(time.time())}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 GitHubActions-OperacaoEleicoes2026/2.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8-sig")
            head = raw.lstrip()[:200].lower()
            if head.startswith("<!doctype") or head.startswith("<html"):
                raise ValueError(
                    "A planilha retornou HTML (provável página de login). "
                    "Verifique se ela está compartilhada/publicada como 'qualquer pessoa com o link'."
                )
            return raw
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            print(f"Tentativa {attempt}/{retries} falhou: {exc}", file=sys.stderr)
            if isinstance(exc, ValueError):
                break  # não adianta repetir
            time.sleep(2 * attempt)
    sys.exit(f"ERRO: não foi possível ler a planilha ({last_error}). Arquivo mantido sem alterações.")


def clean(value):
    return (value or "").strip()


def normalize_zone(value):
    text = clean(value).upper()
    for junk in ("ZONA", "º", "°", "ª"):
        text = text.replace(junk, "")
    text = text.strip()
    return text.zfill(2) if text.isdigit() else text


def public_summary(tipo, gravidade):
    return (
        f"Ocorrência registrada: {tipo or 'não informado'} — "
        f"gravidade {gravidade or 'não informada'}."
    )


raw = fetch_csv()
reader = csv.DictReader(io.StringIO(raw))

# Cabeçalhos tolerantes a maiúsculas/minúsculas e espaços.
fieldmap = {(name or "").strip().lower(): name for name in (reader.fieldnames or [])}

def pick(row, *names):
    for name in names:
        original = fieldmap.get(name.lower())
        if original is not None:
            value = clean(row.get(original))
            if value:
                return value
    return ""

required = {"zona", "tipo"}
missing = required - set(fieldmap)
if missing:
    sys.exit(
        f"ERRO: colunas obrigatórias ausentes na planilha: {sorted(missing)}. "
        f"Colunas encontradas: {sorted(fieldmap)}. Arquivo mantido sem alterações."
    )

output = []
seen_keys = {}
skipped = 0

for row in reader:
    timestamp = pick(row, "Timestamp", "carimbo de data/hora")
    responsavel = pick(row, "Responsável pelo Registro", "Responsável", "responsavel")
    zona = normalize_zone(pick(row, "Zona"))
    local = pick(row, "Local")
    tipo = pick(row, "Tipo")
    gravidade = pick(row, "Gravidade")
    relato = pick(row, "Relato")

    if not (zona or local or tipo or gravidade):
        skipped += 1  # linha vazia / em construção
        continue

    # Mesma chave do script anterior => ids já publicados continuam estáveis.
    key = "|".join([timestamp, responsavel, zona, local, tipo, gravidade, relato])
    n = seen_keys.get(key, 0)
    seen_keys[key] = n + 1
    unique_key = key if n == 0 else f"{key}|#{n}"  # linhas idênticas não colidem
    record_id = hashlib.sha1(unique_key.encode("utf-8")).hexdigest()[:12]

    record = {
        "id": record_id,
        "timestamp": timestamp,
        "zona": zona,
        "local": local,
        "tipo": tipo,
        "gravidade": gravidade,
        "relato": public_summary(tipo, gravidade),
    }
    if INCLUDE_RESPONSAVEL:
        record["responsavel"] = responsavel
    output.append(record)

if not output and DEST.exists() and not ALLOW_EMPTY:
    try:
        previous = json.loads(DEST.read_text(encoding="utf-8"))
    except ValueError:
        previous = []
    if previous:
        sys.exit("ERRO: planilha sem registros válidos; mantendo o arquivo anterior (use ALLOW_EMPTY=true para forçar).")

new_text = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
old_text = DEST.read_text(encoding="utf-8") if DEST.exists() else None

if new_text == old_text:
    print(f"Sem alterações ({len(output)} registros).")
else:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(DEST)  # escrita atômica
    print(f"Sincronizados {len(output)} registros.")

print(f"Linhas ignoradas (vazias): {skipped}")
if INCLUDE_RESPONSAVEL:
    print(f"Com responsável informado: {sum(1 for x in output if x.get('responsavel'))}")
else:
    print("Campo 'responsavel' NÃO publicado (INCLUDE_RESPONSAVEL=false).")
