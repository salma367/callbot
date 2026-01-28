# test.py
import uuid
from backend.models.call_session import CallSession
from backend.controllers.callbot_controller import finalize_call
from backend.repositories.call_report_repo import init_db
from backend.services.llm_service import LLMService

# 1️⃣ Initialize DB
init_db()

# 2️⃣ Create a fake call session
call_id = str(uuid.uuid4())
call_session = CallSession(call_id=call_id, client_id="CLIENT_123")

# 3️⃣ Simulate conversation
call_session.add_message("Bonjour, j'ai un problème avec mon contrat d'assurance auto.")
call_session.add_message("Je n'arrive pas à faire une réclamation pour mon sinistre.")
call_session.add_message("Pouvez-vous m'aider à savoir quoi faire ?")

# 4️⃣ End call and generate report
llm_service = LLMService()  # make sure GROQ_API_KEY is set
finalize_call(call_session, llm_service)

# 5️⃣ Print summary for demo
from backend.models.call_report import CallReport

report = CallReport(call_session)
report.generate_summary(llm_service)
print("\n=== CALL SUMMARY ===")
print(report.summary_text)
