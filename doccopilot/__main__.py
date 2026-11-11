"""Terminal chat:  python -m doccopilot"""
import uuid

from langgraph.types import Command

from .graph import build_graph
from .steps import JsonLLM


def main():
    graph = build_graph(JsonLLM())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    request = input("What document do you need?\n> ")
    result = graph.invoke({"conversation": [request]}, config)
    while "__interrupt__" in result:
        print("\n" + result["__interrupt__"][0].value["question"])
        result = graph.invoke(Command(resume=input("> ")), config)
    print("\n" + result.get("message", ""))


if __name__ == "__main__":
    main()
