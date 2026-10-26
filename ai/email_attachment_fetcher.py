import os
import imaplib
import email
from email.header import decode_header


class EmailAttachmentFetcher:
    def __init__(self):
        self.imap_server = os.getenv("IMAP_SERVER")
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")

        if not all([self.imap_server, self.email_user, self.email_pass]):
            raise ValueError("IMAP credentials missing in environment variables")

    def _decode_subject(self, raw_subject: str) -> str:
        if not raw_subject:
            return ""
        decoded_parts = decode_header(raw_subject)
        subject = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                subject += part
        return subject.strip()

    def fetch_pdf_with_subject(self, subject_keyword: str) -> bytes:
        """
        Fetch latest PDF attachment from emails
        whose subject contains `subject_keyword` (case-insensitive)
        """

        print("📧 Connecting to IMAP server...")
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_user, self.email_pass)
        mail.select("inbox")

        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        if not email_ids:
            raise Exception("No emails found in inbox")

        # Traverse from latest to oldest
        for email_id in reversed(email_ids):
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subject = self._decode_subject(msg.get("Subject", ""))
            print(f"🔍 Checking email subject: {subject}")

            if subject_keyword.lower() not in subject.lower():
                continue

            print(f"✅ Matched subject: {subject}")

            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition.lower():
                    filename = part.get_filename()
                    if filename:
                        decoded_name, _ = decode_header(filename)[0]
                        if isinstance(decoded_name, bytes):
                            decoded_name = decoded_name.decode(errors="ignore")

                        if decoded_name.lower().endswith(".pdf"):
                            print(f"📎 PDF attachment found: {decoded_name}")
                            return part.get_payload(decode=True)

            raise Exception("Matched email found but no PDF attachment")

        raise Exception(f"No email found with subject containing '{subject_keyword}'")
