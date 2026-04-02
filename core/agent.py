import re
import os
import json
import time
import sys
from datetime import datetime
from .tools import RodiTools
from .llm_client import OpenAILLMClient
from .prompts import SYSTEM_PROMPT, TODO_GENERATION_PROMPT, TODO_CHECK_PROMPT
from .orchestrator import Orchestrator

class RodiAgent:
    def __init__(self, config_path: str = "configs/llm_config.json"):
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path)
        self.llm = OpenAILLMClient(config_path=config_path)
        self.orchestrator = Orchestrator(self.llm)
        
        self.tools = RodiTools()
        self.history = [] # Linear history of the current session
        self.result_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'result')
        
        # Ensure result directory exists
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

    def _parse_response(self, response: str):
        """
        Parses LLM response to extract Command or Final Output.
        Returns: (type, content)
            type: 'command', 'output', or 'thought' (if no command/output found)
        """
        # Check for Final Output first
        if "Agent Output:" in response:
            parts = response.split("Agent Output:")
            thought_part = parts[0].strip()
            code_part = parts[1].strip()
            return 'output', code_part, thought_part

        # Check for Command
        match = re.search(r'Command:\s*\$\s*(\w+)\s+(.*)', response, re.IGNORECASE)
        if match:
            tool_name = match.group(1)
            tool_args = match.group(2).strip()
            return 'command', (tool_name, tool_args), response

        return 'thought', response, response

    def _save_result(self, instruction: str, output: str, full_history: list, problem_idx: str = None, todo_list: str = None, verification: str = None):
        """Saves interaction result to JSON and output code to TXT."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine model name for folder differentiation
        model_name = getattr(self.llm, 'model', 'unknown_model').replace('/', '_')
        
        # Append problem-specific subfolder if provided
        if problem_idx is not None:
            model_result_dir = os.path.join(self.result_dir, model_name, f"problem_{problem_idx}")
        else:
            model_result_dir = os.path.join(self.result_dir, model_name)
            
        if not os.path.exists(model_result_dir):
            os.makedirs(model_result_dir)
            
        filename = f"{timestamp}.json"
        filepath = os.path.join(model_result_dir, filename)
        
        data = {
            "timestamp": timestamp,
            "model": getattr(self.llm, 'model', 'unknown_model'),
            "instruction": instruction,
            "todo_list": todo_list,
            "output": output,
            "verification": verification,
            "history": full_history
        }
        
        try:
            # Save JSON log
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n[Result Saved]: {filepath}")
            
            # Save output code separately
            txt_filename = f"{timestamp}_output.txt"
            txt_filepath = os.path.join(model_result_dir, txt_filename)
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"[Output Code Saved]: {txt_filepath}")
            
        except Exception as e:
            print(f"[Error Saving Result]: {e}")

    def run(self, user_instruction: str, problem_idx: str = None):
        todo_list = self.orchestrator.generate_approved_todo(user_instruction)
        
        if not todo_list:
            print("Failed to generate an approved TODO list. Aborting.")
            return None

        # Initialize conversation for this run
        enhanced_instruction = f"User Instruction:\n{user_instruction}\n\nPlanned TODO List:\n{todo_list}\n\nPlease execute these steps."
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": enhanced_instruction}
        ]
        
        max_steps = 20
        step = 0
        final_output = None
        
        while step < max_steps:
            # Generate LLM response
            try:
                response_text = self.llm.generate(self.history, stop_sequences=["Observation:"])
            except Exception as e:
                print(f"Agent Error (LLM): {e}")
                return None

            print(f"{response_text}\n")
            
            # Parse
            msg_type, content, full_text = self._parse_response(response_text)
            
            # Append Agent's response to history
            self.history.append({"role": "assistant", "content": response_text})
            
            if msg_type == 'output':
                code_part, thought_part = content, full_text
                
                # Success
                final_output = code_part
                
                print("\n--- [Verification: Checking Output via Auditor] ---")
                verification_result = self.orchestrator.verify_generated_code(user_instruction, todo_list, final_output)
                print(f"{verification_result}\n")
                
                if "[VERIFICATION FAILURE]" in verification_result:
                    observation = f"Code Verification Failed:\n{verification_result}\n\nPlease revise your code."
                    print(f"Observation: {observation}")
                    self.history.append({"role": "user", "content": f"Observation:\n{observation}"})
                    step += 1
                    continue
                    
                self._save_result(user_instruction, final_output, self.history, problem_idx, todo_list, verification_result)
                return final_output
            
            elif msg_type == 'command':
                tool_name, tool_args = content
                
                # Execute Tool
                observation = ""
                if tool_name == "get_list":
                    observation = self.tools.get_list(tool_args)
                elif tool_name == "get_information":
                    result = self.tools.get_information(tool_args)
                    observation = json.dumps(result, ensure_ascii=False)
                elif tool_name == "search_rag":
                    result = self.tools.search_rag(tool_args)
                    observation = json.dumps(result, ensure_ascii=False)
                else:
                    observation = f"Error: Unknown tool '{tool_name}'"
                
                print(f"Observation: {observation[:2000]}..." if len(observation) > 2000 else f"Observation: {observation}")
                print("-" * 20)
                
                self.history.append({"role": "user", "content": f"Observation:\n{observation}"})
                
            else:
                 print("Warning: No command or output detected. Continuing...")
            
            step += 1
            
        print("Max steps reached.")
        return None

    def run_stream(self, user_instruction: str, problem_idx: str = None):
        """
        Generator version of run() designed to be consumed by UIs (like Streamlit).
        Yields dictionaries containing state updates.
        """
        todo_list = None
        for item in self.orchestrator.generate_approved_todo_stream(user_instruction):
            yield item
            if item["type"] == "todo":
                todo_list = item["content"]
            elif item["type"] == "error":
                return
        
        if not todo_list:
            yield {"type": "error", "content": "Failed to generate an approved TODO list. Aborting."}
            return

        # Initialize conversation for this run
        enhanced_instruction = f"User Instruction:\n{user_instruction}\n\nPlanned TODO List:\n{todo_list}\n\nPlease execute these steps."
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": enhanced_instruction}
        ]
        
        max_steps = 20
        step = 0
        final_output = None
        
        while step < max_steps:
            yield {"type": "status", "content": f"Thinking (Step {step + 1}/{max_steps})..."}
            
            # Generate LLM response
            try:
                response_text = self.llm.generate(self.history, stop_sequences=["Observation:"])
            except Exception as e:
                yield {"type": "error", "content": f"Agent Error (LLM): {e}"}
                return

            # Parse
            msg_type, content, full_text = self._parse_response(response_text)
            
            # Append Agent's response to history
            self.history.append({"role": "assistant", "content": response_text})
            
            if msg_type == 'output':
                code_part, thought_part = content, full_text
                yield {"type": "thought", "content": thought_part}
                
                # Success
                final_output = code_part
                
                yield {"type": "status", "content": "Verifying Output via Auditor..."}
                verification_result = self.orchestrator.verify_generated_code(user_instruction, todo_list, final_output)
                yield {"type": "observation", "content": f"Verification: {verification_result}"}
                
                if "[VERIFICATION FAILURE]" in verification_result:
                    observation = f"Code Verification Failed:\n{verification_result}\n\nPlease revise your code."
                    yield {"type": "observation", "content": observation}
                    self.history.append({"role": "user", "content": f"Observation:\n{observation}"})
                    step += 1
                    continue
                
                self._save_result(user_instruction, final_output, self.history, problem_idx, todo_list, verification_result)
                yield {"type": "finish", "content": final_output}
                return
            
            elif msg_type == 'command':
                tool_name, tool_args = content
                
                # We can yield the thought part before the command if we want, but parsing extracts them together often.
                # In Rodi, the thought is usually prepended in the text. Let's just yield the whole response as thought.
                yield {"type": "thought", "content": response_text}
                
                # Execute Tool
                observation = ""
                if tool_name == "get_list":
                    observation = self.tools.get_list(tool_args)
                elif tool_name == "get_information":
                    result = self.tools.get_information(tool_args)
                    observation = json.dumps(result, ensure_ascii=False)
                elif tool_name == "search_rag":
                    result = self.tools.search_rag(tool_args)
                    observation = json.dumps(result, ensure_ascii=False)
                else:
                    observation = f"Error: Unknown tool '{tool_name}'"
                
                yield {"type": "observation", "content": observation}
                self.history.append({"role": "user", "content": f"Observation:\n{observation}"})
                
            else:
                 yield {"type": "thought", "content": response_text}
            
            step += 1
            
        yield {"type": "error", "content": "Max steps reached without finalizing output."}



