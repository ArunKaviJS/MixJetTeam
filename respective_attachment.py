import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
from azure_llm_agent import extract_structured_email_data
from gmailmongo import store_structured_in_mongo
from texttopdf import string_to_pdf_unique_and_upload
import time

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

AWS_ACCESS_KEY=os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY=os.getenv("AWS_SECRET_KEY")
REGION=os.getenv("REGION")

os.makedirs("attachments", exist_ok=True)

def decode_text(raw):
    if raw is None:
        return ""
    text, enc = decode_header(raw)[0]
    if isinstance(text, bytes):
        return text.decode(enc or "utf-8", errors="ignore")
    return text

def get_email_body_and_attachments(msg):
    body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            # Extract body
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                except:
                    pass

            # Extract attachments
            if part.get("Content-Disposition"):
                filename = part.get_filename()
                if filename:
                    filename = decode_text(filename)
                    file_path = os.path.join("attachments", filename)

                    with open(file_path, "wb") as f:
                        f.write(part.get_payload(decode=True))

                    attachments.append(file_path)
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    return body, attachments

def fetch_unread_Approlabs_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    print("Fetching unread emails containing: Permit Request...\n")

    status, messages = mail.search(None, "(UNSEEN)")
    email_ids = messages[0].split()

    result_output = ""

    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        from_email = msg.get("From")
        subject = decode_text(msg.get("Subject")).strip()

        # ⭐ Check if subject *contains* the phrase "Email Content"
        if "permit request" not in subject.lower():
            continue

        body, attachments = get_email_body_and_attachments(msg)

        # mark as read
        mail.store(email_id, "+FLAGS", "\\Seen")

        block = f"""

From: {from_email}
Subject: {subject}
Message:
{body}

Attachments:
{attachments}
----------------------------------------
"""
        result_output += block

    return result_output


def extract_message_content(full_output: str) -> str:
    """
    Extracts only the message body between 'Message:' and 'Attachments:' 
    from the email fetch output.
    """
    # Normalize line endings
    text = full_output.replace("\r", "")

    # Look for start and end markers
    start_marker = "Message:"
    end_marker = "Attachments:"

    # Find positions
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return ""  # Message not found
    
    # Move index to after 'Message:'
    start_idx += len(start_marker)

    end_idx = text.find(end_marker, start_idx)
    if end_idx == -1:
        # If no attachment block, take text till end
        message_content = text[start_idx:].strip()
    else:
        message_content = text[start_idx:end_idx].strip()

    return message_content


def live_email_listener():
    print("\n🔄 Live Email Listener Started... Waiting for new mails...\n")

    while True:
        try:
            output = fetch_unread_Approlabs_emails()

            # If empty → no new Approlabs emails, continue waiting
            if not output.strip():
                time.sleep(5)
                continue

            print("\n📥 NEW EMAIL(S) RECEIVED:\n")
            print(output)

            # Extract only the message part
            message_content = extract_message_content(output)
            print("📄 Extracted Message:")
            print(message_content)

            # Upload PDF
            result = string_to_pdf_unique_and_upload(
                text=output,
                folder_path="gmail_pdfs/",
                bucket_name="yc-retails-invoice",
                s3_folder="uploads/",
                aws_access_key=AWS_ACCESS_KEY,
                aws_secret_key=AWS_SECRET_KEY,
                aws_region="ap-south-1"
            )
            
            local_path = result["local_pdf_path"]
            bucket = result["s3_bucket"]
            s3_key = result["s3_key"]
            object_url = result["object_url"]
            filename = result["filename"]
            message = result["message"]

            # LLM Processing
            structured = extract_structured_email_data(message_content)
            print("🤖 LLM Output:")
            print(structured)

            # MongoDB Store
            id = store_structured_in_mongo(structured,object_url,filename,s3_key)
            print("💾 Stored with ID:", id)

        except Exception as e:
            print(f"❌ Error: {e}")

        # Check inbox every 5 seconds
        time.sleep(5)


if __name__ == "__main__":
    live_email_listener()