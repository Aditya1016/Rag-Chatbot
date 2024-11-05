import argparse
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embedding_function import get_embedding_function
from langchain_chroma import Chroma

CHROMA_PATH = "./RAG_Chatbot/chroma"
DATA_PATH = "../RAG_Chatbot/data"

def main():
    # Check if the database should be cleared (using the --reset flag).
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    if args.reset:
        print("✨ Clearing Database")
        clear_database()

    # Load documents and process them.
    documents = load_documents()
    print(f"Loaded documents: {len(documents)}")
    chunks = split_documents(documents)
    print(f"Document chunks: {len(chunks)}")

    # Add processed chunks to the Chroma database.
    add_to_chroma(chunks)

def load_documents():
    # Check if DATA_PATH exists and is accessible.
    if not os.path.exists(DATA_PATH):
        print(f"❌ DATA_PATH '{DATA_PATH}' does not exist.")
        return []
    
    # List files in DATA_PATH for debugging.
    files = os.listdir(DATA_PATH)
    print(f"Files in DATA_PATH: {files}")
    
    # Check if there are PDF files in DATA_PATH.
    pdf_files = [f for f in files if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("❌ No PDF files found in DATA_PATH.")
        return []

    # Load PDFs using PyPDFDirectoryLoader.
    document_loader = PyPDFDirectoryLoader(DATA_PATH)
    documents = document_loader.load()
    print(f"Documents loaded independently: {len(documents)}")
    return documents

def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

def add_to_chroma(chunks: list[Document]):
    # Load the existing database or create a new one.
    db = Chroma(
        persist_directory=CHROMA_PATH, embedding_function=get_embedding_function()
    )
    print("Database loaded.")

    # Calculate unique IDs for each chunk.
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Fetch existing documents in the DB.
    existing_items = db.get(include=[])  # IDs are always included by default
    existing_ids = set(existing_items["ids"])
    print(f"Existing document IDs in DB: {existing_ids}")
    print(f"Number of existing documents in DB: {len(existing_ids)}")

    # Only add documents that are not already in the DB.
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if new_chunks:
        print(f"👉 Adding new documents: {len(new_chunks)}")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        print(f"New document IDs: {new_chunk_ids}")
        db.add_documents(new_chunks, ids=new_chunk_ids)
    else:
        print("✅ No new documents to add")

def calculate_chunk_ids(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the page metadata.
        chunk.metadata["id"] = chunk_id

    return chunks

def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        print("Database cleared.")
    else:
        print("No existing database found to clear.")

if __name__ == "__main__":
    main()
