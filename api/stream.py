import streamlit as st
import asyncio
import nest_asyncio
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from llmAgents.query_agent import query_agent
from langchain.memory import VectorStoreRetrieverMemory
from services.mongo_tool import vector_store
from agents import Runner
from constants.llms import models

nest_asyncio.apply()
st.set_page_config(page_title="News Knowledge Agent", page_icon="📰", layout="wide")
st.title("📰 News Knowledge Agent")

# ✅ Initialize vector store & memory
retriever = vector_store.as_retriever(search_kwargs={"k": 5})
memory = VectorStoreRetrieverMemory(retriever=retriever, memory_key="chat_history")

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

# ✅ Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "main_answered" not in st.session_state:
    st.session_state.main_answered = False
if "last_response" not in st.session_state:
    st.session_state.last_response = None

# 📝 Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if "welcome_shown" not in st.session_state:
    st.info("💡 Hey, what's on your mind today...")
    st.session_state.welcome_shown = True

# 💬 Single input box
user_input = st.chat_input("Ask a question or follow up...")

# 🧠 Function to handle MAIN query
def handle_main_query(query: str):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

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
        {"role": "user", "content": query},
    ]

    with st.spinner("Thinking..."):
        st_callback_container = st.container()
        st_callback = StreamlitCallbackHandler(st_callback_container)
        response = asyncio.run(Runner.run(query_agent, system_message))

    answer_text = str(response.final_output)
    with st.chat_message("assistant"):
        st.markdown(answer_text)

    st.session_state.messages.append({"role": "assistant", "content": answer_text})
    st.session_state.main_answered = True
    st.session_state.last_response = answer_text

    # Save context to memory
    memory.save_context({"input": query}, {"output": answer_text})


# 🧠 Function to handle FOLLOW-UP query
def handle_followup_query(query: str):

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    history_text = ""
    try:
        history_docs = retriever.invoke(query)
        history_text = "\n".join([doc.page_content for doc in history_docs])
    except Exception as e:
        st.warning(f"Problem retrieving history: {e}")

    previous_answer = st.session_state.get("last_response", "")

    if "summary" in query.lower():
        summary_prompt = f"""
        You are an expert content Explainer.
        - Brief the following response in a clear and concise way.
        - Keep original meaning intact, avoid jargon.
        - Explain in points, include aspects + key details.
        - If too long, pick only important parts.
        If nothing to explain, return as it is.
        question_response: {previous_answer}
        history_text: {history_text}
        """
        with st.spinner("Summarizing..."):
            summary = models.gemini_llm.invoke(summary_prompt)
        answer_text = summary.content
    else:
        followup_prompt = f"""
You are a helpful assistant. Answer the question using the following approach:
1. First, answer based on the previous answer (focus on the same topic): {previous_answer}. Do NOT print the previous answer directly.
2. Only use the context below if it is clearly relevant to the previous topic:
{history_text}

- Do NOT change the topic to unrelated areas unless the user explicitly asks.
- Clarify user doubts clearly.
- Keep responses structured and detailed.

Question: {query}
"""

        with st.spinner("Thinking..."):
            result = models.gemini_llm.invoke(followup_prompt)
        answer_text = result.content.strip()

    with st.chat_message("assistant"):
        st.markdown(answer_text)

    st.session_state.messages.append({"role": "assistant", "content": answer_text})
    memory.save_context({"input": query}, {"output": answer_text})


# 🚀 Main interaction logic
if user_input:
    # Ask model to classify follow-up vs new query
    try:
        followup_check_prompt = f"""
You are an intelligent assistant. Determine if the user query is a follow-up to your previous response.

Previous answer: {st.session_state.get('last_response', '')}
User query: {user_input}

Answer with ONLY one word: "FOLLOWUP" if the user is continuing the previous topic, otherwise "NEW".
"""
        
        classification = models.gemini_llm.invoke(followup_check_prompt).content.strip().upper()
    except Exception as e:
        classification = "NEW"  

    if classification == "FOLLOWUP":
        handle_followup_query(user_input)
    else:
        handle_main_query(user_input)

    st.rerun()
