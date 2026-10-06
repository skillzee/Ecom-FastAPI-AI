from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.rag import (INDEX_PATH, PDF_PATH, get_embeddings,)

def main():
    loader = PyPDFLoader(str(PDF_PATH), mode='page')
    pages = loader.load()

    pages = [page for page in pages if page.page_content.strip()]

    if not pages:
        raise ValueError(
            "No text was extracted. A scanned PDF may need OCR."
        )

    print(f"Loaded {len(pages)} non-empty pages")
    print("\nFirst page preview:")
    print(pages[0].page_content[:500])


    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = splitter.split_documents(pages)

    for chunk in chunks:
        chunk.metadata["source"] = PDF_PATH.name

    print(f"\nCreated {len(chunks)} chunks")
    print("\nFirst chunk preview:")
    print(chunks[0].page_content)
    print("\nMetadata:", chunks[0].metadata)

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
    )

    # 4. Save the index, chunk text, and metadata locally.
    vector_store.save_local(str(INDEX_PATH))

    print(f"\nSaved FAISS index to {INDEX_PATH}")


if __name__ == "__main__":
    main()

