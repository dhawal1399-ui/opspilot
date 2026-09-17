from app.services.agent_service import AgentService
from app.services.confirmation_service import ConfirmationService


def test_create_ticket_requires_confirmation():
    confirmation_service = ConfirmationService()
    agent = AgentService(
        confirmation_service=confirmation_service
    )

    token = agent.request_confirmation(
        tool_name="create_ticket",
        arguments={
            "customer_id": 1024,
            "title": "Payment failure",
            "description": "Payment failed.",
        },
    )

    pending = confirmation_service.get(token)

    assert pending is not None
    assert pending["tool_name"] == "create_ticket"


def test_update_ticket_requires_confirmation():
    confirmation_service = ConfirmationService()
    agent = AgentService(
        confirmation_service=confirmation_service
    )

    token = agent.request_confirmation(
        tool_name="update_ticket",
        arguments={
            "ticket_id": 5001,
            "status": "resolved",
        },
    )

    pending = confirmation_service.get(token)

    assert pending is not None
    assert pending["tool_name"] == "update_ticket"


def test_confirmation_token_is_one_time_use():
    confirmation_service = ConfirmationService()

    token = confirmation_service.create(
        tool_name="update_ticket",
        arguments={
            "ticket_id": 5001,
            "status": "resolved",
        },
    )

    first = confirmation_service.consume(token)
    second = confirmation_service.consume(token)

    assert first is not None
    assert second is None


def test_destructive_tools_are_blocked():
    agent = AgentService(
        confirmation_service=ConfirmationService()
    )

    assert agent.is_destructive_tool("delete_ticket") is True
    assert agent.is_destructive_tool("delete_customer") is True
    assert agent.is_destructive_tool("remove_ticket") is True
    assert agent.is_destructive_tool("drop_database") is True
    assert agent.is_destructive_tool("truncate_logs") is True
    assert agent.is_destructive_tool("get_ticket") is False