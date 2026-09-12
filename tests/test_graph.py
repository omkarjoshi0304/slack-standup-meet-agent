from langchain_core.messages import HumanMessage

from agent.graph import graph


def test_echo_node_prefixes_the_last_message():
    config = {"configurable": {"thread_id": "test-thread"}}
    result = graph.invoke({"messages": [HumanMessage(content="hello")]}, config)

    last_message = result["messages"][-1]

    assert last_message.content == "echo: hello"
