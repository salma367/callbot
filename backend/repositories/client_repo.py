import sqlite3
import uuid

DB_PATH = "calls.db"


def init_clients_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            full_name TEXT,
            phone_number TEXT UNIQUE
        )
        """
    )

    conn.commit()
    conn.close()


def get_or_create_client(full_name: str, phone_number: str) -> str:
    """
    Look up a client by phone_number.
    If phone exists but full_name is different (case-insensitive), raise an error.
    If not found, create a new client.
    Returns client_id.
    """
    init_clients_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Normalize input for comparison
    normalized_name = full_name.strip().lower()

    cur.execute(
        "SELECT client_id, full_name FROM clients WHERE phone_number = ?",
        (phone_number,),
    )
    row = cur.fetchone()

    if row:
        client_id, existing_name = row
        if existing_name.strip().lower() != normalized_name:
            conn.close()
            raise ValueError(
                f"Le numéro {phone_number} est déjà associé à un autre utilisateur."
            )
    else:
        client_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO clients (client_id, full_name, phone_number) VALUES (?, ?, ?)",
            (client_id, full_name.strip(), phone_number),
        )
        conn.commit()

    conn.close()
    return client_id


def get_client(client_id: str):
    """Return client info by ID."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT client_id, full_name, phone_number FROM clients WHERE client_id = ?",
        (client_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"client_id": row[0], "full_name": row[1], "phone_number": row[2]}
    return None
