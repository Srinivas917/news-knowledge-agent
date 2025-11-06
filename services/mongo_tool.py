from agents import (
    Agent, Runner,
    OpenAIChatCompletionsModel,
    function_tool, FunctionTool
)
from langchain_core.tools import tool
# from constants.vectorStore import vector_store
from langchain.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.memory import VectorStoreRetrieverMemory
from constants.connection.mongodb_connection import mongo_connection
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FAISS_PATH = os.path.join(BASE_DIR, "faiss_index")
vector_store =  FAISS.load_local(FAISS_PATH,embeddings=HuggingFaceEmbeddings(),allow_dangerous_deserialization=True)
@function_tool
def mongo_tool(query: str=None):
    """
    Fetch article IDs from MongoDB based on content similarity to the query.
     Args:
        query (str): The content-based query to search for relevant articles.
    Returns:
        List of article_ids that are relevant to the query. 
    The article_id should be in string format and correspond to articles in the Neo4j knowledge graph.
    Example:
    query = "Find articles about climate change and renewable energy."
    returns ["article_id_1", "article_id_2", "article_id_3"]

        """
    
    
    results = vector_store.similarity_search(query, k=5) 
    article_map = {str(insight.metadata["article_id"]): insight for insight in results}
    print(list(article_map.keys()))
    return list(article_map.keys())

@function_tool
def summary_tool(article_ids: list)-> list:
    """
    Fetch article summaries from MongoDB based on a list of article IDs.
    
    Args:
        article_ids (list): List of article IDs to fetch summaries for.
    
    Returns:
        str: Concatenated string of article summaries corresponding to the provided article IDs.
    
    Example:
        article_ids = ["article_id_1", "article_id_2"]
        returns "Summary of article 1...\nSummary of article 2..."
    """

    db = mongo_connection.mongo_client["news_db"]
    collection = db["summaries"]

    if not article_ids or not isinstance(article_ids, list):
        raise ValueError("article_ids must be a non-empty list of article ID strings or integers.")

    converted_ids = []
    for a in article_ids:
        try:
            converted_ids.append(int(a))
        except ValueError:
            converted_ids.append(a)  

    articles_cursor = collection.find(
        {"article_id": {"$in": converted_ids}},
        {"summary.summary": 1, "_id": 0}
    )

    summaries = []
    for doc in articles_cursor:
        try:
            summaries.append(doc["summary"]["summary"])
        except (KeyError, TypeError):
            continue

    if not summaries:
        print("⚠️ No summaries found for the provided article IDs.")
        return []
    combined_text = "\n".join(summaries)
    with open("summary.json", "w") as f:
        json.dump(summaries, f, indent=4)
    print("Retrieved summaries----------\n",combined_text)
    return combined_text
