import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from dotenv import load_dotenv

load_dotenv()


def send_email(html_content):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Shop-Ware Daily Report - {date.today()}"
    message["From"] = f"{os.getenv('SENDER_NAME')} <{os.getenv('SENDER_EMAIL')}>"
    message["To"] = os.getenv('RECIPIENT_EMAIL')
    # Create the HTML part of the message
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)

    try:
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
            server.sendmail(os.getenv('SENDER_EMAIL'), os.getenv('RECIPIENT_EMAIL'), message.as_string())
        print("Email sent successfully")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
