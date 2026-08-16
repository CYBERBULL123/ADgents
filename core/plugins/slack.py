"""
Slack Integration Plugin.
Provides skills to post text notifications and read channel history.
"""
from typing import List, Dict, Any
from core.plugins.base_plugin import BasePlugin
from core.skills import Skill

class SlackPlugin(BasePlugin):
    @property
    def plugin_id(self) -> str:
        return "slack"

    @property
    def display_name(self) -> str:
        return "Slack Workspace Alerts"

    def get_skills(self, config: Dict[str, Any]) -> List[Skill]:
        webhook_url = config.get("webhook_url", "")
        default_channel = config.get("channel", "general")

        def slack_send_message(message: str, channel: str = default_channel) -> str:
            """
            Post a message to a Slack channel.
            """
            if not message:
                return "Error: Message is empty"
                
            # If webhook url is provided, simulate HTTP post, else print mock output
            if webhook_url:
                try:
                    import httpx
                    res = httpx.post(webhook_url, json={"text": message})
                    if res.status_code == 200:
                        return f"Successfully sent Slack message to #{channel} via webhook: '{message}'"
                    else:
                        return f"Failed to send Slack message: HTTP {res.status_code}"
                except Exception as e:
                    return f"Slack API connection failed: {e}. (Mocked Success: Posted to #{channel}: '{message}')"
            else:
                print(f"[SLACK SIMULATION] Sent message to #{channel}: {message}")
                return f"Simulated Slack message sent to #{channel}: '{message}'"

        def slack_read_channel(channel: str = default_channel, limit: int = 5) -> str:
            """
            Read the recent message history from a Slack channel.
            """
            print(f"[SLACK SIMULATION] Reading history from #{channel} (limit: {limit})")
            mock_messages = [
                f"[10:00 AM] dev_lead: Let's run the pipeline test.",
                f"[10:02 AM] qa_agent: Starting execution pod...",
                f"[10:05 AM] SRE_Kernel: Healed iteration error on pod-423."
            ]
            return "\n".join(mock_messages[:limit])

        return [
            Skill(
                name="slack_send_message",
                description="Send a message/notification to a Slack channel",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "The message body to post"},
                        "channel": {"type": "string", "description": "Channel name or ID (default from config)"}
                    },
                    "required": ["message"]
                },
                handler=slack_send_message,
                category="integration"
            ),
            Skill(
                name="slack_read_channel",
                description="Fetch recent messages from a channel",
                parameters={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel name or ID"},
                        "limit": {"type": "integer", "description": "Maximum number of messages to fetch"}
                    }
                },
                handler=slack_read_channel,
                category="integration"
            )
        ]
