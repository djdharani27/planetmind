"""Pydantic tool models and implementations for the ReAct agent."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from backend.search.hybrid_search import hybrid_search, quick_search


# ── Input/Output Schemas ──

class SearchInput(BaseModel):
    """Input schema for the document search tool."""
    query: str = Field(description="The search query to find relevant documents.")
    top_k: int = Field(default=10, description="Number of results to retrieve.", ge=1, le=50)


class SearchResultItem(BaseModel):
    """A single search result from the document repository."""
    document_id: str
    filename: str
    snippet: str
    page_number: int | None = None
    score: float = 0.0
    source: str = "vector"


class SearchOutput(BaseModel):
    """Output schema for the document search tool."""
    results: list[SearchResultItem]
    total: int
    query: str


# ── Tool Definition ──

class Tool:
    """A callable tool with a Pydantic schema for OpenAI function calling."""

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: type[BaseModel],
        fn: callable,
    ):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.fn = fn

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI function-calling tool format."""
        schema = self.args_schema.model_json_schema()
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Remove pydantic metadata fields from schema
        clean_properties = {}
        for key, val in properties.items():
            cleaned = {k: v for k, v in val.items() if k in {"type", "description", "items", "enum", "default"}}
            if "default" in val:
                cleaned.pop("default", None)
            clean_properties[key] = cleaned

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": clean_properties,
                    "required": required,
                },
            },
        }

    async def run(self, **kwargs) -> Any:
        validated = self.args_schema(**kwargs)
        return self.fn(**validated.model_dump())


# ── Tool Implementations ──

def _search_documents(query: str, top_k: int = 10) -> SearchOutput:
    """Run hybrid search and return structured results."""
    raw = hybrid_search(query, top_k=top_k)
    results_raw = raw.get("results", [])
    items = []
    for r in results_raw:
        items.append(SearchResultItem(
            document_id=r.get("document_id", ""),
            filename=r.get("filename", r.get("document_id", "")),
            snippet=r.get("snippet", "")[:500],
            page_number=r.get("page_number"),
            score=r.get("rerank_score", r.get("score", 0)),
            source=r.get("source", "vector"),
        ))
    return SearchOutput(results=items, total=len(items), query=query)


def _quick_search_docs(query: str, top_k: int = 5) -> SearchOutput:
    """Run lightweight quick search (vector-only, faster)."""
    raw = quick_search(query, top_k=top_k)
    results_raw = raw.get("results", [])
    items = []
    for r in results_raw:
        items.append(SearchResultItem(
            document_id=r.get("document_id", ""),
            filename=r.get("filename", r.get("document_id", "")),
            snippet=r.get("snippet", "")[:500],
            page_number=r.get("page_number"),
            score=r.get("rerank_score", r.get("score", 0)),
            source=r.get("source", "vector"),
        ))
    return SearchOutput(results=items, total=len(items), query=query)


# ── Registry ──

SEARCH_TOOL = Tool(
    name="search_documents",
    description="Search through the company's document repository to find information relevant to the user's question. "
                "Returns document snippets with source references. Use this for any factual question.",
    args_schema=SearchInput,
    fn=_search_documents,
)

QUICK_SEARCH_TOOL = Tool(
    name="quick_search",
    description="Fast lightweight search through documents. Use for quick lookups when you need speed over thoroughness.",
    args_schema=SearchInput,
    fn=_quick_search_docs,
)

ALL_TOOLS: list[Tool] = [SEARCH_TOOL, QUICK_SEARCH_TOOL]


def get_openai_tools() -> list[dict]:
    """Get all tool definitions in OpenAI format."""
    return [t.to_openai_tool() for t in ALL_TOOLS]


def get_tool_by_name(name: str) -> Tool | None:
    """Look up a tool by name."""
    for t in ALL_TOOLS:
        if t.name == name:
            return t
    return None
