from agents import (
    Agent, Runner,
    OpenAIChatCompletionsModel,
    function_tool, FunctionTool
)
from langchain_core.tools import tool
from constants.llms.models import chain 
from constants.connection.neo4j_connection import connection
from constants.prompts import Prompts

@function_tool
def neo4j_tool(query: str=None):
    """
    Generate and execute a Cypher query against the Neo4j database.
    """
    prompts = Prompts(query)
    restricted_query = f"""
You are a Cypher query generator for Neo4j.
Rules:
- Always include 'b.refLink' (article reference link) in the RETURN clause for every query.
- Do NOT return all properties of a node.
- Always include exactly one RETURN clause.
- Do NOT include explanations, natural language text, or comments in the response.
- Respond with ONLY the Cypher query.
- If the query is about getting the articles, return all the properties present including author, category.

Schema pattern to always follow:
{{MATCH (a:Author)-[:WROTE]->(b:Articles)-[:BELONGSTO]->(c:Category)}}

Follow the schema pattern strictly. Check the nodes, labels, properties, and relationships before generating the Cypher query.

After generating the Cypher query, make sure to run the query in the Neo4j database. Always return the result of the query.

The labels are:
Author, Articles, Category

- Always take the Category values in lower case.

User question: {query}

Example Cypher:
MATCH (a:Author)-[:WROTE]->(b:Articles)-[:BELONGSTO]->(c:Category)
    WHERE b.article_id = "13"
    RETURN b.title AS title, b.refLink AS refLink, a.author AS author, c.category AS category
"""

    result = chain.invoke(restricted_query)
        
    required = connection.session.run(result["result"])
    ans = []
    for r in required:
        ans.append(r)
    print(ans)
    return ans