from datetime import date
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import smtplib
import os
import base64
from bs4 import BeautifulSoup
import uuid

load_dotenv()


def extract_images_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = {}
    for img in soup.find_all('img'):
        if img.get('src', '').startswith('data:image'):
            img_data = img['src'].split(',')[1]
            img_type = img['src'].split(';')[0].split('/')[1]
            img_id = str(uuid.uuid4())
            images[img_id] = (img_data, img_type)
            img['src'] = f'cid:{img_id}'
    return str(soup), images


def create_email_with_images(message, html_content):
    # Extract images and update HTML
    updated_html, images = extract_images_from_html(html_content)

    # Attach HTML
    html_part = MIMEText(updated_html, "html")
    message.attach(html_part)

    # Attach images
    for img_id, (img_data, img_type) in images.items():
        image = MIMEImage(base64.b64decode(img_data), _subtype=img_type)
        image.add_header('Content-ID', f'<{img_id}>')
        image.add_header('Content-Disposition', 'inline', filename=f'{img_id}.{img_type}')
        message.attach(image)

    return message


def send_email(subject, html_content, hasimage=False):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"{subject} - {date.today()}"
    message["From"] = f"{os.getenv('SENDER_NAME')} <{os.getenv('SENDER_EMAIL')}>"
    message["To"] = os.getenv('RECIPIENT_EMAIL')
    # Create the HTML part of the message
    if hasimage:
        message = create_email_with_images(message, html_content)
    else:
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
    try:
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
            server.send_message(message)
        print("Email sent successfully")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
