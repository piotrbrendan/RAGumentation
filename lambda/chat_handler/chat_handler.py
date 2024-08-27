import json
import os
from functools import lru_cache
from pathlib import Path

import boto3
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings


BUCKET_NAME = os.environ.get("BUCKET_NAME")
VECTOR_DB_PREFIX = os.environ.get("VECTOR_DB_PREFIX")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID")
CHAT_MODEL_ID = os.environ.get("CHAT_MODEL_ID")

boto_session = boto3.Session()
s3_client = boto_session.client("s3")
bedrock_client = boto_session.client("bedrock-runtime")


system_template = """
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. 
If the question cannot be answered based on the context provided, say that there is no sufficient data to answer the question. 
Keep the answer concise. Think step-by-step: 
- start with identifying the main topic of the question
- then, find the most relevant information in the context, if there is no relevant information, say that there is no sufficient data to answer the question
- finally, provide a concise answer based on the context if the context is relevant, otherwise respond with: "there is no sufficient data to answer the question".
After considering the above steps and the context, provide a concise answer to the question.
Context: {context} 
"""

human_prompt_template = "Question: {input} \nAnswer:"

PROMPT = ChatPromptTemplate.from_messages([("system", system_template), ("human", human_prompt_template)])

RETRIEVER_KWARGS = {"search_type": "mmr", "search_kwargs": {"k": 5}}
MODEL_KWARGS = {"temperature": 0.0, "max_tokens": 1000, "top_p": 0.9, "top_k": 50}


@lru_cache  # model can be cached
def get_embedding_model(model_id: str = EMBEDDING_MODEL_ID) -> Embeddings:
    """Get embedding model"""
    return BedrockEmbeddings(client=bedrock_client, model_id=model_id)


@lru_cache
def get_chat_model(model_id: str = CHAT_MODEL_ID) -> ChatBedrock:
    """Get chat model"""
    model = ChatBedrock(
        model_id=CHAT_MODEL_ID,
        model_kwargs=MODEL_KWARGS,
        client=bedrock_client,
    )
    return model


@lru_cache
def download_faiss_index() -> None:
    """Downloads the faiss index from S3 to Lambda /tmp directory."""

    tmp_dir = "/tmp"
    for obj in s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=VECTOR_DB_PREFIX)["Contents"]:
        file_key = obj["Key"]
        file_name = Path(file_key).name
        s3_client.download_file(Bucket=BUCKET_NAME, Key=file_key, Filename=f"{tmp_dir}/{file_name}")
    return


@lru_cache
def load_faiss_index() -> FAISS:
    """Load the faiss index from disk"""
    faiss_index = FAISS.load_local(
        folder_path="/tmp",
        index_name="index",
        embeddings=get_embedding_model(EMBEDDING_MODEL_ID),
        allow_dangerous_deserialization=True,
    )
    return faiss_index


def format_docs(docs: list) -> str:
    return "\n\n------------------\n".join(doc.page_content for doc in docs)


def lambda_handler(event, context):
    """Lambda function to interact with the RAG pipeline."""
    question = event.get("input")

    if not question:
        return {"statusCode": 400, "body": "No question provided."}

    download_faiss_index()
    # prep faiss index for retrieval
    faiss_index = load_faiss_index()
    retriever = faiss_index.as_retriever(**RETRIEVER_KWARGS)

    # prep llm for question answering
    model = get_chat_model(CHAT_MODEL_ID)
    question_answer_chain = create_stuff_documents_chain(model, PROMPT)

    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    # invoke the chain
    response = rag_chain.invoke({"input": question})

    # parse the response
    answer = response["answer"]
    sources = format_docs(response["context"])

    return {"statusCode": 200, "body": json.dumps({"answer": answer, "sources": sources})}
