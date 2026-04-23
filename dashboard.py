import streamlit as st
import os
import json
import pandas as pd
from pathlib import Path
from glob import glob
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Rodi Agent Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
)

# Constants
RESULT_DIR = Path("result")

def get_available_models():
    """Scan the result directory to get available evaluated models."""
    if not RESULT_DIR.exists():
        return []
    models = []
    for model_dir in RESULT_DIR.iterdir():
        if model_dir.is_dir() and (model_dir / "evaluation_summary.json").exists():
            models.append(model_dir.name)
    return sorted(models)

def load_evaluation_summary(model_name):
    """Load the evaluation summary JSON for a specific model."""
    summary_path = RESULT_DIR / model_name / "evaluation_summary.json"
    if summary_path.exists():
        with open(summary_path, "r") as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                st.error(f"Failed to parse {summary_path}")
    return None

def load_problem_detail(model_name, problem_id):
    """Load latest attempt details for a specific problem."""
    problem_dir = RESULT_DIR / model_name / f"problem_{problem_id}"
    if not problem_dir.exists():
        return None
    
    # Find all json files in the problem directory
    json_files = list(problem_dir.glob("*.json"))
    if not json_files:
        return None
        
    # Sort files by name (which includes timestamp like 20260311_193004.json)
    # to get the latest attempt
    latest_file = sorted(json_files)[-1]
    
    with open(latest_file, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None

def render_results_viewer():
    st.header("📊 Results Viewer")
    
    # Sidebar
    st.sidebar.divider()
    st.sidebar.header("Viewer Options")
    models = get_available_models()
    
    if not models:
        st.warning(f"No evaluation results found in `{RESULT_DIR.absolute()}`.")
        st.sidebar.info("Run experiments to see data here.")
        return
        
    selected_model = st.sidebar.selectbox("Select Model", models)
    
    if selected_model:
        # Load summary data
        summary_data = load_evaluation_summary(selected_model)
        
        if not summary_data:
            st.error("No valid evaluation_summary.json found for this model.")
            return
            
        # Display Overview Metrics
        st.header("Overview Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        total = summary_data.get("total_problems", 0)
        evaluated = summary_data.get("evaluated", 0)
        correct = summary_data.get("correct", 0)
        accuracy = summary_data.get("accuracy_percentage", 0.0)
        
        col1.metric("Total Problems", total)
        col2.metric("Evaluated", evaluated)
        col3.metric("Correct", correct)
        col4.metric("Accuracy", f"{accuracy:.2f}%")
        
        # Details Table
        st.header("Evaluation Details")
        
        details = summary_data.get("details", [])
        if details:
            # Convert to DataFrame for better display
            df = pd.DataFrame(details)
            
            # Styling: Add color to status
            def color_status(val):
                color = 'green' if val == 'CORRECT' else 'red'
                return f'color: {color}'
                
            styled_df = df.style.map(color_status, subset=['status'])
            
            # Show dataframe
            st.dataframe(
                styled_df,
                use_container_width=True,
                column_config={
                    "problem": st.column_config.NumberColumn("Problem ID", format="%d"),
                    "status": "Status",
                    "reason": "Reason for Failure"
                },
                hide_index=True,
            )
            
            # Problem Drill Down
            st.header("Inspect Specific Problem")
            
            # Get list of problems and create formatted options for selectbox
            problem_ids = [d["problem"] for d in details]
            problem_options = {d["problem"]: f"Problem {d['problem']} - {d['status']}" for d in details}
            
            selected_problem = st.selectbox(
                "Select a problem to view internal agent traces:",
                options=problem_ids,
                format_func=lambda x: problem_options[x]
            )
            
            if selected_problem:
                problem_detail = load_problem_detail(selected_model, selected_problem)
                if problem_detail:
                    st.subheader(f"Internal Trace (Problem {selected_problem})")
                    
                    # Display metadata manually for better formatting
                    st.markdown("**Model:** " + str(problem_detail.get('model', 'N/A')))
                    st.markdown("**Instruction:**\n" + str(problem_detail.get('instruction', 'N/A')))
                    feature_checklist = problem_detail.get('feature_checklist', '')
                    if feature_checklist:
                        st.markdown("**Feature Checklist:**")
                        st.markdown(feature_checklist)
                    
                    st.divider()
                    
                    # Output logic
                    output = problem_detail.get('output', '')
                    if output:
                        st.markdown("**Generated Code Output:**")
                        st.code(output, language='javascript')
                        
                    # History Chat Exchanger
                    history = problem_detail.get('history', [])
                    if history:
                        with st.expander("Show Internal Chat History", expanded=False):
                            for msg in history:
                                role = msg.get('role', '')
                                content = msg.get('content', '')
                                
                                # Choose icon based on role
                                if role == 'user':
                                    icon = "👤"
                                    name = "Environment/User"
                                elif role == 'assistant':
                                    icon = "🤖"
                                    name = "Agent Tools"
                                else:
                                    icon = "⚙️"
                                    name = "System"
                                    
                                with st.chat_message(role, avatar=icon):
                                    st.markdown(f"**{name}**")
                                    # If content looks like code/JSON or has multiple newlines, format properly
                                    if "Observation:" in content or "Thought:" in content:
                                        # Split thought and command for readability if possible
                                        parts = content.split("Command:")
                                        if len(parts) == 2:
                                            st.markdown(parts[0].strip())
                                            st.code("Command:" + parts[1], language="bash")
                                        else:
                                            st.markdown(content)
                                    else:
                                        st.markdown(content)
                else:
                    st.info(f"No detailed trace files found for Problem {selected_problem}.")

def render_interactive_generation():
    st.header("Interactive Code Generation")
    st.markdown("Enter an instruction below to watch the Rodi Agent execute tools and generate code in real-time.")
    
    # Text area for user instruction
    user_instruction = st.text_area(
        "Observation Instruction", 
        height=150, 
        placeholder="e.g. Move linearly to the designated position."
    )
    
    if st.button("Generate Code", type="primary"):
        if not user_instruction.strip():
            st.warning("Please enter an instruction.")
            return

        # Import RodiAgent here to avoid circular dependencies if any, and initialize
        from core.agent import RodiAgent
        
        # UI Elements for streaming
        status_placeholder = st.empty()
        checklist_placeholder = st.empty()
        
        st.subheader("Agent Execution Trace")
        trace_container = st.container()
        
        st.subheader("Final Output")
        output_placeholder = st.empty()
        
        st.divider()
        
        # Initialize Agent
        try:
            agent = RodiAgent()
        except Exception as e:
            st.error(f"Failed to initialize Agent: {e}")
            return
            
        with st.spinner("Agent is running..."):
            try:
                # Consume stream
                for update in agent.run_stream(user_instruction):
                    update_type = update.get("type")
                    content = update.get("content", "")
                    
                    if update_type == "status":
                        status_placeholder.info(f"🔄 Status: {content}")
                    
                    elif update_type in {"checklist_draft", "checklist"}:
                        with checklist_placeholder.expander("📝 Generated Feature Checklist", expanded=True):
                            st.markdown(content)
                            
                    elif update_type == "thought":
                        with trace_container.chat_message("assistant", avatar="🤖"):
                            st.markdown("**Agent Thought/Command:**")
                            if "Command:" in content:
                                parts = content.split("Command:")
                                st.markdown(parts[0].strip())
                                st.code("Command:" + parts[1], language="bash")
                            else:
                                st.markdown(content)
                                
                    elif update_type == "observation":
                        with trace_container.chat_message("user", avatar="👤"):
                            st.markdown("**Observation (Tool Result):**")
                            # Truncate if too long to prevent UI freezing
                            display_content = content[:2000] + "\n...[truncated]" if len(content) > 2000 else content
                            st.markdown(f"```text\n{display_content}\n```")
                            
                    elif update_type == "error":
                        status_placeholder.error(f"❌ Error: {content}")
                        break
                        
                    elif update_type == "finish":
                        status_placeholder.success("✅ Generation Complete!")
                        output_placeholder.code(content, language="javascript")
                        st.toast("Result saved to result/ directory.")
                        break
            except Exception as e:
                st.error(f"Error during streaming execution: {e}")

def main():
    st.title("🤖 Rodi Agent Dashboard")
    st.markdown("Visualize the performance of different models on Rodi Agent tasks, and interactively generate code.")
    
    # Navigation Sidebar
    st.sidebar.header("Navigation")
    app_mode = st.sidebar.radio("Select Mode", ["📊 Results Viewer", "⚡ Interactive Generation"])
    
    if app_mode == "📊 Results Viewer":
        render_results_viewer()
    elif app_mode == "⚡ Interactive Generation":
        render_interactive_generation()

if __name__ == "__main__":
    main()
