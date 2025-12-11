import uuid
import boto3
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

def string_to_pdf_unique_and_upload(
        text: str,
        folder_path: str = "",
        bucket_name: str = "",
        s3_folder: str = "",
        aws_access_key: str = "",
        aws_secret_key: str = "",
        aws_region: str = "ap-south-1"
    ):
    """
    Generate a uniquely named PDF from text and upload it to AWS S3.
    """

    # ========== Original PDF Generation (unchanged) ==========
    unique_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    Filename=f"Email_{unique_id}"
    pdf_path = f"{folder_path}Email_{unique_id}.pdf"

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    formatted_text = text.replace("\n", "<br/>")

    doc = SimpleDocTemplate(pdf_path)
    story = [Paragraph(formatted_text, normal_style)]
    doc.build(story)
    # =========================================================

    # ========== Added: Upload to S3 ==========
    s3_key = f"{s3_folder}Email_{unique_id}.pdf"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    s3.upload_file(pdf_path, bucket_name, s3_key)
    
    object_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"


    return {
        "local_pdf_path": pdf_path,
        "s3_bucket": bucket_name,
        "s3_key": s3_key,
        "object_url": object_url,
        "filename":Filename,
        "message": "PDF generated and uploaded successfully"
    }
