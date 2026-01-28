# backend/models/agent.py


class Agent:
    def __init__(self, agent_id, name, department):
        self.agent_id = agent_id
        self.name = name
        self.department = department

    def take_over_call(self, session):
        session.escalated = True
        session.agent_id = self.agent_id
        session.status = "ESCALATED"

        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "department": self.department,
            "session_id": session.call_id,
            "message": "Agent has taken over the call",
        }
