import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

# --- CONFIG ---
PDF_DIR = "FAQ_ASSURANCE"
CHROMA_DIR = "backend/vectorstore/chroma"
COLLECTION_NAME = "insurance_faqs"

# --- USE A STRONGER EMBEDDING MODEL ---
embeddings = SentenceTransformerEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)


# --- PDF LOADING ---
def load_pdfs(pdf_dir):
    documents = []
    for file in os.listdir(pdf_dir):
        if file.endswith(".pdf"):
            path = os.path.join(pdf_dir, file)
            loader = PyPDFLoader(path)
            docs = loader.load()
            for d in docs:
                d.metadata["source"] = file
            documents.extend(docs)
    return documents


# --- MAIN SCRIPT ---
def main():
    print("Loading PDFs...")
    documents = load_pdfs(PDF_DIR)
    if not documents:
        print("No PDFs found. Exiting.")
        return

    print("Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60,
        separators=["\n\n", "\n"],
    )
    chunks = splitter.split_documents(documents)
    print(f"Total chunks created: {len(chunks)}")

    print("Creating embeddings and storing in Chroma DB...")
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME,
    )
    db.persist()
    print("Embedding complete. Chroma DB ready at:", CHROMA_DIR)


if __name__ == "__main__":
    main()
