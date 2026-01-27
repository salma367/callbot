def intent_to_response(intent_name: str) -> str:
    return {
        "GREETING": "Hello! How can I help you today?",
        "PROBLEM": "I understand. Please explain your problem and I will assist you.",
        "GOODBYE": "Thank you for calling. Have a nice day!",
        "UNKNOWN": "I'm sorry, I didn't fully understand. Could you please repeat?",
    }.get(intent_name, "Could you please repeat?")
