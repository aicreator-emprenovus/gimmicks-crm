"""Reproduce the bug where a malformed JSON from the LLM leaked the raw dump
to the customer (Patricia Tito conversation). Verify the 3-tier safety net."""
import sys
sys.path.insert(0, "/app/backend")

from bot_service import _repair_json, _extract_response_field, _looks_like_json
import json


# Exact text the customer received in the bug report (broken trailing comma)
LEAKED = '''{ "response": "Perfecto, Patricia. Ahora, ¿podrías proporcionarme el nombre de tu empresa?", "extracted_data": { "correo": "mon76@hotmail.es" }, "catalog_search": null, "intent": "cotizacion_directa", "lead_quality": "tibio", "category": "cotizacion_directa", "needs_quote": false, "needs_human": false, "conversation_summary": "Patricia Tito está interesada en el producto GIMK-Q01-044 y busca cotización. Desea logotipo a 1 color y ha proporcionado su correo.",
}'''

# 1. Strict json.loads must FAIL (proving the original bug)
try:
    json.loads(LEAKED)
    raise AssertionError("LEAKED parsed as valid JSON; bug premise wrong")
except json.JSONDecodeError:
    print("[OK] Original LEAKED text fails strict json.loads (reproduces bug)")

# 2. _repair_json + json.loads must succeed
repaired = _repair_json(LEAKED)
parsed = json.loads(repaired)
assert parsed["response"].startswith("Perfecto, Patricia")
print(f"[OK] _repair_json fixed trailing comma. response={parsed['response'][:60]!r}")

# 3. _extract_response_field must work even on raw broken text
fished = _extract_response_field(LEAKED)
assert fished.startswith("Perfecto, Patricia")
print(f"[OK] _extract_response_field recovered: {fished[:60]!r}")

# 4. _looks_like_json detects this leaked blob
assert _looks_like_json(LEAKED)
print("[OK] _looks_like_json detects leaked JSON dumps")

# 5. _looks_like_json does NOT trigger on legitimate Spanish text
legit = "¡Claro! Aquí puedes ver las opciones de tomatodos: https://cotizador.gimmicks.com.ec/catalog?q=tomatodos. Revísalas."
assert not _looks_like_json(legit), f"False positive on legit text: {legit!r}"
print("[OK] _looks_like_json does NOT false-positive on regular replies")

# 6. Smart quotes and additional malformations
broken = '{"response": "Hola"' + ',' + ' "intent": "saludo",}'
assert _repair_json(broken).count(",}") == 0
assert json.loads(_repair_json(broken))["response"] == "Hola"
print("[OK] _repair_json handles trailing commas before }")

# 7. Smart quotes
smart = '{\u201cresponse\u201d: \u201cHola\u201d}'
fixed = _repair_json(smart)
assert json.loads(fixed)["response"] == "Hola"
print("[OK] _repair_json handles smart quotes")

# 8. The simulated LLM fallback path (when even repair fails)
truly_broken = '{ "response: missing close quote'
assert not _looks_like_json(truly_broken) or _extract_response_field(truly_broken) == ""
fished2 = _extract_response_field(truly_broken)
print(f"[OK] Unrecoverable JSON: extract returns {fished2!r} (caller falls back to safe message)")

print("\n=== ALL JSON SAFETY-NET CHECKS PASSED ===")
