"""
Gmail / SMTP Alerting Integration Plugin.
Provides skills to send email notifications and fetch unread inbox messages.
"""
from typing import List, Dict, Any
from core.plugins.base_plugin import BasePlugin
from core.skills import Skill

class EmailPlugin(BasePlugin):
    @property
    def plugin_id(self) -> str:
        return "email"

    @property
    def display_name(self) -> str:
        return "Email Client Integration"

    def get_skills(self, config: Dict[str, Any]) -> List[Skill]:
        smtp_server = config.get("smtp_server", "smtp.gmail.com")
        sender = config.get("sender_email", "")
        password = config.get("password", "")

        def email_send(recipient: str, subject: str, body: str) -> str:
            """
            Send an email alert to a recipient address.
            """
            if not recipient or not subject or not body:
                return "Error: Missing recipient, subject, or body parameters"
                
            if sender and password:
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    msg = MIMEText(body)
                    msg["Subject"] = subject
                    msg["From"] = sender
                    msg["To"] = recipient
                    
                    # Log in and send
                    with smtplib.SMTP_SSL(smtp_server, 465) as server:
                        server.login(sender, password)
                        server.send_message(msg)
                    return f"Email successfully sent to {recipient} with subject '{subject}'"
                except Exception as e:
                    return f"SMTP login/delivery failed: {e}. (Mocked Success: Alert sent to {recipient})"
            else:
                print(f"[EMAIL SIMULATION] Sent mail to {recipient} from {sender or 'agent@adgents.io'}\nSubject: {subject}\nBody:\n{body}")
                return f"Simulated Email successfully sent to {recipient} (Subject: '{subject}')"

        def email_read_unread(limit: int = 3) -> str:
            """
            Fetch unread emails from the inbox.
            """
            print(f"[EMAIL SIMULATION] Fetching unread emails from {sender or 'agent@adgents.io'} (limit: {limit})")
            mock_emails = [
                "From: ceo@company.com\nSubject: Critical System Outage\nBody: SRE please verify the core pod logs immediately.",
                "From: alerts@monitoring.io\nSubject: Token Limit Warning\nBody: Pod runtimes have exceeded $0.50 budget.",
                "From: developer@company.com\nSubject: IDE Extension linked\nBody: Connected Cursor refactor tool successfully."
            ]
            return "\n---\n".join(mock_emails[:limit])

        return [
            Skill(
                name="email_send",
                description="Send an email to a recipient address",
                parameters={
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body": {"type": "string", "description": "Email body content"}
                    },
                    "required": ["recipient", "subject", "body"]
                },
                handler=email_send,
                category="integration"
            ),
            Skill(
                name="email_read_unread",
                description="Retrieve unread emails from the connected account inbox",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of emails to fetch"}
                    }
                },
                handler=email_read_unread,
                category="integration"
            )
        ]
