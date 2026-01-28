# backend/logs/logger.py

import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("backend/logs/data")
LOG_DIR.mkdir(parents=True, exist_ok=True)


class Logger:
    def __init__(self, log_level="INFO"):
        self.log_level = log_level

    def _write(self, filename, payload):
        filepath = LOG_DIR / filename
        payload["timestamp"] = datetime.utcnow().isoformat()

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def log_session(self, session_id, caller_type):
        self._write(
            "sessions.log", {"session_id": session_id, "caller_type": caller_type}
        )

    def log_confidence(self, session_id, asr, nlu, global_score):
        self._write(
            "confidence.log",
            {
                "session_id": session_id,
                "asr_confidence": asr,
                "nlu_confidence": nlu,
                "global_confidence": global_score,
            },
        )

    def log_escalation(self, session_id, reason):
        self._write("escalations.log", {"session_id": session_id, "reason": reason})

    def log_decision(self, session_id, decision, reason):
        self._write(
            "decisions.log",
            {"session_id": session_id, "decision": decision, "reason": reason},
        )

    def log_agent_takeover(self, session_id, agent_id):
        self._write(
            "agent.log",
            {"session_id": session_id, "agent_id": agent_id, "event": "AGENT_TAKEOVER"},
        )
