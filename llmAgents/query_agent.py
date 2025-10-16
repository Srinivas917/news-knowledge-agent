from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from services.mongo_tool import mongo_tool
from services.neo4j_tool import neo4j_tool
from agents import Agent
from constants.prompts import Prompts
#from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from constants.llms.models import gemini_llm
agent_tools=[mongo_tool, neo4j_tool]
# prompt = ChatPromptTemplate.from_messages([
#     SystemMessagePromptTemplate.from_template(Prompts.instructions),
#     HumanMessagePromptTemplate.from_template("{input}\n{agent_scratchpad}")
    
# ])
# query_agent = create_tool_calling_agent(
#     llm=gemini_llm,
#     prompt=prompt,
#     tools=agent_tools
#     )

# agent_executor = AgentExecutor(agent=query_agent, tools=agent_tools, verbose=True)

query_agent = Agent(name="neo4j_mongo_agent",
                    model="litellm/gemini/gemini-2.0-flash-lite",
                    tools=agent_tools,
                    instructions=Prompts.instructions)
                               