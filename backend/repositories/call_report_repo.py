import sqlite3

DB_PATH = "calls.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

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
            summary TEXT,
            confidence REAL,
            clarification_count INTEGER
        )
        """
    )

    conn.commit()
    conn.close()


def save_call_report(report):
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Log the status being saved
    status_to_save = getattr(report, "status", "UNKNOWN")
    print(
        f"[SAVE_REPORT] Saving call {getattr(report, 'call_id', 'UNKNOWN')} with status: {status_to_save}"
    )

    cur.execute(
        """
        INSERT OR REPLACE INTO call_reports (
            call_id, client_id, user_name, phone_number, agent_name, status,
            start_time, end_time, summary, confidence, clarification_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            getattr(report, "call_id", "Unknown"),
            getattr(report, "client_id", "Unknown"),
            getattr(report, "user_name", "Unknown"),
            getattr(report, "phone_number", "Unknown"),
            getattr(report, "agent_name", "Unknown"),
            status_to_save,
            getattr(report, "start_time", None).isoformat(),
            getattr(report, "end_time", None).isoformat(),
            getattr(report, "summary_text", ""),
            (
                float(getattr(report, "confidence", 0.0))
                if getattr(report, "confidence", None) is not None
                else 0.0
            ),
            int(getattr(report, "clarification_count", 0)),
        ),
    )

    conn.commit()
    conn.close()
