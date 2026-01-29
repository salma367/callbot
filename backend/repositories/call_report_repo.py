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
            summary TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save_call_report(report):
    init_db()

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
            getattr(report, "user_name", "Unknown"),
            getattr(report, "phone_number", "Unknown"),
            getattr(report, "agent_name", "Unknown"),
            getattr(report, "status", "UNKNOWN"),
            getattr(report, "start_time", None).isoformat(),
            getattr(report, "end_time", None).isoformat(),
            getattr(report, "summary_text", ""),
        ),
    )

    conn.commit()
    conn.close()
