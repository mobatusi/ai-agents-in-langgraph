
import streamlit as st
from helper import ewriter
import os

# Initialize the writer agent
if 'agent' not in st.session_state:
    st.session_state.agent = ewriter()

if 'thread_id' not in st.session_state:
    st.session_state.thread_id = 0
    st.session_state.threads = [0]
    st.session_state.max_revisions = 2

# Global Step Mapping
step_mapping = {
    'planner': 'Plan',
    'generate': 'Draft',
    'reflect': 'Critique',
    'research_plan': 'Research Plan',
    'research_critique': 'Research Critique',
    '__start__': 'Start',
    'end': 'End'
}
    
# Helper function to get current configuration
def get_thread():
    return {"configurable": {"thread_id": str(st.session_state.thread_id)}}

st.set_page_config(layout="wide")
st.title("Essay Writer Agent")

# Sidebar controls
with st.sidebar:
    st.header("Controls")
    with st.expander("Usage Instructions"):
        st.markdown("""
        **How to use the Essay Writer Agent:**
        
        1. **Start New:** Enter a topic in "Essay Topic" and click **Generate Essay**.
        2. **Monitor:** Watch the **Agent Stream** tab for live progress.
        3. **Human-in-the-loop:** The agent pauses at key steps (Plan, Draft, Critique).
           - Switch to the respective tabs (Plan, Draft, Critique) to review.
           - Edit the content if desired and click **Update**.
        4. **Resume:** Click **Continue** to let the agent proceed with your changes.
        5. **Time Travel:** Use the dropdown to select a previous step and restore it to branch off from that point.
        """)
    topic = st.text_input("Essay Topic", value="Pizza Shop")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Essay"):
            # Initialize new thread for new generation
            st.session_state.thread_id += 1
            st.session_state.threads.append(st.session_state.thread_id)
            
            initial_state = {
                'task': topic,
                "max_revisions": st.session_state.max_revisions,
                "revision_number": 0,
                'lnode': "", 
                'planner': "no plan", 
                'draft': "no draft", 
                'critique': "no critique", 
                'content': [], 
                'queries': [], 
                'count': 0
            }
            
            thread = get_thread()
            st.session_state.stream = st.session_state.agent.graph.stream(initial_state, thread)
            st.session_state.is_running = True

    with col2:
        # Determine next step for button label
        next_step = "Continue"
        try:
            thread = get_thread()
            state = st.session_state.agent.graph.get_state(thread)
            if state.next:
                next_node = state.next[0]
                next_step_name = step_mapping.get(next_node, next_node)
                next_step = f"Continue to {next_step_name}"
        except:
             pass

        if st.button(next_step):
            thread = get_thread()
            st.session_state.stream = st.session_state.agent.graph.stream(None, thread)
            st.session_state.is_running = True

    st.markdown("---")
    
    # Thread Switching
    thread_options = {}
    for t_id in st.session_state.threads:
        t_config = {"configurable": {"thread_id": str(t_id)}}
        try:
            t_state = st.session_state.agent.graph.get_state(t_config)
            if t_state.values:
                t_lnode = t_state.values.get("lnode", "Unknown")
                t_status = step_mapping.get(t_lnode, t_lnode.replace("_", " ").title())
                thread_options[f"Thread {t_id} ({t_status})"] = t_id
            else:
                thread_options[f"Thread {t_id} (New)"] = t_id
        except:
             thread_options[f"Thread {t_id}"] = t_id

    selected_thread_label = st.selectbox(
        "Select Thread", 
        list(thread_options.keys()), 
        index=st.session_state.threads.index(st.session_state.thread_id)
    )
    selected_thread = thread_options[selected_thread_label]
    
    if selected_thread != st.session_state.thread_id:
        st.session_state.thread_id = selected_thread
        st.experimental_rerun()



    # Time Travel / State History
    thread = get_thread()
    history = []
    # step_mapping is defined globally now

    try:
        for state in st.session_state.agent.graph.get_state_history(thread):
             if state.metadata.get('step', 0) < 1:
                 continue
             ts = state.config['configurable']['thread_ts']
             lnode = state.values.get('lnode', 'unknown')
             step_name = step_mapping.get(lnode, lnode)
             revision = state.values.get('revision_number', 0)
             history.append(f"{step_name} (Rev {revision}) - {ts}")
    except Exception:
        pass
        
    if history:
        selected_step = st.selectbox("Time Travel (Step)", history)
        if st.button("Restore Selected Step"):
            thread_ts = selected_step.split(' - ')[-1]
            config = None
            for state in st.session_state.agent.graph.get_state_history(thread):
                if state.config['configurable']['thread_ts'] == thread_ts:
                    config = state.config
                    break
            if config:
                state = st.session_state.agent.graph.get_state(config)
                st.session_state.agent.graph.update_state(thread, state.values, as_node=state.values.get('lnode'))
                st.success(f"Restored state to {selected_step}")
                st.experimental_rerun()

