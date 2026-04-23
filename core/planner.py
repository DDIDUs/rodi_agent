from .prompts import FEATURE_CHECKLIST_GENERATION_PROMPT, PLANNER_REVISION_PROMPT
from .llm_client import OpenAILLMClient

class PlannerAgent:
    def __init__(self, llm_client: OpenAILLMClient):
        self.llm = llm_client

    def generate_initial_checklist(self, instruction: str) -> str:
        history = [
            {"role": "system", "content": FEATURE_CHECKLIST_GENERATION_PROMPT},
            {"role": "user", "content": instruction}
        ]
        try:
            checklist = self.llm.generate(history)
            return checklist
        except Exception as e:
            print(f"Planner Error: {e}")
            return "Could not generate feature checklist."

    def revise_checklist(self, instruction: str, previous_checklist: str, audit_feedback: str) -> str:
        prompt = (
            f"User Instruction:\n{instruction}\n\n"
            f"Previous Feature Checklist:\n{previous_checklist}\n\n"
            f"Auditor Issues:\n{audit_feedback}\n\n"
            "Please provide a revised feature checklist addressing these issues."
        )
        history = [
            {"role": "system", "content": PLANNER_REVISION_PROMPT},
            {"role": "user", "content": prompt}
        ]
        try:
            revised_checklist = self.llm.generate(history)
            return revised_checklist
        except Exception as e:
            print(f"Planner Error (Revision): {e}")
            return previous_checklist
