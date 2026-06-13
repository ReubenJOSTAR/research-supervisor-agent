# src/agents/extractor.py

from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from schemas.finding import Finding
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from config.settings import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY
)

class Findings(BaseModel):
    findings: list[Finding]

extractor_llm = llm.with_structured_output(Findings)

def extractor(state):
    # Get the raw tool results from messages
    tool_results = [
        m.content for m in state.get("messages", [])
        if isinstance(m, ToolMessage)
    ]
    
    if not tool_results:
        return Command(
            update={"findings": []},
            goto="supervisor"
        )
    
    raw_text = "\n\n".join(tool_results)
    
    result = extractor_llm.invoke(
        f"""Extract structured findings from these search results.
        
For each distinct finding, identify:
- The key finding or fact
- The source URL
- The supporting evidence

Search results:
{raw_text}"""
    )
    
    return Command(
        update={"findings": result.findings},
        goto="supervisor"
    )