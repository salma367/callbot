#!/usr/bin/env python3
"""
Interactive CLI test for Callbot - no UI required
Allows you to feed text questions and see:
- NLU (Intent detection)
- LLM (Response generation)
- TTS (Audio output)
- Full pipeline output
"""

import sys
import os
from backend.models.call_session import CallSession
from backend.services.voice_pipeline import VoicePipeline
from backend.services.nlu_service import NLUService
from backend.services.llm_service import LLMService
from backend.services.tts_service import TTSService
from backend.services.rag_service import RAGService
from backend.logs.logger import Logger


class CallbotCLITest:
    def __init__(self):
        print("[INIT] Initializing Callbot components...")
        self.pipeline = VoicePipeline()
        self.nlu = NLUService()
        self.llm = LLMService()
        self.tts = TTSService()
        self.rag = RAGService()
        self.logger = Logger()

        # Start a call session
        self.call_session = CallSession(
            call_id=None,
            client_id=None,
            user_name="Test User",
            phone_number="+212000000000",
            agent_id="test_agent",
        )
        self.logger.log_session(self.call_session.call_id, "TESTING")
        print(f"[INIT] ✓ Call session started: {self.call_session.call_id}\n")

    def process_text_input(self, user_input: str, generate_audio=False):
        """
        Process user text input through the pipeline.

        Args:
            user_input: User text to process
            generate_audio: Whether to generate TTS audio (default: False for speed)
        """
        print("=" * 80)
        print(f"USER INPUT: {user_input}")
        print("=" * 80)

        # Add to session
        self.call_session.add_message(user_input)

        # ─────────────────────────────────────────────────────────────
        # STEP 1: NLU (Intent Detection)
        # ─────────────────────────────────────────────────────────────
        print("\n[NLU] Detecting intent...")
        detected_intent = self.nlu.detect_intent(user_input)
        intent_name = detected_intent.name if detected_intent else "UNKNOWN"
        intent_confidence = detected_intent.confidence if detected_intent else 0.0

        print(f"  Intent: {intent_name}")
        print(f"  Confidence: {intent_confidence:.2%}")

        # ─────────────────────────────────────────────────────────────
        # STEP 2: RAG (Context Retrieval)
        # ─────────────────────────────────────────────────────────────
        print("\n[RAG] Retrieving relevant FAQ context...")
        contexts = self.rag.retrieve(user_input, k=3)
        if contexts:
            print(f"  Found {len(contexts)} relevant context(s):")
            for i, ctx in enumerate(contexts, 1):
                # Truncate long contexts for display
                display_ctx = ctx[:200] + "..." if len(ctx) > 200 else ctx
                print(f"    {i}. {display_ctx}")
            context_str = "\n".join(contexts)
        else:
            print("  No relevant context found")
            context_str = ""

        # ─────────────────────────────────────────────────────────────
        # STEP 3: LLM (Response Generation)
        # ─────────────────────────────────────────────────────────────
        print("\n[LLM] Generating response...")
        try:
            response_text = self.llm.generate_response(
                user_text=user_input,
                context=context_str,
                language="fr",
                intent=intent_name,
            )
            print(f"  Response: {response_text}")
        except Exception as e:
            response_text = "Je suis désolé, je n'ai pas pu générer de réponse."
            print(f"  [ERROR] {e}")
            print(f"  Fallback: {response_text}")

        # ─────────────────────────────────────────────────────────────
        # STEP 4: TTS (Text-to-Speech)
        # ─────────────────────────────────────────────────────────────
        if generate_audio:
            print("\n[TTS] Generating audio...")
            try:
                audio_path = self.tts.synthesize(response_text, "fr")
                if audio_path:
                    print(f"  ✓ Audio saved: {audio_path}")
                else:
                    print("  ✗ Failed to generate audio")
            except Exception as e:
                print(f"  ✗ TTS Error: {e}")
        else:
            print("\n[TTS] Skipped (use --no-audio flag to disable)")

        # ─────────────────────────────────────────────────────────────
        # STEP 5: Orchestrator Processing
        # ─────────────────────────────────────────────────────────────
        print("\n[ORCHESTRATOR] Processing turn...")
        try:
            orch_result = self.pipeline.orchestrator.process_turn(
                call_session=self.call_session,
                intent=detected_intent,
                asr_conf=0.95,  # Simulated high confidence (text input is 100% accurate)
                nlu_conf=intent_confidence,
                ambiguous=False,
            )
            print(f"  Decision: {orch_result.get('decision', 'UNKNOWN')}")
            print(f"  Reason: {orch_result.get('reason', 'N/A')}")
            if "message" in orch_result:
                print(f"  Message: {orch_result['message']}")
        except Exception as e:
            print(f"  [ERROR] {e}")

        # ─────────────────────────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────────────────────────
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Intent:          {intent_name} ({intent_confidence:.2%})")
        print(f"Response:        {response_text}")
        print(f"Session ID:      {self.call_session.call_id}")
        print(f"Messages:        {len(self.call_session.messages)}")
        print("")

    def interactive_mode(self, generate_audio=True):
        """
        Interactive mode: Continuously prompt for user input.
        Type 'quit' or 'exit' to end the session.
        """
        print("\n" + "=" * 80)
        print("CALLBOT INTERACTIVE TEST")
        print("=" * 80)
        print("Commands:")
        print("  - Type your question in French or English")
        print("  - Type 'quit' or 'exit' to end the session")
        print("  - Type 'audio' to toggle audio generation")
        print("  - Type 'status' to show session info")
        print("=" * 80 + "\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit"]:
                    print("\n[INFO] Ending call session...")
                    self.call_session.end_call(status="ENDED")
                    print(f"[INFO] Session ended. Call ID: {self.call_session.call_id}")
                    break

                if user_input.lower() == "status":
                    print(f"\n--- Session Status ---")
                    print(f"Call ID: {self.call_session.call_id}")
                    print(f"Status: {self.call_session.status}")
                    print(f"Messages: {len(self.call_session.messages)}")
                    print(f"Current Intent: {self.call_session.current_intent}")
                    print(f"Global Confidence: {self.call_session.global_confidence}")
                    print("")
                    continue

                if user_input.lower() == "audio":
                    generate_audio = not generate_audio
                    status = "ON" if generate_audio else "OFF"
                    print(f"[INFO] Audio generation: {status}\n")
                    continue

                self.process_text_input(user_input, generate_audio=generate_audio)

            except KeyboardInterrupt:
                print("\n\n[INFO] Interrupted by user")
                self.call_session.end_call(status="INTERRUPTED")
                break
            except Exception as e:
                print(f"\n[ERROR] {e}")
                print("Continuing...\n")

    def batch_mode(self, questions: list, generate_audio=False):
        """
        Batch mode: Process a list of predefined questions.

        Args:
            questions: List of questions to process
            generate_audio: Whether to generate TTS audio
        """
        print(f"\n[BATCH] Processing {len(questions)} questions...\n")

        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Processing question...")
            self.process_text_input(question, generate_audio=generate_audio)

        self.call_session.end_call(status="COMPLETED")
        print(f"\n[BATCH] Completed. Session ID: {self.call_session.call_id}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive CLI test for Callbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python test2.py
  
  # Interactive with audio generation
  python test2.py --audio
  
  # Batch test with predefined questions
  python test2.py --batch
  
  # Test with specific questions
  python test2.py --batch --questions "How much is insurance?" "I want to make a claim"
        """,
    )

    parser.add_argument(
        "--no-audio", action="store_true", help="Disable TTS audio generation"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run in batch mode with predefined questions",
    )
    parser.add_argument(
        "--questions", nargs="+", help="Custom questions for batch mode"
    )

    args = parser.parse_args()

    try:
        tester = CallbotCLITest()

        if args.batch:
            # Use custom questions or predefined ones
            if args.questions:
                questions = args.questions
            else:
                questions = [
                    "Bonjour, je voudrais déclarer un sinistre",
                    "Combien coûte une assurance habitation?",
                    "Suis-je couvert pour les dégâts d'eau?",
                    "Comment faire un paiement?",
                    "Au revoir",
                ]

            tester.batch_mode(questions, generate_audio=not args.no_audio)
        else:
            # Interactive mode
            tester.interactive_mode(generate_audio=not args.no_audio)

    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
