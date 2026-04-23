import re
import os
import json
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List, Generator

from .tools import RodiTools
from .llm_client import OpenAILLMClient
from .prompts import SYSTEM_PROMPT
from .orchestrator import Orchestrator

class AgentResponse:
    def __init__(self, msg_type: str, content: Any, full_text: str):
        self.msg_type = msg_type
        self.content = content
        self.full_text = full_text

class RodiAgent:
    def __init__(self, config_path: str = "configs/llm_config.json"):
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path)
        self.llm = OpenAILLMClient(config_path=config_path)
        self.orchestrator = Orchestrator(self.llm)
        self.tools = RodiTools()
        self.history: List[Dict[str, str]] = []
        self.result_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'result')
        
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

    def _parse_response(self, response: str) -> AgentResponse:
        """Parses LLM response to extract Command or Final Output."""
        if "Agent Output:" in response:
            parts = response.split("Agent Output:")
            return AgentResponse('output', parts[1].strip(), parts[0].strip())

        match = re.search(r'Command:\s*\$\s*(\w+)\s+(.*)', response, re.IGNORECASE)
        if match:
            return AgentResponse('command', (match.group(1), match.group(2).strip()), response)

        return AgentResponse('thought', response, response)

    def _execute_tool(self, tool_name: str, tool_args: str) -> str:
        """Dispatches tool calls to the RodiTools instance."""
        try:
            if tool_name == "get_list":
                return self.tools.get_list(tool_args)
            elif tool_name == "get_information":
                result = self.tools.get_information(tool_args)
                return json.dumps(result, ensure_ascii=False)
            elif tool_name == "search_rag":
                result = self.tools.search_rag(tool_args)
                return json.dumps(result, ensure_ascii=False)
            else:
                return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _save_result(self, instruction: str, output: str, full_history: list,
                     problem_idx: Optional[str] = None, feature_checklist: Optional[str] = None,
                     verification: Optional[str] = None):
        """Saves interaction result to JSON and output code to TXT."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = getattr(self.llm, 'model', 'unknown_model').replace('/', '_')
        
        model_result_dir = os.path.join(self.result_dir, model_name)
        if problem_idx:
            model_result_dir = os.path.join(model_result_dir, f"problem_{problem_idx}")
            
        os.makedirs(model_result_dir, exist_ok=True)
            
        filepath = os.path.join(model_result_dir, f"{timestamp}.json")
        txt_filepath = os.path.join(model_result_dir, f"{timestamp}_output.txt")
        
        data = {
            "timestamp": timestamp,
            "model": getattr(self.llm, 'model', 'unknown_model'),
            "instruction": instruction,
            "feature_checklist": feature_checklist,
            "output": output,
            "verification": verification,
            "history": full_history
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n[Result Saved]: {filepath}")
        except Exception as e:
            print(f"[Error Saving Result]: {e}")

    def run(self, user_instruction: str, problem_idx: str = None) -> Optional[str]:
        """Synchronous execution loop."""
        feature_checklist = self.orchestrator.generate_approved_checklist(user_instruction)
        if not feature_checklist:
            print("Failed to generate an approved feature checklist. Aborting.")
            return None

        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User Instruction:\n{user_instruction}\n\n"
                    f"Feature Checklist:\n{feature_checklist}\n\n"
                    "Use this checklist to decide what functionality must be verified through RAG search before generating the final code."
                )
            }
        ]
        
        max_steps = 20
        for step in range(max_steps):
            try:
                response_text = self.llm.generate(self.history, stop_sequences=["Observation:"])
            except Exception as e:
                print(f"Agent Error (LLM): {e}")
                return None

            print(f"{response_text}\n")
            resp = self._parse_response(response_text)
            self.history.append({"role": "assistant", "content": response_text})
            
            if resp.msg_type == 'output':
                final_output = resp.content
                self._save_result(user_instruction, final_output, self.history, problem_idx, feature_checklist, None)
                return final_output
            
            elif resp.msg_type == 'command':
                tool_name, tool_args = resp.content
                observation = self._execute_tool(tool_name, tool_args)
                print(f"Observation: {observation[:2000]}..." if len(observation) > 2000 else f"Observation: {observation}")
                print("-" * 20)
                self.history.append({"role": "user", "content": f"Observation:\n{observation}"})
            else:
                 print("Warning: No command or output detected.")
            
        print("Max steps reached.")
        return None

    def run_stream(self, user_instruction: str, problem_idx: str = None) -> Generator[Dict[str, str], None, None]:
        """Streaming execution loop for UIs."""
        feature_checklist = None
        for item in self.orchestrator.generate_approved_checklist_stream(user_instruction):
            yield item
            if item["type"] == "checklist":
                feature_checklist = item["content"]
            elif item["type"] == "error":
                return
        
        if not feature_checklist:
            yield {"type": "error", "content": "Failed to generate an approved feature checklist. Aborting."}
            return

        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User Instruction:\n{user_instruction}\n\n"
                    f"Feature Checklist:\n{feature_checklist}\n\n"
                    "Use this checklist to decide what functionality must be verified through RAG search before generating the final code."
                )
            }
        ]
        
        max_steps = 20
        for step in range(max_steps):
            yield {"type": "status", "content": f"Thinking (Step {step + 1}/{max_steps})..."}
            try:
                response_text = self.llm.generate(self.history, stop_sequences=["Observation:"])
            except Exception as e:
                yield {"type": "error", "content": f"Agent Error (LLM): {e}"}
                return

            resp = self._parse_response(response_text)
            self.history.append({"role": "assistant", "content": response_text})
            
            if resp.msg_type == 'output':
                yield {"type": "thought", "content": resp.full_text}
                final_output = resp.content
                self._save_result(user_instruction, final_output, self.history, problem_idx, feature_checklist, None)
                yield {"type": "finish", "content": final_output}
                return
            
            elif resp.msg_type == 'command':
                yield {"type": "thought", "content": response_text}
                tool_name, tool_args = resp.content
                observation = self._execute_tool(tool_name, tool_args)
                yield {"type": "observation", "content": observation}
                self.history.append({"role": "user", "content": f"Observation:\n{observation}"})
            else:
                 yield {"type": "thought", "content": response_text}
            
        yield {"type": "error", "content": "Max steps reached without finalizing output."}
