"""Simple script to get the embeddings from raw data and populate the faiss index."""

import io
import os
import zipfile
from functools import lru_cache
from itertools import chain

import boto3
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# Initialize the S3 client
BUCKET_NAME = os.environ.get("BUCKET_NAME")
RAW_DOCS_PREFIX = os.environ.get("RAW_DOCS_PREFIX")
VECTOR_DB_PREFIX = os.environ.get("VECTOR_DB_PREFIX")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID")

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 250

boto_session = boto3.Session()
s3_client = boto_session.client("s3")


@lru_cache  # model can be cached
def get_embedding_model(model_id: str = EMBEDDING_MODEL_ID) -> Embeddings:
    """Get embedding model"""

    client = boto_session.client("bedrock-runtime")
    return BedrockEmbeddings(client=client, model_id=model_id)


def lambda_handler(event, context):
    # List objects within the folder in the specified S3 bucket
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=RAW_DOCS_PREFIX)

    if "Contents" not in response:
        return {"statusCode": 400, "body": "No files found in the specified folder."}

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=RAW_DOCS_PREFIX)
    docs = []
    # Iterate over each object in the folder
    for obj in response["Contents"]:
        file_key = obj["Key"]
        # Skip if it is just the folder itself
        if file_key == RAW_DOCS_PREFIX:
            continue
        if file_key.endswith(".zip"):
            # Retrieve the object
            zip_file_dct = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_key)
            docs = process_zip_file(zip_file_dct)

    headers_to_split_on = [
        ("#", "Header 1"),  # split only main headers
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
    docs_splitted = list(chain(*[md_splitter.split_text(doc) for doc in docs]))

    # further split the documents into chunks if they are too large
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    docs_splitted_chars = text_splitter.split_documents(docs_splitted)

    embedding_layer = get_embedding_model()
    vector_store = FAISS.from_documents(docs_splitted_chars, embedding=embedding_layer)
    dump_faiss_index(vector_store)

    return {
        "statusCode": 200,
        "body": f"Files processed successfully and index stored in S3: s3://{BUCKET_NAME}/{VECTOR_DB_PREFIX}.",
    }


def process_zip_file(zip_file_dct: dict) -> list[str]:
    docs = []
    with io.BytesIO(zip_file_dct.get("Body").read()) as file_obj:
        file_obj.seek(0)
        with zipfile.ZipFile(file_obj) as zip_ref:
            file_list = zip_ref.namelist()
            for file_name in file_list:
                with zip_ref.open(file_name) as file:
                    doc = file.read().decode("utf-8")
                    docs.append(doc)
    return docs


def dump_faiss_index(vector_store: FAISS) -> None:
    out_path = "/tmp/faiss/"
    index_name = "index"
    vector_store.save_local(index_name=index_name, folder_path=out_path)

    for file in os.listdir(out_path):
        s3_client.upload_file(Filename=out_path + file, Bucket=BUCKET_NAME, Key=f"{VECTOR_DB_PREFIX}/{file}")
    return
