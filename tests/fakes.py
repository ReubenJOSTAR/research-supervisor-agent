"""Fake LLMs and search for running agents and the graph without network calls."""
from langchain_core.messages import AIMessage

from agents.research_task import Findings
from schemas.finding import Finding


class Fake:
    """Returns the given outputs in order, then repeats the last one. Records calls."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def invoke(self, arg):
        self.calls.append(arg)
        return self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]


def _prompt_text(arg) -> str:
    return arg if isinstance(arg, str) else arg[0].content


def task_of(prompt: str, tasks) -> str:
    """Which of `tasks` a branch prompt is about (branches run in any order)."""
    matches = [t for t in tasks if t in prompt]
    assert len(matches) == 1, f"prompt should mention exactly one of {tasks}"
    return matches[0]


class FakeResearchAgent:
    """Asks for one search per call, querying the branch's task. Raises for `fail_on` tasks."""

    def __init__(self, tasks, fail_on=(), calls_per_task=1):
        self.tasks, self.fail_on, self.calls_per_task = list(tasks), set(fail_on), calls_per_task
        self.calls = []

    def invoke(self, messages):
        prompt = _prompt_text(messages)
        self.calls.append(prompt)
        task = task_of(prompt, self.tasks)
        if task in self.fail_on:
            raise RuntimeError(f"LLM exploded on {task}")
        calls = [{"name": "search_web", "args": {"query": task}, "id": f"{task}-{i}"}
                 for i in range(self.calls_per_task)]
        return AIMessage(content="", tool_calls=calls)


class FakeSearch:
    """Stands in for the `search_web` tool. Raises for `fail_on` queries."""

    def __init__(self, fail_on=()):
        self.fail_on = set(fail_on)
        self.queries = []

    def invoke(self, args):
        self.queries.append(args["query"])
        if args["query"] in self.fail_on:
            raise ConnectionError("Tavily is down")
        return f"Source: https://{args['query']}.example\nContent: about {args['query']}"


class FakeExtractor:
    """Returns one Finding per extraction, tagged with the branch's task."""

    def __init__(self, tasks):
        self.tasks = list(tasks)

    def invoke(self, prompt):
        task = task_of(_prompt_text(prompt), self.tasks)
        return Findings(findings=[Finding(finding=f"fact about {task}",
                                          source=f"https://{task}.example", evidence="e")])
