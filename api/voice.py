from agents import Runner
import whisper
from io import BytesIO
import streamlit as st
import asyncio
import nest_asyncio
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from llmAgents.query_agent import query_agent
import numpy as np
import soundfile as sf
from constants.llms import models
from langchain.memory import VectorStoreRetrieverMemory
from services.mongo_tool import vector_store

nest_asyncio.apply()
st.set_page_config(page_title="News Knowledge Agent", page_icon="📰", layout="wide")
st.title("News Knowledge Agent")

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
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")  # tiny/base/small/medium/large

whisper_model = load_whisper_model()

def transcribe_audio_in_memory(audio_file, model):
    if audio_file is None:
        return None
    try:
        audio_bytes = audio_file.read()
        audio_np, sr = sf.read(BytesIO(audio_bytes))  # Read as np.ndarray
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
        result = model.transcribe(audio_np, fp16=False)
        st.write(result["text"])
        return result["text"].strip()
    except Exception as e:
        st.error(f"Audio transcription failed: {e}")
        return None
with st.container():
    st.subheader("Ask your main query")
    col1, col2 = st.columns(2)

    with col1:
        user_text = st.text_input("Type your query:", key="main_query", value="")

    with col2:
        audio_file = st.audio_input("🎤 record your query:")


    audio_text = transcribe_audio_in_memory(audio_file, whisper_model)
    # Determine final input (text has priority)
    user_query = user_text.strip() or (audio_text or "").strip()


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
                # response = agent_executor.invoke(
                #     {"input":user_query
                #     },
                #      {"callbacks":[st_callback]},
                     
                # )
                response = asyncio.run(Runner.run(query_agent,system_message))
            except Exception as e:
                error_message = f"Sorry, an error occurred: {e}"
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )
                st.stop()

        #answer_text = str(response["output"])
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

    followup_text = st.text_input("You (Type 'happy' to move on):", key="followup")
    audio_followup = st.audio_input("🎤 Or record follow-up:")
    followup_transcript = transcribe_audio_in_memory(audio_followup, whisper_model)
    

    followup_query = followup_text.strip() or (followup_transcript or "").strip()

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
