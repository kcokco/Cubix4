import os
import glob
from pathlib import Path
from unstructured.partition.md import partition_md
from vectordb import VectorDB
from typing import List, Dict


def process_markdown_files(folder_path: str) -> List[Dict]:
    """
    Process markdown files from given folder using unstructured library
    """
    documents = []
    md_files = glob.glob(os.path.join(folder_path, "**/*.md"), recursive=True)

    for file_path in md_files:
        try:
            elements = partition_md(filename=file_path)

            text_content = []
            for element in elements:
                if hasattr(element, 'text') and element.text.strip():
                    text_content.append(element.text.strip())

            if text_content:
                full_text = "\n".join(text_content)

                metadata = {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "folder": os.path.dirname(file_path),
                    "version": extract_version_from_path(file_path)
                }

                documents.append({
                    "text": full_text,
                    "metadata": metadata
                })

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    return documents


def extract_version_from_path(file_path: str) -> str:
    """Extract version from file path (e.g., v1.2.x from path)"""
    path_parts = file_path.split(os.sep)
    for part in path_parts:
        if part.startswith('v') and ('.' in part or 'x' in part):
            return part
    return "unknown"


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better retrieval
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        chunk = text[start:end]

        last_sentence = chunk.rfind('.')
        last_newline = chunk.rfind('\n')

        break_point = max(last_sentence, last_newline)
        if break_point > start + chunk_size // 2:
            chunk = text[start:break_point + 1]
            end = break_point + 1

        chunks.append(chunk)
        start = end - overlap

    return chunks


def upload_documents_to_qdrant(documents: List[Dict], vector_db: VectorDB, enable_chunking: bool = True):
    """
    Upload processed documents to Qdrant vector database
    """
    uploaded_count = 0

    for doc in documents:
        try:
            text = doc["text"]
            metadata = doc["metadata"]

            if enable_chunking:
                chunks = chunk_text(text)
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["total_chunks"] = len(chunks)

                    vector_db.add_document(chunk, chunk_metadata)
                    uploaded_count += 1
            else:
                vector_db.add_document(text, metadata)
                uploaded_count += 1

        except Exception as e:
            print(f"Error uploading document {metadata.get('file_name', 'unknown')}: {e}")

    return uploaded_count


def main():
    """
    Main function to process and upload Qdrant documentation
    """
    data_folder = "data/docs/qdrant/v1.2.x"

    if not os.path.exists(data_folder):
        available_versions = []
        base_path = "data/docs/qdrant"
        if os.path.exists(base_path):
            available_versions = [d for d in os.listdir(base_path)
                                if os.path.isdir(os.path.join(base_path, d))]

        if available_versions:
            print(f"v1.2.x not found. Available versions: {available_versions}")
            data_folder = f"data/docs/qdrant/{available_versions[0]}"
            print(f"Using {data_folder} instead")
        else:
            print("No Qdrant documentation found in data/docs/qdrant/")
            return

    print(f"Processing markdown files from: {data_folder}")

    documents = process_markdown_files(data_folder)
    print(f"Processed {len(documents)} documents")

    vector_db = VectorDB()

    uploaded_count = upload_documents_to_qdrant(documents, vector_db, enable_chunking=True)
    print(f"Uploaded {uploaded_count} document chunks to Qdrant")


if __name__ == "__main__":
    main()