# src/tools/search.py

from langchain_core.tools import tool
from tavily import TavilyClient
import os

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

@tool
def search_web(query: str) -> str:
    """Search the web for current information on a topic.
    
    Args:
        query: The search query string
    """
    try:
        response = client.search(
            query=query,
            search_depth="advanced",   # basic or advanced
            max_results=5,
            include_answer=True,       # Tavily synthesizes an answer too
        )
        
        # Format results cleanly for the LLM
        results = []
        
        if response.get("answer"):
            results.append(f"Summary: {response['answer']}\n")
        
        for r in response.get("results", []):
            results.append(
                f"Source: {r['url']}\n"
                f"Title: {r['title']}\n"
                f"Content: {r['content']}\n"
            )
        
        return "\n---\n".join(results)
    
    except Exception as e:
        return f"Search failed: {str(e)}"