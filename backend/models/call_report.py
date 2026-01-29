import sqlite3
from datetime import datetime
from backend.repositories.client_repo import get_client  # new import

DB_PATH = "calls.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- call_reports table ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS call_reports (
            call_id TEXT PRIMARY KEY,
            client_id TEXT,
            user_name TEXT,
            phone_number TEXT,
            agent_name TEXT,
            status TEXT,
            start_time TEXT,
            end_time TEXT,
            summary TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save_call_report(report):
    """Save a CallReport instance to SQLite."""
    init_db()

    # --- Fetch latest client info from DB if possible ---
    user_name = report.user_name
    phone_number = report.phone_number
    if report.client_id:
        client = get_client(report.client_id)
        if client:
            user_name = client["user_name"]
            phone_number = client["phone_number"]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR REPLACE INTO call_reports (
            call_id, client_id, user_name, phone_number, agent_name, status,
            start_time, end_time, summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            getattr(report, "call_id", "Unknown"),
            getattr(report, "client_id", "Unknown"),
            user_name,
            phone_number,
            getattr(report, "agent_name", "Unknown"),
            getattr(report, "status", "UNKNOWN"),
            getattr(report, "start_time", datetime.now()).isoformat(),
            getattr(report, "end_time", datetime.now()).isoformat(),
            getattr(report, "summary_text", ""),
        ),
    )

    conn.commit()
    conn.close()


class CallReport:
    def __init__(self, call_session):
        self.call_id = call_session.call_id
        self.client_id = call_session.client_id
        self.user_name = getattr(call_session, "user_name", "UNKNOWN")
        self.phone_number = getattr(call_session, "phone_number", "UNKNOWN")
        self.agent_name = getattr(call_session, "agent_name", "Unknown")
        self.status = getattr(call_session, "status", "UNKNOWN")
        self.start_time = getattr(call_session, "start_time", datetime.now())
        self.end_time = getattr(call_session, "end_time", datetime.now())
        self.messages = getattr(call_session, "messages", [])
        self.summary_text = None

    def generate_summary(self, llm_service=None):
        if llm_service:
            # call your LLM summarization here
            transcript = "\n".join(self.messages)
            prompt = f"""
            Résume l’appel suivant de manière professionnelle et concise.
            Conversation:
            {transcript}
            """
            self.summary_text = llm_service.generate_response(
                user_text=prompt,
                context="",
                language="fr",
                intent="CALL_SUMMARY",
            )
        else:
            duration = (self.end_time - self.start_time).seconds
            self.summary_text = (
                f"Call {self.call_id} lasted {duration}s. "
                f"{len(self.messages)} messages. Final status: {self.status}."
            )

        return self.summary_text
