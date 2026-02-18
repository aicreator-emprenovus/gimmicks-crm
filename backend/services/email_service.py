import os
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

async def send_po_email(to_email: str, subject: str, html_content: str, pdf_bytes: bytes, filename: str):
    email_provider = os.environ.get('EMAIL_PROVIDER', 'gmail').lower()
    if email_provider == 'gmail':
        return await send_via_gmail(to_email, subject, html_content, pdf_bytes, filename)
    else:
        return await send_via_resend(to_email, subject, html_content, pdf_bytes, filename)

async def send_via_gmail(to_email: str, subject: str, html_content: str, pdf_bytes: bytes, filename: str):
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_password = os.environ.get('GMAIL_PASSWORD')
    if not gmail_user or not gmail_password:
        logger.warning("Gmail credentials not found. Email not sent.")
        print(f"MOCK EMAIL to {to_email}: {subject}")
        return {"id": "mock-gmail-id"}
    try:
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(part)
        def send_email():
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_password.replace(' ', ''))
            server.sendmail(gmail_user, to_email, msg.as_string())
            server.quit()
            return True
        await asyncio.to_thread(send_email)
        logger.info(f"Email sent via Gmail to {to_email}")
        return {"id": "gmail-sent", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to send email via Gmail: {str(e)}")
        raise e

async def send_via_resend(to_email: str, subject: str, html_content: str, pdf_bytes: bytes, filename: str):
    try:
        import resend
    except ImportError:
        logger.warning("resend not installed. Mocking email.")
        print(f"MOCK EMAIL to {to_email}: {subject}")
        return {"id": "mock-email-id"}
    
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        logger.warning("RESEND_API_KEY not found. Mocking email send.")
        print(f"MOCK EMAIL to {to_email}: {subject}")
        return {"id": "mock-email-id"}
    resend.api_key = api_key
    sender = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
    content_list = list(pdf_bytes)
    params = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "attachments": [{"filename": filename, "content": content_list}]
    }
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email} with ID: {email.get('id')}")
        return email
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise e
