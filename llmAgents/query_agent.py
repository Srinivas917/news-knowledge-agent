from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from services.mongo_tool import mongo_tool
from services.neo4j_tool import neo4j_tool
from agents import Agent
from constants.prompts import Prompts
from constants.llms.models import gemini_llm
agent_tools=[mongo_tool, neo4j_tool]

query_agent = Agent(name="neo4j_mongo_agent",
                    model="litellm/gemini/gemini-2.0-flash-lite",
                    tools=agent_tools,
                    instructions=Prompts.instructions)
                               