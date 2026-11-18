import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from typing import List, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_hostname = settings.smtp_hostname
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.mail_from = settings.mail_from
        self.mail_from_name = settings.mail_from_name
        self.frontend_url = settings.frontend_url

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """Send an email using SMTP."""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.mail_from_name} <{self.mail_from}>"
            message["To"] = to_email
            
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Build recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_hostname,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_user,
                password=self.smtp_password,
                recipients=recipients
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_password_reset_email(self, to_email: str, reset_token: str, user_name: str = "") -> bool:
        """Send password reset email."""
        reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"
        
        # HTML template
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset - Due Diligence Automation</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }
        .content {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }
        .button {
            display: inline-block;
            padding: 15px 30px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            font-size: 12px;
            color: #666;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Password Reset Request</h1>
        <p>Due Diligence Automation Platform</p>
    </div>
    
    <div class="content">
        <h2>Hello{% if user_name %} {{ user_name }}{% endif %}!</h2>
        
        <p>We received a request to reset your password for your Due Diligence Automation account.</p>
        
        <p>Click the button below to reset your password:</p>
        
        <a href="{{ reset_link }}" class="button">Reset My Password</a>
        
        <div class="warning">
            <p><strong>Important Security Information:</strong></p>
            <ul>
                <li>This link will expire in 24 hours</li>
                <li>If you didn't request this reset, please ignore this email</li>
                <li>Never share this link with anyone</li>
            </ul>
        </div>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px;">{{ reset_link }}</p>
        
        <p>If you have any questions or need assistance, please contact our support team.</p>
        
        <p>Best regards,<br>
        <strong>Due Diligence Automation Team</strong></p>
    </div>
    
    <div class="footer">
        <p>This is an automated message. Please do not reply to this email.</p>
        <p>© 2025 Due Diligence Automation Platform. All rights reserved.</p>
    </div>
</body>
</html>
        """)
        
        # Text template (fallback)
        text_template = Template("""
Password Reset Request - Due Diligence Automation

Hello{% if user_name %} {{ user_name }}{% endif %}!

We received a request to reset your password for your Due Diligence Automation account.

To reset your password, please visit the following link:
{{ reset_link }}

IMPORTANT SECURITY INFORMATION:
- This link will expire in 24 hours
- If you didn't request this reset, please ignore this email
- Never share this link with anyone

If you have any questions or need assistance, please contact our support team.

Best regards,
Due Diligence Automation Team

---
This is an automated message. Please do not reply to this email.
© 2025 Due Diligence Automation Platform. All rights reserved.
        """)

        html_content = html_template.render(
            reset_link=reset_link,
            user_name=user_name
        )
        
        text_content = text_template.render(
            reset_link=reset_link,
            user_name=user_name
        )

        return await self.send_email(
            to_email=to_email,
            subject="🔐 Password Reset Request - Due Diligence Automation",
            html_content=html_content,
            text_content=text_content
        )

# Create global email service instance
email_service = EmailService()