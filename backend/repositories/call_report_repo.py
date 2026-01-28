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
            call_id, client_id, agent_name, status,
            start_time, end_time, summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.call_id,
            report.client_id,
            report.agent_name,
            report.status,
            report.start_time.isoformat(),
            report.end_time.isoformat(),
            report.summary_text,
        ),
    )

    conn.commit()
    conn.close()
