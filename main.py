from agents import Agent, Runner
from services import mongo_tool, neo4j_tool
from constants.vectorStore import vector_store, memory, retriever
from langchain.memory import VectorStoreRetrieverMemory
import asyncio
from constants.llms import models
from constants.prompts import Prompts
from llmAgents.query_agent import query_agent
from constants.connection.neo4j_connection import connection
from constants.connection.mongodb_connection import mongo_connection
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def main():
    while True:
        query = input("Enter your query (or type 'exit' to quit): ")
        system_message = [{
        "role": "system",
        "content": (
            "You are a helpful assistant. Always respond as 'Assistant'. "
            "You can ask follow-up questions to clarify user intent or to continue tasks. "
            "If the user says 'yes' or 'no', continue the previous task appropriately. "
            "Provide clear, detailed, and engaging explanations. Avoid jargon."
        )
    },
        {"role": "user", "content": query}]
        if query.strip().lower() == "exit":
            print("Bot: Goodbye! 👋")
            break
        response = await Runner.run(query_agent, system_message)
        print("\n=== Response ===")
        print(response)
        
        memory.save_context(
        {"input": query},
        {"output": str(response.final_output)}
    )

        while True:
            user_input = input("You (Type 'happy' to move on): ")
            if user_input.strip().lower() in ["happy", "exit", "quit", "bye"]:
                
                break
            try:
                history_docs = retriever.invoke(user_input)
                history_text = "\n".join([doc.page_content for doc in history_docs])
                print("history text retrieved")
            except Exception as e:
                print(f"problem in retrieving: {e}")
            if "summary" in user_input.lower():
                summary_prompt = f"""
        You are an expert content Explainer.
        - Brief the following response in a clear and concise way. Explain the response in detail covering everything.
        - Keep the original meaning and intent of the response intact. Use simple and easy-to-understand language. Avoid jargon and technical terms. Make it engaging and informative.
        - Make the content for every article in points. while explaining the answer, make sure to include the aspects of the article too.
        - Include the key details of the article too in the explanation. 
        - If there are any links present in the response, get the content and explain by visiting the link.
        - If the response is too long for you, take the important things only.

        if there is no explainable content, just print the response as it is.
        

        {response}
        """
        
                summary = models.gemini_llm.invoke(summary_prompt)

                print(summary.content)
            prompt = f"""
            You are a helpful assistant. Answer the question based on the context below.
            - Clarify user doubts with the provided context. If the answer is not in the context, instead of saying "I don't know",
            explain what you know according to context.
            - you can also use the following relevant past chat from the conversation to answer the question.

            Context: {response}  
            Question: {user_input}
            Relevant past chat: {history_text}

            Answer:
            """

            result = models.gemini_llm.invoke(prompt)
            print("\n=== Response ===")
            print(result.content.strip())
            memory.save_context(
        {"input": query},
        {"output": str(result.content.strip())}
    )

def cleanup():
    """Clean up database connections."""
    try:
        if connection.neo4j_driver:
            connection.neo4j_driver.close()
        if mongo_connection.mongo_client:
            mongo_connection.mongo_client.close()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🤖 Shutting down...")
    finally:
        cleanup()