# Main Area
st.subheader("Current Progress")
thread = get_thread()
current_state = st.session_state.agent.graph.get_state(thread)
lnode = current_state.values.get("lnode", "Start")

progress_map = {
    "__start__": 0,
    "planner": 20,
    "research_plan": 40,
    "generate": 60,
    "reflect": 80,
    "research_critique": 90,
    "end": 100
}
progress_val = progress_map.get(lnode, 0)

readable_stage = step_mapping.get(lnode, lnode)

st.progress(progress_val, text=f"Stage: {readable_stage}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Agent Stream", "Plan", "Research Content", "Draft", "Critique", "Snapshots"])

with tab1:
    st.subheader("Live Agent Execution")
    log_container = st.empty()
    logs = []
    
    if st.session_state.get("is_running"):
        try:
            for event in st.session_state.stream:
                logs.append(str(event))
                log_container.text_area("Logs", value="\n\n".join(logs), height=400)
            st.session_state.is_running = False
            st.success("Execution Completed")
        except Exception as e:
            st.error(f"Error during execution: {e}")
            st.session_state.is_running = False

    # Show current state info
    thread = get_thread()
    current_state = st.session_state.agent.graph.get_state(thread)
    if current_state.values:
        col1, col2, col3 = st.columns(3)
        col1.metric("Last Node", current_state.values.get("lnode", "N/A"))
        col2.metric("Next Node", str(current_state.next))
        col3.metric("Revision", current_state.values.get("revision_number", 0))

def get_current_value(key):
    thread = get_thread()
    state = st.session_state.agent.graph.get_state(thread)
    return state.values.get(key, "")

def update_state(key, new_value, as_node):
    thread = get_thread()
    st.session_state.agent.graph.update_state(thread, {key: new_value}, as_node=as_node)
    st.success(f"Updated {key}")

with tab2:
    current_plan = get_current_value("plan")
    new_plan = st.text_area("Edit Plan", value=current_plan, height=300)
    if st.button("Update Plan"):
        update_state("plan", new_plan, "planner")

with tab3:
    content = get_current_value("content")
    if isinstance(content, list):
        st.json(content)
    else:
        st.markdown("No research content available.")

with tab4:
    current_draft = get_current_value("draft")
    new_draft = st.text_area("Edit Draft", value=current_draft, height=600)
    if st.button("Update Draft"):
        update_state("draft", new_draft, "generate")

with tab5:
    current_critique = get_current_value("critique")
    new_critique = st.text_area("Edit Critique", value=current_critique, height=300)
    if st.button("Update Critique"):
        update_state("critique", new_critique, "reflect")

with tab6:
    if st.button("Refresh Snapshots"):
        thread = get_thread()
        snapshots = []
        for state in st.session_state.agent.graph.get_state_history(thread):
            snapshots.append(state)
        st.write(snapshots)
