"""Entry point for the RAG content agent."""

import os
import logging
import argparse
from datetime import datetime
from src.ingest import load_documents
from src.chunking import split_documents
from src.vector_store import create_vector_store
from src.generator import generate_blog, generate_tweet, generate_linkedin_post
from src.evaluator import build_evaluation_dataset, evaluate_rag_pipeline, save_evaluation_results
from src.config import OUTPUT_PATH, TOP_K

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Suppress verbose third-party HTTP request logs
for logger_name in ["httpx", "urllib3", "huggingface_hub", "sentence_transformers"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def save_output(filename: str, content: str, timestamp: str) -> str:
    """Saves generated content to a file with a timestamp."""
    name, ext = os.path.splitext(filename)
    timestamped_name = f"{name}_{timestamp}{ext}"
    filepath = os.path.join(OUTPUT_PATH, timestamped_name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return timestamped_name

def _preview_text(text: str, limit: int = 220) -> str:
    """Returns a compact preview of text for logging."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."

def main():
    parser = argparse.ArgumentParser(description="RAG Content Agent Pipeline")
    parser.add_argument("--eval", action="store_true", help="Run the RAGAS evaluation pipeline after generation")
    parser.add_argument("--query", type=str, default="How AEO/GEO is shifting the search game from SEO to AI visibility", help="The query to generate content for")
    args = parser.parse_args()

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Load Documents
    logger.info("Loading documents...")
    documents = load_documents()

    if not documents:
        logger.warning("No documents loaded.")
        return

    logger.info("Loaded %s documents successfully.\n", len(documents))

    # 2. Chunk Documents
    logger.info("Chunking documents...")
    chunks = split_documents(documents)
    logger.info("Generated %s chunks.", len(chunks))

    empty_chunks = [chunk for chunk in chunks if not chunk.page_content.strip()]
    if empty_chunks:
        logger.error("Validation failed: %s empty chunks found.", len(empty_chunks))
        return

    if chunks:
        logger.info("Sample chunk preview: %s\n", _preview_text(chunks[0].page_content))

    # 3. Create or Load Vector Database
    logger.info("Creating embeddings...")
    vectordb = create_vector_store(chunks)
    logger.info("Embeddings generated successfully.")
    logger.info("Loading ChromaDB...")
    logger.info("Vector database ready.\n")

    # 4. Retrieval Setup
    query = args.query
    logger.info("Retrieving relevant context for query: '%s'\n", query)
    
    # Create the retriever from the chroma vectorstore
    retriever = vectordb.as_retriever(search_kwargs={"k": TOP_K})
    
    # Just to log the number of chunks retrieved
    retrieved_chunks = retriever.invoke(query)
    logger.info("Retrieved %s chunks.", len(retrieved_chunks))

    if retrieved_chunks:
        for index, chunk in enumerate(retrieved_chunks, start=1):
            logger.info("Retrieved chunk %s preview: %s", index, _preview_text(chunk.page_content))
    logger.info("")
    
    # 5. Generation
    logger.info("Generating blog post...")
    blog_output = generate_blog(query, retriever)
    if not blog_output.strip():
        logger.error("Gemini blog response empty.")
        return
    logger.info("Gemini blog response status: ok (chars=%s)", len(blog_output))
    saved_blog = save_output("blog_output.txt", blog_output, run_timestamp)

    logger.info("Generating tweet...")
    tweet_output = generate_tweet(query, retriever)
    if not tweet_output.strip():
        logger.error("Gemini tweet response empty.")
        return
    logger.info("Gemini tweet response status: ok (chars=%s)", len(tweet_output))
    saved_tweet = save_output("tweet_output.txt", tweet_output, run_timestamp)

    logger.info("Generating LinkedIn post...")
    linkedin_output = generate_linkedin_post(query, retriever)
    if not linkedin_output.strip():
        logger.error("Gemini LinkedIn response empty.")
        return
    logger.info("Gemini LinkedIn response status: ok (chars=%s)", len(linkedin_output))
    saved_linkedin = save_output("linkedin_output.txt", linkedin_output, run_timestamp)

    logger.info("\nOutputs saved successfully:")
    logger.info("- %s", saved_blog)
    logger.info("- %s", saved_tweet)
    logger.info("- %s", saved_linkedin)

    # 6. Evaluation
    if not args.eval:
        logger.info("\nSkipping RAG evaluation. Run with --eval to execute the evaluation pipeline.")
        return

    logger.info("\n==================================================")
    logger.info("Starting RAG Evaluation Phase...")
    logger.info("==================================================\n")
    
    eval_queries = [
        "What is AEO?",
        "How is AEO different from SEO?"
    ]
    
    eval_ground_truths = [
        "AEO (Answer Engine Optimization) focuses on optimizing content for AI-powered answer engines instead of traditional search engine results pages.",
        "While SEO focuses on ranking blue links on search engine results pages (SERPs), AEO focuses on providing direct, structured answers that AI search engines can easily synthesize and display."
    ]

    data, dataset = build_evaluation_dataset(retriever, eval_queries, eval_ground_truths)
    
    result = evaluate_rag_pipeline(dataset)
    
    result = evaluate_rag_pipeline(dataset)

    if result:
        result_dict = result.to_pandas().mean(numeric_only=True).to_dict()

        logger.info("\nFaithfulness Score: %.2f", result_dict.get("faithfulness", 0.0))
        logger.info("Answer Relevancy Score: %.2f", result_dict.get("answer_relevancy", 0.0))
        logger.info("Context Recall Score: %.2f", result_dict.get("context_recall", 0.0))

        saved_eval = save_evaluation_results(result, data)

        logger.info(
            "\nEvaluation completed successfully. Results saved to: %s",
            saved_eval
        )


if __name__ == "__main__":
    main()

