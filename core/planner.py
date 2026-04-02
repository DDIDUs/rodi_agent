import json
from base64 import b64encode
from .prompts import TODO_GENERATION_PROMPT, PLANNER_REVISION_PROMPT
from .llm_client import OpenAILLMClient

class PlannerAgent:
    def __init__(self, llm_client: OpenAILLMClient):
        self.llm = llm_client

    def generate_initial_todo(self, instruction: str) -> str:
        history = [
            {"role": "system", "content": TODO_GENERATION_PROMPT},
            {"role": "user", "content": instruction}
        ]
        try:
            todo_list = self.llm.generate(history)
            return todo_list
        except Exception as e:
            print(f"Planner Error: {e}")
            return "Could not generate TODO list."

    def revise_todo(self, instruction: str, previous_todo: str, audit_feedback: str) -> str:
        prompt = (
            f"User Instruction:\n{instruction}\n\n"
            f"Previous TODO List:\n{previous_todo}\n\n"
            f"Auditor Issues:\n{audit_feedback}\n\n"
            "Please provide a revised TODO list addressing these issues."
        )
        history = [
            {"role": "system", "content": PLANNER_REVISION_PROMPT},
            {"role": "user", "content": prompt}
        ]
        try:
            revised_todo = self.llm.generate(history)
            return revised_todo
        except Exception as e:
            print(f"Planner Error (Revision): {e}")
            return previous_todo
