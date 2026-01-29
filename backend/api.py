from flask import Flask, jsonify
import sqlite3
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Allows JavaScript from different origins to call the API

# Database path - adjust this to match your actual database location
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "calls.db")

# Alternative: use absolute path if the above doesn't work
# DB_PATH = "/path/to/your/calls.db"


@app.route("/api/calls")
def get_calls():
    """
    Fetch all call records from the database
    Returns JSON array of call objects
    """
    try:
        # Check if database exists
        if not os.path.exists(DB_PATH):
            return jsonify({"error": "Database not found", "path": DB_PATH}), 404

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        c = conn.cursor()

        # Execute query
        c.execute("SELECT * FROM call_reports ORDER BY start_time DESC")
        rows = c.fetchall()
        conn.close()

        # Convert to list of dictionaries
        calls = [dict(row) for row in rows]

        print(f"✓ Returning {len(calls)} calls")
        return jsonify(calls)

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return jsonify({"error": "Database error", "message": str(e)}), 500
    except Exception as e:
        print(f"✗ Server error: {e}")
        return jsonify({"error": "Server error", "message": str(e)}), 500


@app.route("/api/calls/<call_id>")
def get_call(call_id):
    """
    Fetch a single call by ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM call_reports WHERE call_id = ?", (call_id,))
        row = c.fetchone()
        conn.close()

        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Call not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """
    Get aggregated statistics
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Get counts by status
        c.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'solved' THEN 1 ELSE 0 END) as solved,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END) as escalated,
                AVG(confidence) as avg_confidence
            FROM call_reports
        """
        )

        stats = c.fetchone()
        conn.close()

        return jsonify(
            {
                "total": stats[0],
                "solved": stats[1],
                "active": stats[2],
                "escalated": stats[3],
                "avg_confidence": round(stats[4], 2) if stats[4] else 0,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    """
    API info endpoint
    """
    return jsonify(
        {
            "name": "Call Center Dashboard API",
            "version": "1.0.0",
            "endpoints": {
                "/api/calls": "Get all calls",
                "/api/calls/<call_id>": "Get specific call",
                "/api/stats": "Get statistics",
            },
            "database": DB_PATH,
            "database_exists": os.path.exists(DB_PATH),
        }
    )


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Call Center Dashboard API")
    print("=" * 50)
    print(f"📁 Database: {DB_PATH}")
    print(f"✓ Database exists: {os.path.exists(DB_PATH)}")
    print("🌐 API running at: http://127.0.0.1:5000")
    print("=" * 50)
    print()

    app.run(debug=True, host="127.0.0.1", port=5000)
