import uuid
import boto3
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from PyPDF2 import PdfMerger
import os

def string_to_pdf_unique_and_upload(
        text: str,
        attachments: list,            # << NEW
        folder_path: str = "",
        bucket_name: str = "",
        s3_folder: str = "",
        aws_access_key: str = "",
        aws_secret_key: str = "",
        aws_region: str = "ap-south-1"
    ):
    """
    Generate a uniquely named PDF from email text,
    merge it with PDF attachments, and upload to AWS S3.
    """

    # --- Create main email PDF ---
    unique_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base_filename = f"Email_{unique_id}"
    pdf_path = f"{folder_path}{base_filename}.pdf"

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    formatted_text = text.replace("\n", "<br/>")

    doc = SimpleDocTemplate(pdf_path)
    story = [Paragraph(formatted_text, normal_style)]
    doc.build(story)

    # --- Prepare merged output path ---
    merged_pdf_path = f"{folder_path}{base_filename}_merged.pdf"

    merger = PdfMerger()

    # Add the generated email PDF first
    merger.append(pdf_path)

    # Merge email attachments if they are PDFs
    for file in attachments:
        if file.lower().endswith(".pdf"):
            merger.append(file)

    merger.write(merged_pdf_path)
    merger.close()

    # --- Upload merged PDF to S3 ---
    s3_key = f"{s3_folder}{base_filename}_merged.pdf"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    s3.upload_file(merged_pdf_path, bucket_name, s3_key)

    object_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"

    return {
        "local_pdf_path": merged_pdf_path,
        "s3_bucket": bucket_name,
        "s3_key": s3_key,
        "object_url": object_url,
        "filename": f"{base_filename}_merged",
        "message": "Merged PDF generated and uploaded successfully"
    }