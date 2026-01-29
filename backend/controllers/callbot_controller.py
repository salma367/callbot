from backend.models.call_report import CallReport
from backend.repositories.call_report_repo import save_call_report
from backend.services.llm_service import LLMService

llm_service = LLMService()  # make sure this is the same service used elsewhere


def finalize_call(call_session):
    print(
        f"[FINALIZE] call_session.clarification_count = {getattr(call_session, 'clarification_count', 'NOT SET')}"
    )
    report = CallReport(call_session)
    print(f"[FINALIZE] report.clarification_count = {report.clarification_count}")

    # Pass the llm_service to generate_summary
    report.generate_summary(llm_service=llm_service)

    save_call_report(report)
    print(f"[REPORT] Saved report for Call ID {call_session.call_id}")
