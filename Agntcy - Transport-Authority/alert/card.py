# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill)

from config.config import ALERT_AGENT_HOST, ALERT_AGENT_PORT

AGENT_SKILL = AgentSkill(
    id="get_alerts",
    name="Get MBTA Alerts",
    description="Returns current MBTA service alerts and disruptions.",
    tags=["mbta", "transit", "alerts", "service"],
    examples=[
        "Are there any delays on the Red Line?",
        "What's the service status on the Green Line?",
        "Show me all current MBTA alerts",
        "Is there construction on the Orange Line?",
    ]
)

AGENT_CARD = AgentCard(
    name='MBTA Alerts Service',
    id='mbta-alerts-agent',
    description='An AI agent that provides real-time MBTA service alerts and disruptions.',
    url='',
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[AGENT_SKILL],
    supportsAuthenticatedExtendedCard=False,
)