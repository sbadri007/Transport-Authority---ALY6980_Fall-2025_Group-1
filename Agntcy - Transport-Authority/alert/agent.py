# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import TypedDict
import requests
import os 

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from ioa_observe.sdk.decorators import agent, graph

from common.llm import get_llm

logger = logging.getLogger("mbta.alert_agent.graph")

class State(TypedDict):
    prompt: str
    error_type: str
    error_message: str
    alert_notes: str

@agent(name="alert_agent")
class AlertAgent:
    def __init__(self):
        self.ALERT_NODE = "AlertNode"
        self._agent = self.build_graph()

    @graph(name="alert_graph")
    def build_graph(self) -> StateGraph:
        graph_builder = StateGraph(State)
        graph_builder.add_node(self.ALERT_NODE, self.alert_node)
        graph_builder.add_edge(START, self.ALERT_NODE)
        graph_builder.add_edge(self.ALERT_NODE, END)
        return graph_builder.compile()

    async def alert_node(self, state: State):
        """Fetch and format MBTA alerts."""
        user_prompt = state.get("prompt")
        logger.debug(f"Received user prompt: {user_prompt}")
        
        # Extract route from prompt using LLM
        system_prompt = (
            "Extract the MBTA route from this query if mentioned. "
            "Routes: Red, Orange, Blue, Green, Green-B, Green-C, Green-D, Green-E. "
            "Respond with ONLY the route name or 'none' if not specified."
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = get_llm().invoke(messages)
        route = response.content.strip()
        route = None if route.lower() == 'none' else route
        
        # Fetch alerts from MBTA API
        try:
            mbta_key = os.getenv("MBTA_API_KEY")
            if not mbta_key:
                return {
                    "error_type": "config_error",
                    "error_message": "MBTA_API_KEY not configured"
                }
            
            params = {
                "api_key": mbta_key,
                "sort": "-updated_at",
                "page[limit]": "5",
                "filter[lifecycle]": "NEW,ONGOING,UPDATE"
            }
            
            if route:
                params["filter[route]"] = route
            
            logger.info(f"Fetching alerts for route: {route}")
            
            r = requests.get(
                "https://api-v3.mbta.com/alerts",
                params=params,
                timeout=10
            )
            r.raise_for_status()
            
            data = r.json()
            alerts = data.get("data", [])
            
            if not alerts:
                alert_text = f"No current alerts for {route}." if route else "No current alerts."
                return {"alert_notes": alert_text}
            
            # Format alerts with LLM
            alert_summaries = []
            for alert in alerts[:3]:
                attrs = alert.get("attributes", {})
                alert_summaries.append({
                    "header": attrs.get("header", ""),
                    "severity": attrs.get("severity", ""),
                    "effect": attrs.get("effect", "")
                })
            
            format_prompt = (
                f"Format these MBTA alerts concisely for riders:\n"
                f"{alert_summaries}\n"
                f"Route: {route or 'all lines'}\n"
                f"Provide a brief, helpful summary."
            )
            
            messages = [
                SystemMessage(content="You are an MBTA service assistant."),
                HumanMessage(content=format_prompt)
            ]
            formatted = get_llm().invoke(messages)
            
            return {"alert_notes": formatted.content}
            
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return {
                "error_type": "api_error",
                "error_message": f"Error getting alerts: {str(e)}"
            }

    async def ainvoke(self, input: str) -> dict:
        """
        Sends a user input string to the agent asynchronously and returns the result.

        Args:
            input (str): A user prompt describing MBTA alerts/delays/service status.

        Returns:
            dict: A response dictionary, typically containing either:
                - "alert_notes" with the LLM's generated profile, or
                - An error message if parsing or context extraction failed.
        """
        # build graph if not already built
        if not hasattr(self, '_agent'):
            self._agent = self.build_graph()
        return await self._agent.ainvoke({"prompt": input})