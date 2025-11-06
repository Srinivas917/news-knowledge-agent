import streamlit as st
import asyncio
import nest_asyncio
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from llmAgents.query_agent import query_agent
from langchain.memory import VectorStoreRetrieverMemory, ConversationBufferMemory
from services.mongo_tool import vector_store
from agents import Runner
from services.refining_agent import refine_response_with_gemini
from agents.run import RunConfig
import json

nest_asyncio.apply()
st.set_page_config(page_title="News Knowledge Agent", page_icon="📰", layout="wide")
st.title("📰 News Knowledge Agent")

# ✅ Initialize vector store & memory
retriever = vector_store.as_retriever(search_kwargs={"k": 5})
memory = VectorStoreRetrieverMemory(retriever=retriever, memory_key="chat_history")
memory_1 = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


if "vector_store" not in st.session_state:
    with st.spinner("Creating vector store..."):
        st.session_state.vector_store = vector_store
        st.session_state.retriever = retriever
        st.session_state.memory = memory
        st.session_state.memory_1 = memory_1  
    print("✅ Vector store and memory initialized successfully!")
else:
    vector_store = st.session_state.vector_store
    retriever = st.session_state.retriever
    memory = st.session_state.memory
    memory_1 = st.session_state.memory_1

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if "welcome_shown" not in st.session_state:
    st.info("💡 Hey, what's on your mind today...")
    st.session_state.welcome_shown = True

user_input = st.chat_input("Ask a question or follow up...")
memory_1_history_messages = memory_1.load_memory_variables({})['chat_history']


def handle_query(query: str):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    history_text = ""
    try:
        
        relevant_context = memory.retriever.invoke(query)
        history_text = "\n".join([doc.page_content for doc in relevant_context])


    except Exception as e:
        st.warning(f"Problem retrieving history: {e}")

    if history_text.strip():
        system_message = f"""
        You are continuing a conversation with context below.

        === Previous Context ===
        {history_text}

        === Current User Query ===
        {query}
        """
    else:
        system_message = query

    with st.spinner("Thinking..."):
        st_callback_container = st.container()
        st_callback = StreamlitCallbackHandler(st_callback_container)
        response = asyncio.run(Runner.run(query_agent, system_message))
        answer_text = str(response.final_output)
        print("Using refining agent to improve the answer...")
        refined_answer = refine_response_with_gemini(query, answer_text)
        print("Used refining agent successfully.")

    print("relevant_context----------------\n", relevant_context)
    print("memory_1_history_messages----------------\n", memory_1_history_messages)
    for r in response.raw_responses:
        print("🧾 Token usage:\n", r.usage)
    print("agent thoughts----------------\n", answer_text)
    
    with st.chat_message("assistant"):
        st.markdown(refined_answer)

    st.session_state.messages.append({"role": "assistant", "content": refined_answer})
    st.session_state.last_response = answer_text
    memory.save_context({"user: ": query}, {"assistant: ": answer_text})
    memory_1.save_context({"user: ": query}, {"assistant: ": answer_text})


if user_input:
    handle_query(user_input)
    st.rerun()
