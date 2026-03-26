import os
import sys
import json
import glob
import argparse
from core.agent import RodiAgent

EVAL_PROMPT = """You are an expert code evaluator.
You will be given a 'Ground Truth Code' and a 'Generated Code'.
Their formatting, variables naming or spacing might differ, but if their logical outcome, APIs used and respective parameters mean exactly the same thing, you should consider them correct.
CRITICAL RULE FOR VARIABLE VALUES:
The Generated Code must declare the necessary variables and pass the required parameters as dictated by the Ground Truth Code. However, you MUST IGNORE ANY DIFFERENCES IN THE ACTUAL DATA VALUES assigned to these necessary variables or parameters (e.g., different array numbers for joint angles, different coordinates, etc.). As long as the logical structure, API usage, and the presence of the required parameters match the Ground Truth, treat them as logically equivalent even if the specific values differ.

You MUST ALWAYS use the provided tools (like `get_list` and `get_information`) to look up and verify the exact specifications and required parameters of ANY API present in the code snippets BEFORE making your evaluation. 

Ground Truth Code:
{gt_code}

Generated Code:
{gen_code}

Evaluate the Generated Code against the Ground Truth Code. 
If they are logically equivalent and achieve the exact same behavior based on the criteria above, output a final answer (Agent Output:) with EXACTLY the word "CORRECT".
If they are completely different or the generated code has errors/missing logic, output a final answer (Agent Output:) with the word "INCORRECT" followed by a newline, and then provide a brief 1-2 sentence explanation starting with "REASON: ".
Do not output any other explanation for CORRECT answers.
"""

def evaluate_path(result_base_dir: str, test_file_path: str = "data/test.json", config_path: str = "configs/openai_config.json"):
    if not os.path.exists(result_base_dir):
        print(f"Error: Result directory not found at {result_base_dir}")
        return

    # Load Ground Truth
    if not os.path.exists(test_file_path):
        print(f"Error: Test file not found at {test_file_path}")
        return
        
    with open(test_file_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    # Initialize the Agent
    # We set a distinct result directory so evaluation logs don't mix with generation logs if possible,
    # but the agent will just create another json in result/ as configured.
    eval_agent = RodiAgent(config_path=config_path)
    
    # Monkey-patch _save_result to prevent the agent from writing its own result folders during evaluation.
    # We only want the final summary JSON.
    eval_agent._save_result = lambda *args, **kwargs: None
    
    total_problems = len(test_data)
    correct_count = 0
    evaluated_count = 0
    results_list = []

    print(f"--- Starting Evaluation for Path: {result_base_dir} ---")
    
    for idx, item in enumerate(test_data):
        prob_idx = idx + 1
        gt_code = item.get("output", "").strip()
        
        # Find the output text file for this problem
        prob_dir = os.path.join(result_base_dir, f"problem_{prob_idx}")
        if not os.path.exists(prob_dir):
            print(f"[Problem {prob_idx}] SKIP (Directory not found)")
            continue
            
        txt_files = glob.glob(os.path.join(prob_dir, "*_output.txt"))
        if not txt_files:
            print(f"[Problem {prob_idx}] SKIP (No output.txt found)")
            continue
            
        # Assuming one output per problem, grab the latest/first
        txt_file = sorted(txt_files)[-1]
        
        with open(txt_file, 'r', encoding='utf-8') as f:
            gen_code = f.read().strip()
            
        # Prepare Agent prompt
        eval_instruction = EVAL_PROMPT.format(gt_code=gt_code, gen_code=gen_code)
        
        try:
            # Let the agent run its tool loop to analyze the code
            # Note: We pass problem_idx here simply so its own logs differentiate
            response_full = eval_agent.run(eval_instruction, problem_idx=f"eval_{prob_idx}")
            
            # The agent returns the final output content
            if response_full is None:
                print(f"[Problem {prob_idx}] ERROR: Agent failed to produce a final output.")
                continue
                
            response = response_full.strip()
            
            evaluated_count += 1
            status = "ERROR"
            reason = ""

            if response.upper().startswith("CORRECT"):
                correct_count += 1
                status = "CORRECT"
                print(f"[Problem {prob_idx}] CORRECT")
            else:
                status = "INCORRECT"
                print(f"[Problem {prob_idx}] INCORRECT")
                # Try to extract the reason
                reason = response.split("REASON:", 1)[-1].strip() if "REASON:" in response.upper() else response.strip()
                print(f"  Reason: {reason}")
            
            results_list.append({
                "problem": prob_idx,
                "status": status,
                "reason": reason
            })
                
        except Exception as e:
            print(f"[Problem {prob_idx}] ERROR during Agent eval: {e}")
            results_list.append({
                "problem": prob_idx,
                "status": "ERROR",
                "reason": str(e)
            })

    # Results
    if total_problems > 0:
        accuracy = (correct_count / total_problems) * 100
        print("\n--- Final Evaluation Results ---")
        print(f"Total Test Cases: {total_problems}")
        print(f"Evaluated: {evaluated_count}")
        print(f"Correct: {correct_count}")
        print(f"Accuracy: {accuracy:.2f}%")
        
        # Save evaluation summary to a single JSON
        summary_path = os.path.join(result_base_dir, "evaluation_summary.json")
        summary_data = {
            "total_problems": total_problems,
            "evaluated": evaluated_count,
            "correct": correct_count,
            "accuracy_percentage": accuracy,
            "details": results_list
        }
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=4, ensure_ascii=False)
        print(f"\nEvaluation summary saved to: {summary_path}")
    else:
        print("No test data found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate generated code.")
    parser.add_argument("result_directory_path", help="Path to the result directory (e.g., result/MiniMaxAI)")
    parser.add_argument("--config", default="configs/openai_config.json", help="Path to the LLM config file to use for evaluation")
    
    args = parser.parse_args()
    evaluate_path(args.result_directory_path, config_path=args.config)
