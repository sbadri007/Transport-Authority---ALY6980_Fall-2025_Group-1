# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from uuid import uuid4

from ioa_observe.sdk.decorators import agent
from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from config.config import DEFAULT_MESSAGE_TRANSPORT, TRANSPORT_SERVER_ENDPOINT
from langchain_core.messages import HumanMessage, SystemMessage
from common.llm import get_llm
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
)

from alert.card import AGENT_CARD as alert_agent_card

logger = logging.getLogger("mbta.exchange.agent")

tools = [
    {
        "name": "a2a_client_send_message",
        "description": "Processes relevant user prompts and returns a response",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user prompt to process"
                }
            },
            "required": ["prompt"]
        }
    }
]

system_prompt = (
    "You are a routing assistant for MBTA transit queries. "
    "For ANY question about MBTA service, alerts, delays, or transit status, "
    "you MUST call the a2a_client_send_message tool with the user's prompt. "
    "Do NOT answer directly - ALWAYS use the tool for MBTA questions. "
    "Only respond directly if the query is completely unrelated to transit."
)


@agent(name="exchange_agent")
class ExchangeAgent:
    def __init__(self, factory: AgntcyFactory):
        self.factory = factory

    async def execute_agent_with_llm(self, user_prompt: str):
        """
        Processes a user prompt using the LLM to determine if the prompt is relevant to MBTA alerts/delays/service status.
        If relevant, calls the a2a_client_send_message with the prompt. Otherwise, responds with 'I'm sorry, I cannot assist with that request. Please ask about MBTA alerts/delays/service status.'

        Args:
            user_prompt (str): The user prompt to process.

        Returns:
            str: The response from the LLM or the tool if called.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # Invoke LLM WITHOUT binding - pass tools directly in kwargs
        response = get_llm().invoke(messages, tools=tools)

        # Check if tool was called
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info("Tool was called!")
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                logger.info(f"Tool: {tool_name}")
                logger.info(f"Arguments: {tool_args}")

                # Manual local routing to the tool
                if tool_name == "a2a_client_send_message":
                    result = await self.a2a_client_send_message(tool_args["prompt"])
                    logger.info(f"Tool Result: {result}")
                    return result
        else:
            logger.info("No tool called - LLM responded directly")
            return response.content

    async def a2a_client_send_message(self, prompt: str):
        """
        Send the user-provided prompt to the alert agent over A2A.
        """
        logger.info("Sending prompt to alert agent")
        
        import httpx
        from a2a.client import A2AClient
        from config.config import ALERT_AGENT_HOST, ALERT_AGENT_PORT
        
        # Build the message request
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message=Message(
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(root=TextPart(text=prompt))],
                )
            )
        )
        
        try:
            # Create httpx client
            async with httpx.AsyncClient(timeout=60.0) as http_client:
                # Connect directly to alert server
                alert_url = f"http://{ALERT_AGENT_HOST}:{ALERT_AGENT_PORT}"
                
                logger.info(f"Sending to alert URL: {alert_url}")
                
                # Create A2A client
                a2a_client = A2AClient(
                    httpx_client=http_client,
                    agent_card=alert_agent_card,
                    url=alert_url
                )
                
# Send message
                result = await a2a_client.send_message(request)
                
                logger.info(f"Got response from alert")
                
                # Extract response - it's in root.result.parts
                if hasattr(result, 'root') and hasattr(result.root, 'result'):
                    message = result.root.result
                    parts = message.parts
                    if parts and hasattr(parts[0], 'root') and hasattr(parts[0].root, 'text'):
                        return parts[0].root.text
                
                return "No valid response format"
                
        except Exception as e:
            logger.error(f"Error communicating with alert agent: {e}", exc_info=True)
            return f"Error: {str(e)}"
