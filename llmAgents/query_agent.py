from agents import Agent
from services.mongo_tool import mongo_tool
from services.neo4j_tool import neo4j_tool
from constants.prompts import Prompts

query_agent = Agent(
    name="Neo4j-MongoDB-Agent",
    model="litellm/gemini/gemini-2.0-flash-lite",
    instructions="""
        You are an intelligent agent designed to interact with a Neo4j knowledge graph and a MongoDB database to 
        retrieve and analyze information about news articles, authors, and categories. You can use the provided tools 
        to perform specific tasks based on user queries.
        Your goal is to understand the user's question, determine the appropriate tool to use, and provide a 
        comprehensive answer.
        When responding, consider the following:
        - first analyze the user's question to determine if it requires information from Neo4j, MongoDB, or both.
        - If the user's question requires information about articles, authors, or categories, use the neo4j_tool to
        generate and execute Cypher queries.
        - If the user's question requires finding relevant articles based on content, use the mongo_tool to find
            article IDs. Then swith to neo4j_tool to get the details of those articles.
        - Combine results from both tools to provide a complete answer when necessary.
        """,
    tools=[mongo_tool, neo4j_tool]
    )