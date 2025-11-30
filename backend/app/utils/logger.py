import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

BASE_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
BASE_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_chatbot_call(
    query: str,
    history: Any,
    reply: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    record: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "chatbot",
        "query": query,
        "history": history,
        "reply": reply,
    }
    if extra:
        record["extra"] = extra
    _write_jsonl(BASE_LOG_DIR / "chatbot_logs.jsonl", record)


def log_copilot_call(
    mode: str,  # "suggest-reply" | "summarize-case"
    payload: Any,
    output: Any,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    record: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "copilot",
        "mode": mode,
        "payload": payload,
        "output": output,
    }
    if extra:
        record["extra"] = extra
    _write_jsonl(BASE_LOG_DIR / "copilot_logs.jsonl", record)
