import json
from .planner import PlannerAgent
from .auditor import AuditorAgent
from .llm_client import OpenAILLMClient

class Orchestrator:
    def __init__(self, llm_client: OpenAILLMClient):
        self.planner = PlannerAgent(llm_client)
        self.auditor = AuditorAgent(llm_client)

    def generate_approved_todo(self, instruction: str, max_rounds: int = 3) -> str:
        print("\n--- [Analysis: Generating TODO List (Planner)] ---")
        todo_list = self.planner.generate_initial_todo(instruction)
        print(f"Initial TODO:\n{todo_list}\n")

        for round_idx in range(max_rounds):
            print(f"--- [Audit Round {round_idx + 1}/{max_rounds}] ---")
            audit_result = self.auditor.evaluate_todo(instruction, todo_list)
            
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
                print("\n✅ TODO List successfully approved by Auditor.")
                return todo_list
            elif decision == "REVISE":
                if round_idx < max_rounds - 1:
                    print("\n⏳ Revising TODO list based on Auditor's feedback...")
                    audit_feedback_str = json.dumps(issues, indent=2, ensure_ascii=False)
                    todo_list = self.planner.revise_todo(instruction, todo_list, audit_feedback_str)
                    print(f"Revised TODO:\n{todo_list}\n")
                else:
                    print("\n❌ Max revision rounds reached. Auditor still failing.")
                    # Return the latest list or none depending on policy. Going strict here.
                    return None
            else:
                print("\n❌ Auditor returned FAIL. Terminating generation.")
                return None
            
        return None

    def generate_approved_todo_stream(self, instruction: str, max_rounds: int = 3):
        """Generator version for streaming apps."""
        yield {"type": "status", "content": "Planner: Generating initial TODO list..."}
        todo_list = self.planner.generate_initial_todo(instruction)
        yield {"type": "todo_draft", "content": todo_list}

        for round_idx in range(max_rounds):
            yield {"type": "status", "content": f"Auditor: Evaluating TODO list (Round {round_idx + 1}/{max_rounds})..."}
            audit_result = self.auditor.evaluate_todo(instruction, todo_list)
            
            decision = audit_result.get("decision", "FAIL").upper()
            issues = audit_result.get("issues", [])
            summary = audit_result.get("summary", "")

            yield {"type": "audit_result", "content": audit_result}

            if decision == "PASS":
                yield {"type": "status", "content": "TODO list approved by Auditor ✅."}
                yield {"type": "todo", "content": todo_list}
                return todo_list
            elif decision == "REVISE":
                if round_idx < max_rounds - 1:
                    yield {"type": "status", "content": "Planner: Revising TODO based on feedback ⏳..."}
                    audit_feedback_str = json.dumps(issues, indent=2, ensure_ascii=False)
                    todo_list = self.planner.revise_todo(instruction, todo_list, audit_feedback_str)
                    yield {"type": "todo_draft", "content": todo_list}
                else:
                    yield {"type": "error", "content": "Max revision rounds reached. Auditor still failing ❌."}
                    return None
            else:
                yield {"type": "error", "content": "Auditor returned FAIL. Terminating generation ❌."}
                return None
            
        return None

    def verify_generated_code(self, instruction: str, todo_list: str, generated_code: str) -> str:
        return self.auditor.verify_code(instruction, todo_list, generated_code)
