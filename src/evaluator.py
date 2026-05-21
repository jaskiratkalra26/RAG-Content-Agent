"""Evaluation module using RAGAS for assessing RAG pipeline performance."""

import os
import json
import logging
import time
from typing import List, Dict, Any

import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from src.embeddings import get_embedding_model
from src.config import GEMINI_MODEL_NAME, OUTPUT_PATH
from src.generator import _build_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def build_evaluation_dataset(retriever, queries: List[str], ground_truths: List[str]) -> tuple[List[Dict[str, Any]], Dataset]:
    """Generates answers and retrieves contexts to build the Ragas evaluation dataset."""
    data = []
    
    # Build a simple QA chain for evaluation answers
    prompt_str = "Answer the question based on the provided context.\n\nContext:\n{context}\n\nQuestion: {input}\n\nAnswer:"
    qa_chain = _build_retrieval_chain(prompt_str, retriever)
    
    total = len(queries)
    for i, (query, gt) in enumerate(zip(queries, ground_truths), start=1):
        logger.info("Evaluating query %s/%s...", i, total)
        retrieved_docs = retriever.invoke(query)
        contexts = [doc.page_content for doc in retrieved_docs]
        
        response = qa_chain.invoke({"input": query})
        answer = response["answer"]
        
        data.append({
            "question": query,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": gt
        })
        
        # Add a delay to avoid hitting Gemini free tier rate limits (15 RPM limit)
        if i < total:
            logger.info("Sleeping for 60 seconds to respect API rate limits...")
            time.sleep(60)
        
    dataset = Dataset.from_list(data)
    return data, dataset

def evaluate_rag_pipeline(dataset: Dataset) -> Any:
    """Evaluates the pipeline using RAGAS metrics."""
    logger.info("Running RAG evaluation...")
    
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME)
    embeddings = get_embedding_model()
    
    # Import RunConfig to throttle Ragas concurrency to avoid rate limits
    from ragas.run_config import RunConfig
    
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=1, max_retries=10, max_wait=60) # process slower
    )
    
    return result

def save_evaluation_results(result: Any, data: List[Dict[str, Any]]) -> str:
    """Saves the evaluation metrics and query-wise results to a JSON file."""
    filepath = os.path.join(OUTPUT_PATH, "evaluation_results.json")
    
    # Safely extract overall metrics without using dict(result) which triggers KeyError: 0
    overall_metrics = {}
    if result:
        if hasattr(result, "_repr_dict"):
            overall_metrics = result._repr_dict
        else:
            try:
                overall_metrics = result.to_pandas().mean(numeric_only=True).to_dict()
            except Exception as e:
                logger.warning("Could not calculate overall metrics using pandas fallback: %s", e)
                overall_metrics = {}

    output = {
        "overall_metrics": overall_metrics,
        "query_wise_evaluation": []
    }
    
    try:
        df = result.to_pandas()
        df = df.where(pd.notnull(df), None)
        output["query_wise_evaluation"] = df.to_dict(orient="records")
    except Exception as e:
        logger.error("Failed to convert results to pandas DataFrame: %s", e)
        output["query_wise_evaluation"] = data
        
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)
        
    return filepath

