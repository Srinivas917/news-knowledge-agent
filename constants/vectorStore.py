from constants.connection.mongodb_connection import mongo_connection
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.memory import VectorStoreRetrieverMemory

def create_vector_store_and_memory(db_name="news_db", collection_name="aspects"):

    db = mongo_connection.mongo_client[db_name]
    collection = db[collection_name]
    documents = list(collection.find())
    docs = []
    for item in documents:
        
        content = " ".join(
            str(v)
            for v in item.values()
        )
        docs.append(Document(page_content=content, metadata={"article_id": item["article_id"],"author": item["author"],"category": item["category"]}))

    embedding = HuggingFaceEmbeddings()
    vector_store = FAISS.from_documents(docs, embedding=embedding)
    print("Vector store created with documents from MongoDB")

    memory_store = vector_store
    retriever = memory_store.as_retriever(search_kwargs={"k": 5})
    memory = VectorStoreRetrieverMemory(retriever=retriever, memory_key="chat_history")
    return vector_store, retriever, memory

vector_store, retriever, memory = create_vector_store_and_memory()