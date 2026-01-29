# test.py
from datetime import datetime, timedelta
from backend.models.call_session import CallSession
from backend.models.call_report import CallReport
from backend.repositories.call_report_repo import save_call_report


# Simulate a call session
def create_fake_call():
    call = CallSession(
        call_id=None,  # will auto-generate
        client_id=None,  # will auto-generate
        user_name="Jean Dupont",
        phone_number="+212612345678",
        agent_id="agent_001",
    )

    # Simulate messages
    call.add_message("Bonjour, je voudrais déclarer un sinistre.")
    call.add_message("Bien sûr, pouvez-vous me donner votre numéro de contrat ?")
    call.add_message("123456789")
    call.add_message("Merci, votre demande est enregistrée.")

    # Simulate call end
    call.end_call(status="RESOLVED")

    # Optional: simulate call duration
    call.start_time -= timedelta(minutes=5)

    return call


def test_save_report():
    call_session = create_fake_call()

    # Generate report
    report = CallReport(call_session)
    report.generate_summary()  # will generate a fallback summary if LLM not provided

    # Save to DB
    save_call_report(report)

    print("Report saved successfully!")
    print(f"Call ID: {report.call_id}")
    print(f"User Name: {report.user_name}")
    print(f"Phone Number: {report.phone_number}")
    print(f"Status: {report.status}")
    print(f"Summary: {report.summary_text}")


if __name__ == "__main__":
    test_save_report()
