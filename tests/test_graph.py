import asyncio

from ag_ui_langgraph import CustomEventNames
from langchain_core.messages import HumanMessage

from agent.graph import graph

# The graph's nodes are async because emitting a streamable reply dispatches a
# LangChain custom event, so the tests drive it with asyncio.run rather than
# taking a pytest-asyncio dependency for two cases.


def test_echo_node_prefixes_the_last_message():
    config = {"configurable": {"thread_id": "test-thread"}}
    result = asyncio.run(
        graph.ainvoke({"messages": [HumanMessage(content="hello")]}, config)
    )

    last_message = result["messages"][-1]

    assert last_message.content == "echo: hello"


def test_reply_is_emitted_as_a_streamable_message():
    """A state-only reply is invisible to chat surfaces.

    CopilotKit's Slack renderer renders TEXT_MESSAGE_* events and ignores
    MESSAGES_SNAPSHOT, so a node that only writes an AIMessage into state gets
    delivered as an empty message and posts nothing. `ag_ui_langgraph` turns this
    custom event into the TEXT_MESSAGE_START/CONTENT/END triple.
    """

    async def collect_manual_emits():
        config = {"configurable": {"thread_id": "test-thread-stream"}}
        return [
            event
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content="hello")]}, config
            )
            if event["event"] == "on_custom_event"
            and event["name"] == CustomEventNames.ManuallyEmitMessage.value
        ]

    emitted = asyncio.run(collect_manual_emits())

    assert len(emitted) == 1
    assert emitted[0]["data"]["message"] == "echo: hello"
    assert emitted[0]["data"]["message_id"]
