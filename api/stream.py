

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

# ✅ Initialize vector store & memory
if "vector_store" not in st.session_state:
    with st.spinner("Creating vector store..."):
        st.session_state.vector_store = vector_store
        st.session_state.retriever = retriever
        st.session_state.memory = memory
    st.success("✅ Vector store and memory initialized successfully!")
else:
    vector_store = st.session_state.vector_store
    retriever = st.session_state.retriever
    memory = st.session_state.memory

if "messages" not in st.session_state:
    st.session_state.messages = [] 

if "main_answered" not in st.session_state:
    st.session_state.main_answered = False

if st.session_state.messages:
    # st.markdown("### 💬 Conversation History")
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")
        else:
            st.markdown(f"**🤖 Assistant:** {msg['content']}")

st.markdown("---")

with st.container():
    st.subheader("Ask your main query")
    user_query = st.text_input("Enter your query", key="main_query")

    if st.button("Submit Query") and user_query.strip():
        st.session_state.messages.append({"role": "user", "content": user_query})

        system_message = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Always respond as 'Assistant'. "
                    "You can ask follow-up questions to clarify user intent or to continue tasks. "
                    "If the user says 'yes' or 'no', continue the previous task appropriately. "
                    "Provide clear, detailed, and engaging explanations. Avoid jargon."
                ),
            },
            {"role": "user", "content": user_query},
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
                st.stop()

        answer_text = str(response.final_output)
        st.session_state.messages.append({"role": "assistant", "content": answer_text})
        st.session_state.main_answered = True

        memory.save_context({"input": user_query}, {"output": answer_text})
        st.rerun()  

def clear_followup():
    st.session_state.update({"followup": ""})


if st.session_state.main_answered:
    st.markdown("---")
    st.subheader("💬 Follow-up Questions")

    if "followup" not in st.session_state:
        st.session_state.followup = ""

    followup_query = st.text_input("You (Type 'happy' to move on):", key="followup")

    if st.button("Submit Follow-up"):
        if followup_query.strip().lower() in ["happy", "exit", "quit", "bye"]:
            st.success("✅ Conversation ended. You can start a new main query above.")
            st.session_state.main_answered = False
            st.session_state.last_response = None
            clear_followup()
            st.rerun()

        st.session_state.messages.append({"role": "user", "content": followup_query})

        history_text = ""
        try:
            history_docs = retriever.invoke(followup_query)
            history_text = "\n".join([doc.page_content for doc in history_docs])
        except Exception as e:
            st.warning(f"Problem retrieving history: {e}")

        # Handle summary
        if "summary" in followup_query.lower():
            summary_prompt = f"""
            You are an expert content Explainer.
            - Brief the following response in a clear and concise way.
            - Keep original meaning intact, avoid jargon.
            - Explain in points, include aspects + key details.
            - If too long, pick only important parts.
            If nothing to explain, return as is.

            {history_text}
            """
            with st.spinner("Summarizing..."):
                summary = models.gemini_llm.invoke(summary_prompt)
            answer_text = summary.content

        else:
            prompt = f"""
            You are a helpful assistant. Answer the question based on the context below.
            - Clarify user doubts with provided context.
            - If not in context, explain what you know.
            - You can also use relevant past chat.

            Context: {history_text}
            Question: {followup_query}
            """
            with st.spinner("Thinking..."):
                result = models.gemini_llm.invoke(prompt)
            answer_text = result.content.strip()

        
        st.session_state.messages.append({"role": "assistant", "content": answer_text})

        memory.save_context({"input": followup_query}, {"output": answer_text})
        st.rerun() 
