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
    
    
    # vector_store =  FAISS.load_local("faiss_index",embeddings=HuggingFaceEmbeddings(),allow_dangerous_deserialization=True)
    results = vector_store.similarity_search(query, k=5) 
    article_map = {str(insight.metadata["article_id"]): insight for insight in results}
    print(list(article_map.keys()))
    return list(article_map.keys())