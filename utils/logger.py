from datetime import datetime, timezone

def iso_now() -> str:
    # UTC ISO (simple). Si tu veux timezone Mauritius: on peut le faire.
    return datetime.now(timezone.utc).isoformat()

def push_log(cfg: dict, msg: str, max_items: int = 50) -> None:
    cfg.setdefault("logs", [])
    cfg["logs"].insert(0, {"ts": iso_now(), "msg": msg})
    cfg["logs"] = cfg["logs"][:max_items]