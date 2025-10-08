from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from constants.connection.neo4j_connection import connection
import os  
from dotenv import load_dotenv 
load_dotenv()

chain = GraphCypherQAChain.from_llm(
    ChatGroq(api_key=os.getenv("GROQ_API_KEY"),model="llama-3.3-70b-versatile",temperature=0),
    graph=connection.graph,
    verbose=True,
    return_intermediate_steps=True,
    allow_dangerous_requests=True
)

gemini_llm = ChatGoogleGenerativeAI(api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini-2.0-flash", 
    temperature=0
    )