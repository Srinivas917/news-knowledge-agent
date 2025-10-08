from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
load_dotenv()
class connection:
    neo4j_driver = GraphDatabase.driver(os.getenv("NEO4J_URL"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
    graph = Neo4jGraph(url=os.getenv("NEO4J_URL"), username=os.getenv("NEO4J_USER"), password=os.getenv("NEO4J_PASSWORD"))
    session = neo4j_driver.session()
    