import chainlit as cl
import asyncio
import nest_asyncio
from langchain.callbacks.base import BaseCallbackHandler
from llmAgents.query_agent import query_agent
from constants.vectorStore import vector_store, memory, retriever
from agents import Runner
from constants.llms import models

nest_asyncio.apply()

# ✅ Optional streaming handler
class ChainlitStreamHandler(BaseCallbackHandler):
    def __init__(self):
        self.msg = None

    async def on_llm_start(self, *args, **kwargs):
        self.msg = await cl.Message(content="").send()

    async def on_llm_new_token(self, token: str, *args, **kwargs):
        if self.msg:
            await self.msg.stream_token(token)

    async def on_llm_end(self, *args, **kwargs):
        if self.msg:
            await self.msg.update()

# 🧠 Simple heuristic to decide if it's a new query or follow-up
def is_new_query(user_query: str, prev_query: str | None) -> bool:
    if not prev_query:
        return True
    # If it's too different in keywords, treat as new query
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, user_query.lower(), prev_query.lower()).ratio()
    return similarity < 0.4  # Threshold can be adjusted

@cl.on_chat_start
async def start_chat():
    """Initialize session state for each new user session."""
    cl.user_session.set("vector_store", vector_store)
    cl.user_session.set("retriever", retriever)
    cl.user_session.set("memory", memory)
    cl.user_session.set("last_query", None)  # Track previous main query

    await cl.Message(
        content="📰 **Welcome to News Knowledge Agent!**\nAsk your main query to get started."
    ).send()

@cl.on_message
async def handle_message(message: cl.Message):
    user_query = message.content.strip()
    retriever = cl.user_session.get("retriever")
    memory = cl.user_session.get("memory")
    last_query = cl.user_session.get("last_query")

    # ✅ Detect whether it's a new main query or follow-up
    new_query_flag = is_new_query(user_query, last_query)

    # 🛑 End conversation commands
    if user_query.lower() in ["happy", "exit", "quit", "bye"]:
        await cl.Message(content="✅ Conversation ended. You can start a new query any time.").send()
        cl.user_session.set("last_query", None)
        return

    # -------------------------
    # 🟡 NEW QUERY SECTION
    # -------------------------
    if new_query_flag:
        await cl.Message(content="🤔 Thinking...").send()
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

        try:
            response = await Runner.run(query_agent, system_message)
            answer_text = str(response.final_output)
        except Exception as e:
            await cl.Message(content=f"❌ Error: {e}").send()
            return

        await cl.Message(content=answer_text).send()
        memory.save_context({"input": user_query}, {"output": answer_text})
        cl.user_session.set("last_query", user_query)  # 📝 update last query
        return

    # -------------------------
    # 🟢 FOLLOW-UP SECTION
    # -------------------------
    try:
        history_docs = retriever.invoke(user_query)
        history_text = "\n".join([doc.page_content for doc in history_docs])
    except Exception as e:
        await cl.Message(content=f"⚠️ Context retrieval failed: {e}").send()
        history_text = ""

    # 📝 Summarization follow-up
    if "summary" in user_query.lower():
        summary_prompt = f"""
        You are an expert content explainer.
        - Summarize the following clearly and concisely.
        - Keep original meaning intact, avoid jargon.
        - Explain in bullet points.
        If nothing to summarize, return as is.

        {history_text}
        """
        msg = await cl.Message(content="📝 Summarizing...").send()
        summary = models.gemini_llm.invoke(summary_prompt)
        answer_text = summary.content
        await msg.remove()
        await cl.Message(content=answer_text).send()

    else:
        follow_prompt = f"""
        You are a helpful assistant. Answer based on the context below.
        - Clarify the follow-up query using previous context if relevant.
        - If not in context, respond based on your knowledge.

        Context:
        {history_text}

        Follow-up Question:
        {user_query}
        """
        msg = await cl.Message(content="🤔 Thinking...").send()
        result = models.gemini_llm.invoke(follow_prompt)
        answer_text = result.content.strip()
        await msg.remove()
        await cl.Message(content=answer_text).send()

    memory.save_context({"input": user_query}, {"output": answer_text})
