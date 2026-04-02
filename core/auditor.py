import json
import re
from .prompts import AUDITOR_PROMPT, TODO_CHECK_PROMPT
from .llm_client import OpenAILLMClient

class AuditorAgent:
    def __init__(self, llm_client: OpenAILLMClient):
        self.llm = llm_client

    def verify_code(self, instruction: str, todo_list: str, generated_code: str) -> str:
        verify_prompt = (
            f"User Instruction:\n{instruction}\n\n"
            f"Planned TODO List:\n{todo_list}\n\n"
            f"Generated Code:\n{generated_code}"
        )
        history = [
            {"role": "system", "content": TODO_CHECK_PROMPT},
            {"role": "user", "content": verify_prompt}
        ]
        try:
            return self.llm.generate(history)
        except Exception as e:
            print(f"Auditor Error (Verify LLM): {e}")
            return "Could not verify the output."

    def _extract_json(self, text: str) -> str:
        # Try to find a JSON block in the text
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Or just match the first { and last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0).strip()
        
        return text.strip()

    def evaluate_todo(self, instruction: str, todo_list: str) -> dict:
        prompt = f"User Instruction:\n{instruction}\n\nProposed TODO List:\n{todo_list}\n\nPlease evaluate and output the JSON."
        history = [
            {"role": "system", "content": AUDITOR_PROMPT},
            {"role": "user", "content": prompt}
        ]
        try:
            response_text = self.llm.generate(history)
            json_str = self._extract_json(response_text)
            
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                print("Auditor output was not valid JSON. Defaulting to REVISE.")
                result = {
                    "decision": "REVISE",
                    "issues": [
                        {
                            "type": "other",
                            "severity": "high",
                            "message": "Auditor failed to output valid JSON. Output was: " + response_text,
                            "suggested_fix": "Please check your output format."
                        }
                    ],
                    "summary": "Invalid JSON from Auditor"
                }

            # Ensure required keys exist
            if "decision" not in result:
                result["decision"] = "FAIL"
            if "issues" not in result:
                result["issues"] = []
            if "summary" not in result:
                result["summary"] = ""
                
            return result
        except Exception as e:
            print(f"Auditor Error: {e}")
            return {
                "decision": "FAIL",
                "issues": [{"type": "other", "severity": "high", "message": f"Exception occurred: {e}", "suggested_fix": ""}],
                "summary": "Auditor encountered an exception."
            }
