import streamlit as st
import asyncio
import nest_asyncio
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from llmAgents.query_agent import query_agent
from constants.vectorStore import vector_store, memory, retriever
from agents import Runner
from constants.llms import models

nest_asyncio.apply()
st.set_page_config(page_title="News Knowledge Agent", page_icon="📰", layout="wide")
st.title("News Knowledge Agent")

# Initialize vector store and memory
if "vector_store" not in st.session_state:
    with st.spinner("Creating vector store..."):
        st.session_state.vector_store = vector_store
        st.session_state.retriever = retriever
        st.session_state.memory = memory
    st.success("✅ Vector store and memory initialized successfully!")

# Load from session state
vector_store = st.session_state.vector_store
retriever = st.session_state.retriever
memory = st.session_state.memory

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "main_answered" not in st.session_state:
    st.session_state.main_answered = False
if st.session_state.get("reset_input_flag", False):
    st.session_state["unified_input"] = ""
    st.session_state["reset_input_flag"] = False
# Display conversation history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**🧑 You:** {msg['content']}")
    else:
        st.markdown(f"**🤖 Assistant:** {msg['content']}")

st.markdown("---")

# Single input box for both main and follow-up queries
user_input = st.text_input(
    "Type your query (or follow-up). Type 'exit' to end conversation:", 
    key="unified_input"
)

if st.button("Submit") and user_input.strip():
    # End conversation
    if user_input.strip().lower() in ["exit", "quit", "bye", "happy"]:
        st.success("✅ Conversation ended. You can start a new query.")
        st.session_state.main_answered = False
        st.session_state.messages.append(
            {"role": "assistant", "content": "Conversation ended."}
        )
        #st.session_state["reset_input_flag"] = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": user_input})

    # Decide if this is main query or follow-up
    if not st.session_state.main_answered:
        system_message = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Always respond as 'Assistant'. "
                    "You can ask follow-up questions to clarify user intent or to continue tasks. "
                    "Provide clear, detailed, and engaging explanations. Avoid jargon."
                ),
            },
            {"role": "user", "content": user_input},
        ]
        with st.spinner("Thinking..."):
            try:
                st_callback_container = st.container()
                st_callback = StreamlitCallbackHandler(st_callback_container)
                response = asyncio.run(Runner.run(query_agent, system_message))
            except Exception as e:
                error_message = f"Sorry, an error occurred: {e}"
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )
                #st.session_state["reset_input_flag"] = True
                st.rerun()

        answer_text = str(response.final_output)
        st.session_state.messages.append({"role": "assistant", "content": answer_text})
        st.session_state.main_answered = True
        memory.save_context({"input": user_input}, {"output": answer_text})

    else:
        # Follow-up query
        history_text = ""
        try:
            history_docs = retriever.invoke(user_input)
            history_text = "\n".join([doc.page_content for doc in history_docs])
        except Exception as e:
            st.warning(f"Problem retrieving history: {e}")

        prompt = f"""
        You are a helpful assistant. Answer the question based on the context below.
        - Clarify user doubts with provided context.
        - If not in context, explain what you know.
        - You can also use relevant past chat.

        Context: {history_text}
        Question: {user_input}
        """
        with st.spinner("Thinking..."):
            result = models.gemini_llm.invoke(prompt)
        answer_text = result.content.strip()

        st.session_state.messages.append({"role": "assistant", "content": answer_text})
        memory.save_context({"input": user_input}, {"output": answer_text})

    # Clear input for next query
    #st.session_state["reset_input_flag"] = True
    st.rerun()
