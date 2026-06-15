# src/evaluation/eval.py

from langsmith import Client
from langsmith.evaluation import evaluate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

from graph.workflow import graph

# Instantiate LangSmith client
client = Client()


# ============================================================
# Target function — what we're evaluating
# LangSmith calls this with each example from your dataset
# ============================================================

def run_agent(inputs: dict) -> dict:
    """Runs the research agent and returns the output."""
    result = graph.invoke({
        "query": inputs["query"],
        "messages": [],
        "questions": [],
        "findings": [],
        "critiques": None,
        "research_iterations": 0,
        "finalReport": ""
    })
    return {
        "report": result.get("finalReport", ""),
        "questions": result.get("questions", []),
        "iterations": result.get("research_iterations", 0)
    }


# ============================================================
# Evaluator 1 — Heuristic: report structure
# Checks sections, length, keywords — no LLM needed
# ============================================================

def structure_evaluator(run, example):
    """
    Checks if the report has the correct structure.
    Pure Python — fast and free.
    """
    report = run.outputs.get("report", "")
    expected = example.outputs or {}

    score = 0.0
    feedback = []

    # Check required sections
    required_sections = expected.get("must_have_sections", [
        "Executive Summary",
        "Key Findings",
        "Analysis",
        "Sources"
    ])

    sections_found = sum(
        1 for section in required_sections
        if f"# {section}" in report
    )
    section_score = sections_found / len(required_sections)
    score += section_score * 0.4  # 40% of total score

    if sections_found < len(required_sections):
        missing = [
            s for s in required_sections
            if f"# {s}" not in report
        ]
        feedback.append(f"Missing sections: {missing}")

    # Check minimum length
    min_length = expected.get("min_length", 800)
    if len(report) >= min_length:
        score += 0.3  # 30% of total score
    else:
        feedback.append(
            f"Report too short: {len(report)} chars, "
            f"expected {min_length}+"
        )

    # Check required keywords
    must_contain = expected.get("must_contain", [])
    if must_contain:
        keywords_found = sum(
            1 for kw in must_contain
            if kw.lower() in report.lower()
        )
        keyword_score = keywords_found / len(must_contain)
        score += keyword_score * 0.3  # 30% of total score

        if keywords_found < len(must_contain):
            missing_kw = [
                kw for kw in must_contain
                if kw.lower() not in report.lower()
            ]
            feedback.append(f"Missing keywords: {missing_kw}")

    return {
        "key": "structure_score",
        "score": round(score, 2),
        "comment": " | ".join(feedback) if feedback else "All checks passed"
    }


# ============================================================
# Evaluator 2 — Heuristic: research depth
# Checks iterations and question count
# ============================================================

def depth_evaluator(run, example):
    """
    Checks how thoroughly the agent researched.
    More iterations with sufficient=True = good critic.
    """
    iterations = run.outputs.get("iterations", 0)
    questions = run.outputs.get("questions", [])

    score = 0.0
    feedback = []

    # Did it generate enough questions?
    if len(questions) >= 5:
        score += 0.5
    else:
        feedback.append(f"Only {len(questions)} questions generated")

    # Did it use the research loop properly?
    # 1 iteration = critic said sufficient immediately
    # 2-3 iterations = critic worked properly
    if iterations >= 1:
        score += 0.3
    if iterations >= 2:
        score += 0.2
        feedback.append(f"Good: researched {iterations} iterations")

    return {
        "key": "depth_score",
        "score": round(score, 2),
        "comment": " | ".join(feedback) if feedback else "Good research depth"
    }


# ============================================================
# Evaluator 3 — LLM judge: report quality
# Uses a model to assess insight and relevance
# This costs tokens — use sparingly
# ============================================================

def quality_evaluator(run, example):
    """
    Uses GPT-4o-mini to judge report quality.
    Slower and costs tokens but catches quality issues
    that heuristics miss.
    """
    report = run.outputs.get("report", "")
    query = example.inputs.get("query", "")

    if not report:
        return {
            "key": "quality_score",
            "score": 0.0,
            "comment": "No report generated"
        }

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""You are evaluating a research report.

Query: {query}

Report:
{report[:3000]}

Score this report from 0.0 to 1.0 on these criteria:
- Relevance: does it directly answer the query?
- Insight: does it go beyond surface-level information?
- Clarity: is it well-written and easy to understand?
- Accuracy: does the content seem factually sound?

Respond with ONLY a JSON object:
{{"score": 0.85, "reasoning": "brief explanation"}}"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)
        return {
            "key": "quality_score",
            "score": float(result["score"]),
            "comment": result.get("reasoning", "")
        }
    except Exception as e:
        return {
            "key": "quality_score",
            "score": 0.0,
            "comment": f"Evaluator error: {str(e)}"
        }


# ============================================================
# Run the evaluation
# ============================================================

if __name__ == "__main__":
    print("Setting up dataset...")

    datasets = list(client.list_datasets(dataset_name="research-agent-evals"))

    # Check if dataset exists AND has examples
    dataset_ready = False
    if datasets:
        existing = client.read_dataset(dataset_name="research-agent-evals")
        if existing.example_count and existing.example_count > 0:
            print(f"Dataset already exists with {existing.example_count} examples — skipping creation")
            dataset_ready = True
        else:
            # Exists but empty — delete and recreate
            print("Found empty dataset — deleting and recreating...")
            client.delete_dataset(dataset_name="research-agent-evals")

    if not dataset_ready:
        dataset = client.create_dataset(
            dataset_name="research-agent-evals",
            description="Evaluation dataset for research supervisor agent"
        )

        jsonl_path = os.path.join(os.path.dirname(__file__), "research_agent_evals.jsonl")

        with open(jsonl_path, "r") as f:
            examples = [json.loads(line) for line in f if line.strip()]

        client.create_examples(
            inputs=[e["input"] for e in examples],
            outputs=[e["output"] for e in examples],
            dataset_id=dataset.id
        )
        print(f"Created dataset with {len(examples)} examples")

    print("\nRunning evaluation against dataset: research-agent-evals")
    print("This will run your agent on each example — takes a few minutes\n")

    results = evaluate(
        run_agent,
        data="research-agent-evals",
        evaluators=[
            structure_evaluator,
            depth_evaluator,
            quality_evaluator
        ],
        experiment_prefix="research-agent",
        max_concurrency=1,
        metadata={
            "model": "gpt-4o-mini",
            "max_iterations": 3,
            "version": "1.0.0"
        }
    )

    print("\n=== RESULTS ===")
    print(f"Experiment: {results.experiment_name}")
    print("\nOpen LangSmith to see full results:")
    print("https://smith.langchain.com")