import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

PDF_DIR = "FAQ_ASSURANCE"
CHROMA_DIR = "backend/vectorstore/chroma"
COLLECTION_NAME = "insurance_faqs"

embeddings = SentenceTransformerEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


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


def main():
    print("Loading PDFs...")
    documents = load_pdfs(PDF_DIR)

    print("Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60,
        separators=["\n\n", "\n"],
    )
    chunks = splitter.split_documents(documents)
    print(f"Total chunks: {len(chunks)}")

    print("Creating embeddings + storing in Chroma...")
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME,
    )
    db.persist()
    print("Embedding complete. Chroma DB ready.")


if __name__ == "__main__":
    main()
