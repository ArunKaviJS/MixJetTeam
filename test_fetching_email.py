import os
import imaplib
import email
from email.header import decode_header


def fetch_latest_mbd_emirates_attachments():
    """
    Fetch ALL PDF attachments from the latest email
    whose subject contains 'mbd emirates' (case-insensitive)

    Returns:
    [
        {
            "filename": "document.pdf",
            "bytes": b"..."
        }
    ]
    """

    IMAP_SERVER = os.getenv("IMAP_SERVER")
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

    if not all([IMAP_SERVER, EMAIL_USER, EMAIL_PASS]):
        raise ValueError("Missing IMAP environment variables")

    print("📧 Connecting to IMAP server...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()

    if not email_ids:
        raise Exception("No emails found in inbox")

    # Traverse from latest to oldest
    for email_id in reversed(email_ids):
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        # Decode subject
        subject = ""
        for part, enc in decode_header(msg.get("Subject", "")):
            if isinstance(part, bytes):
                subject += part.decode(enc or "utf-8", errors="ignore")
            else:
                subject += part

        print(f"🔍 Checking subject: {subject}")

        if "mbd emirates" not in subject.lower():
            continue

        print(f"✅ Matched subject: {subject}")

        attachments = []

        for part in msg.walk():
            content_disposition = part.get("Content-Disposition", "")
            if "attachment" in content_disposition.lower():
                filename = part.get_filename()
                if filename:
                    decoded_name, _ = decode_header(filename)[0]
                    if isinstance(decoded_name, bytes):
                        decoded_name = decoded_name.decode(errors="ignore")

                    if decoded_name.lower().endswith(".pdf"):
                        attachments.append({
                            "filename": decoded_name,
                            "bytes": part.get_payload(decode=True)
                        })

        if not attachments:
            raise Exception("Matched email found but no PDF attachments")

        print(f"📎 Found {len(attachments)} PDF attachment(s)")
        return attachments

    raise Exception("No email found with subject containing 'mbd emirates'")


# ===============================
# 🔎 TEST THIS FILE DIRECTLY
# ===============================
if __name__ == "__main__":
    files = fetch_latest_mbd_emirates_attachments()

    for f in files:
        print(f"📄 Attachment: {f['filename']} | Size: {len(f['bytes'])} bytes")
