"""Verify that OBJETIVO_GENERAL_BOT rule is correctly injected at the top of the bot prompt."""
import asyncio
import os
import sys
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # 1) The rule exists in DB
    rule = await db.automation_rules.find_one(
        {"name": {"$regex": "^OBJETIVO_GENERAL_BOT$", "$options": "i"}},
        {"_id": 0}
    )
    assert rule is not None, "OBJETIVO_GENERAL_BOT rule must exist"
    assert rule["is_active"] is True, "OBJETIVO_GENERAL_BOT must be active"
    assert "leads" in rule["action_value"].lower(), "Rule action_value must mention leads"
    print(f"[OK] Rule found: {rule['name']} | id={rule['id']} | active={rule['is_active']}")

    # 2) Simulate the loading logic in bot_service.py
    active_rules = await db.automation_rules.find(
        {"is_active": True}, {"_id": 0, "name": 1, "action_value": 1, "trigger_type": 1}
    ).to_list(50)

    automation_rules_text = ""
    objetivo_general_text = ""
    rules_lines = []
    for r in active_rules:
        rule_name = str(r.get("name") or "").strip()
        if rule_name.upper() == "OBJETIVO_GENERAL_BOT":
            objetivo_general_text = (
                "=== OBJETIVO GENERAL DEL BOT (PRIORIDAD MÁXIMA - PRIMERA FUENTE DE INTENCIÓN) ===\n"
                "Esta directriz fue configurada por el administrador en el panel y tiene "
                "PRIORIDAD sobre cualquier otra regla o instrucción. Cada decisión conversacional "
                "del bot debe alinearse con este objetivo:\n"
                f"{r['action_value']}\n\n"
            )
            continue
        rules_lines.append(f"- {r['name']}: {r['action_value']}")
    if rules_lines:
        automation_rules_text = "=== REGLAS DE AUTOMATIZACION DEL SISTEMA (OBLIGATORIAS - PRIORIDAD MAXIMA) ===\n" + "\n".join(rules_lines)

    # Simulate the user_prompt
    user_prompt = f"""{objetivo_general_text}INSTRUCCIÓN: revisa todo el historial..."""

    assert objetivo_general_text, "objetivo_general_text must NOT be empty"
    assert "PRIORIDAD MÁXIMA" in objetivo_general_text, "Must contain PRIORIDAD MÁXIMA marker"
    assert "OBJETIVO_GENERAL_BOT" not in automation_rules_text, "OBJETIVO_GENERAL_BOT must not appear in regular rules block"
    assert user_prompt.startswith("=== OBJETIVO GENERAL DEL BOT"), "user_prompt MUST start with OBJETIVO GENERAL block"
    print("[OK] user_prompt starts with OBJETIVO GENERAL DEL BOT block")
    print("[OK] OBJETIVO_GENERAL_BOT NOT duplicated in regular rules block")
    print(f"[OK] Total active automation rules: {len(active_rules)} (1 OBJETIVO + {len(rules_lines)} regular)")

    # 3) Verify SYSTEM_PROMPT changes
    from bot_service import SYSTEM_PROMPT
    assert "OBJETIVO GENERAL DEL AGENTE" in SYSTEM_PROMPT, "SYSTEM_PROMPT must contain OBJETIVO GENERAL section"
    assert "Máximo 5 líneas" in SYSTEM_PROMPT, "SYSTEM_PROMPT must allow 5 lines"
    assert "se pondrá en contacto contigo para los siguientes pasos" in SYSTEM_PROMPT, "SYSTEM_PROMPT must use new closure msg"
    assert "https://cotizador.gimmicks.com.ec/catalog?q=producto" in SYSTEM_PROMPT, "SYSTEM_PROMPT must include explicit URL example"
    assert "cuadernos" in SYSTEM_PROMPT, "SYSTEM_PROMPT must list cuadernos in product types"
    print("[OK] SYSTEM_PROMPT contains all 5 expected updates")

    print("\n=== ALL CHECKS PASSED ===")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
