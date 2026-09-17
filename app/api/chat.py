import logging
import uuid

from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.confirmation_service import ConfirmationService


logger = logging.getLogger(__name__)
router = APIRouter()

confirmation_service = ConfirmationService()


@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest) -> ChatResponse:
    request_id = f"req-{uuid.uuid4()}"

    # ---------------------------------------------------------
    # Handle explicit confirmation
    # ---------------------------------------------------------

    if chat_request.confirmation:
        if not chat_request.confirmation_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "request_id": request_id,
                    "error": (
                        "Confirmation token is required."
                    ),
                },
            )

        pending_action = confirmation_service.get(
            chat_request.confirmation_token
        )

        if pending_action is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "request_id": request_id,
                    "error": (
                        "Invalid or expired confirmation token."
                    ),
                },
            )

        if pending_action["tool_name"] not in {
            "create_ticket",
            "update_ticket",
        }:
            raise HTTPException(
                status_code=400,
                detail={
                    "request_id": request_id,
                    "error": "Unsupported confirmation action.",
                },
            )

        # Consume the token BEFORE executing the write.
        # This makes the confirmation one-time-use.
        pending_action = confirmation_service.consume(
            chat_request.confirmation_token
        )

        if pending_action is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "request_id": request_id,
                    "error": (
                        "Confirmation token is no longer valid."
                    ),
                },
            )

        agent = AgentService(
            confirmation_service=confirmation_service
        )

        try:
            await agent.connect()

            result = await agent.execute_tool(
                tool_name=pending_action["tool_name"],
                arguments=pending_action["arguments"],
                confirmed=True,
            )

        except Exception as exc:
            logger.exception(
                "Confirmed ticket creation failed "
                "for request_id=%s",
                request_id,
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "request_id": request_id,
                    "error": (
                        "Unable to create the ticket."
                    ),
                },
            ) from exc

        finally:
            await agent.disconnect()

        if (
            isinstance(result, dict)
            and result.get("success") is False
        ):
            return ChatResponse(
                request_id=request_id,
                answer="The ticket could not be created.",
                evidence=[],
                tools_used=["create_ticket"],
            )


        tool_name = pending_action["tool_name"]

        if tool_name == "create_ticket":
            success_message = "The ticket was created successfully."
        else:
            success_message = "The ticket was updated successfully."

        return ChatResponse(
            request_id=request_id,
            answer=success_message,
            evidence=[
                {
                    "tool": tool_name,
                    "data": (
                        result.get("data")
                        if isinstance(result, dict)
                        else result
                    ),
                }
            ],
            tools_used=[tool_name],
        )

    # ---------------------------------------------------------
    # Normal investigation flow
    # ---------------------------------------------------------

    try:
        try:
            agent = AgentService(
                confirmation_service=confirmation_service
            )
        except TypeError:
            agent = AgentService()

        answer = await agent.investigate(
            chat_request.question
        )

        if (
            isinstance(answer, dict)
            and answer.get("confirmation_required")
        ):
            return ChatResponse(
                request_id=request_id,
                answer=(
                    f"Confirmation required to execute "
                    f"'{answer['tool']}'."
                ),
                evidence=[],
                tools_used=[],
                confirmation_required=True,
                confirmation_token=answer[
                    "confirmation_token"
                ],
            )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Chat investigation failed for request_id=%s",
            request_id,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "error": (
                    "Unable to complete the investigation."
                ),
            },
        ) from exc

    evidence = [
        {
            "tool": result["tool"],
            "data": result["data"],
        }
        for result in agent.last_tool_results
        if result.get("success") is True
    ]

    return ChatResponse(
        request_id=request_id,
        answer=answer,
        evidence=evidence,
        tools_used=list(agent.last_tools_used),
    )