from services.mongo_tool import mongo_tool, summary_tool
from services.neo4j_tool import neo4j_tool
from agents import Agent
from constants.prompts import Prompts
import os
from dotenv import load_dotenv
load_dotenv()

query_agent = Agent(name="neo4j_mongo_agent",
                    model="litellm/gemini/gemini-2.0-flash-lite",
                    tools=[mongo_tool, neo4j_tool, summary_tool],
                    instructions=Prompts.instructions)
                               