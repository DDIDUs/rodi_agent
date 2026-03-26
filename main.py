import os
import sys
import json
from core.agent import RodiAgent

if __name__ == "__main__":
    agent = RodiAgent()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_file = sys.argv[2] if len(sys.argv) > 2 else "data/test.json"
        print(f">>> Rodi Agent Batch Mode ({test_file}) <<<")
        if not os.path.exists(test_file):
            print(f"Error: {test_file} not found.")
            sys.exit(1)
            
        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
            
        for idx, item in enumerate(test_data):
            instruction = item.get("instruction")
            if instruction:
                print(f"\n--- [Batch {idx+1}/{len(test_data)}] ---")
                print(f"Instruction: {instruction}")
                agent.run(instruction, problem_idx=str(idx+1))
    else:
        print(">>> Rodi Agent Interactive Mode <<<")
        print("To run batch inference from test file, use: python main.py --test [filepath]")
        
        while True:
            try:
                instruction = input("\nEnter instruction (or 'exit'): ")
                if instruction.lower() in ['exit', 'quit']:
                    break
                if not instruction.strip():
                    continue
                
                agent.run(instruction)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
