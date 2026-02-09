import argparse
import sys
from pathlib import Path


def main() -> None:
    # Ensure project root is on sys.path
    root_dir = Path(__file__).resolve().parents[1]
    if str(root_dir) not in sys.path:
        sys.path.append(str(root_dir))

    from app.rag_pipeline import RAGPipeline, RAGConfig

    parser = argparse.ArgumentParser(
        description=(
            "Update the Chroma index. "
            "For now this performs the same full ingestion as build_index."
        )
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Default number of results to retrieve (stored in RAG config).",
    )
    args = parser.parse_args()

    pipeline = RAGPipeline(rag_config=RAGConfig(top_k=args.top_k))
    print("Starting index update (full re-ingestion)...")
    documents = pipeline.run_full_ingestion()
    print(f"Completed. Indexed {len(documents)} documents.")


if __name__ == "__main__":
    main()

