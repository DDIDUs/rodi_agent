import json
from .planner import PlannerAgent
from .auditor import AuditorAgent
from .llm_client import OpenAILLMClient

class Orchestrator:
    def __init__(self, llm_client: OpenAILLMClient):
        self.planner = PlannerAgent(llm_client)
        self.auditor = AuditorAgent(llm_client)

    def generate_approved_checklist(self, instruction: str, max_rounds: int = 3) -> str:
        print("\n--- [Analysis: Generating Feature Checklist (Planner)] ---")
        feature_checklist = self.planner.generate_initial_checklist(instruction)
        print(f"Initial Feature Checklist:\n{feature_checklist}\n")

        for round_idx in range(max_rounds):
            print(f"--- [Audit Round {round_idx + 1}/{max_rounds}] ---")
            audit_result = self.auditor.evaluate_checklist(instruction, feature_checklist)
            
            decision = audit_result.get("decision", "FAIL").upper()
            issues = audit_result.get("issues", [])
            summary = audit_result.get("summary", "")

            print(f"Auditor Decision: {decision}")
            print(f"Summary: {summary}")
            if issues:
                print("Issues Found:")
                for issue in issues:
                    print(f" - [{issue.get('severity', 'high').upper()}] {issue.get('type')}: {issue.get('message')} (Suggested: {issue.get('suggested_fix')})")

            if decision == "PASS":
                print("\n✅ Feature checklist successfully approved by Auditor.")
                return feature_checklist
            elif decision == "REVISE":
                if round_idx < max_rounds - 1:
                    print("\n⏳ Revising feature checklist based on Auditor's feedback...")
                    audit_feedback_str = json.dumps(issues, indent=2, ensure_ascii=False)
                    feature_checklist = self.planner.revise_checklist(instruction, feature_checklist, audit_feedback_str)
                    print(f"Revised Feature Checklist:\n{feature_checklist}\n")
                else:
                    print("\n❌ Max revision rounds reached. Auditor still failing.")
                    return None
            else:
                print("\n❌ Auditor returned FAIL. Terminating generation.")
                return None
            
        return None

    def generate_approved_checklist_stream(self, instruction: str, max_rounds: int = 3):
        """Generator version for streaming apps."""
        yield {"type": "status", "content": "Planner: Generating initial feature checklist..."}
        feature_checklist = self.planner.generate_initial_checklist(instruction)
        yield {"type": "checklist_draft", "content": feature_checklist}

        for round_idx in range(max_rounds):
            yield {"type": "status", "content": f"Auditor: Evaluating feature checklist (Round {round_idx + 1}/{max_rounds})..."}
            audit_result = self.auditor.evaluate_checklist(instruction, feature_checklist)
            
            decision = audit_result.get("decision", "FAIL").upper()
            issues = audit_result.get("issues", [])
            summary = audit_result.get("summary", "")

            yield {"type": "audit_result", "content": audit_result}

            if decision == "PASS":
                yield {"type": "status", "content": "Feature checklist approved by Auditor ✅."}
                yield {"type": "checklist", "content": feature_checklist}
                return feature_checklist
            elif decision == "REVISE":
                if round_idx < max_rounds - 1:
                    yield {"type": "status", "content": "Planner: Revising feature checklist based on feedback ⏳..."}
                    audit_feedback_str = json.dumps(issues, indent=2, ensure_ascii=False)
                    feature_checklist = self.planner.revise_checklist(instruction, feature_checklist, audit_feedback_str)
                    yield {"type": "checklist_draft", "content": feature_checklist}
                else:
                    yield {"type": "error", "content": "Max revision rounds reached. Auditor still failing ❌."}
                    return None
            else:
                yield {"type": "error", "content": "Auditor returned FAIL. Terminating generation ❌."}
                return None
            
        return None

    def verify_generated_code(self, instruction: str, feature_checklist: str, generated_code: str) -> str:
        """Runs a single verification pass for the generated code."""
        return self.auditor.verify_code(instruction, feature_checklist, generated_code)
