import os
from uuid import uuid4
from dotenv import load_dotenv
from pymongo import MongoClient
import json
from bson import ObjectId
from datetime import datetime,timezone

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
FILE_DETAILS = os.getenv("FILE_DETAILS")   # collection name

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[FILE_DETAILS]

# -------------------------------------------------------
# NORMALIZER → Ensures nested table stored as real object
# -------------------------------------------------------
def normalize_structured_data(structured, full_text=""):
    """Normalize extracted structured data before Mongo insert."""

    # If structured is JSON string → convert to dict
    if isinstance(structured, str):
        structured = json.loads(structured)

    if not isinstance(structured, dict):
        raise ValueError("structured must be a dict")

    normalized_results = {}

    for key, value in structured.items():

        # 1. Simple field
        if isinstance(value, str) or value is None:
            normalized_results[key] = value or ""

        # 2. Table field
        elif isinstance(value, dict) and value.get("fieldType") == "table":

            items = []
            raw_items = value.get("items", [])

            if isinstance(raw_items, list):
                for row in raw_items:
                    if not isinstance(row, dict):
                        continue

                    clean_row = {
                        k: ("" if v is None else v)
                        for k, v in row.items()
                    }
                    items.append(clean_row)

            normalized_results[key] = {
                "fieldType": "table",
                "items": items  # << REAL OBJECT, NOT JSON STRING
            }

        # 3. Unexpected types → store raw dict/list
        elif isinstance(value, (dict, list)):
            normalized_results[key] = value

        # 4. Fallback
        else:
            normalized_results[key] = value

    # Clean full text
    if not isinstance(full_text, str):
        try:
            full_text = json.dumps(full_text, ensure_ascii=False)
        except:
            full_text = str(full_text)

    return normalized_results, full_text


# -------------------------------------------------------
# MONGO STORE FUNCTION
# -------------------------------------------------------
def store_structured_in_mongo(structured,object_url,filename,originalS3File,email_text=""):
    """Store normalized structured data into MongoDB with unique ID."""

    normalized_structured, cleaned_text = normalize_structured_data(
        structured, email_text
    )

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[FILE_DETAILS]

    doc = {
        "_id": ObjectId(), # create unique ID
        "clusterId":ObjectId("693901f09d8dbf36a427bd91"),
        "userId":ObjectId("6938fd609d8dbf36a427bd6d"),
        "status":"1",
        "fileName":filename ,
        "processingStatus":"Completed" ,
        "originalS3File":originalS3File,
        "originalFile":object_url ,
        "extractedValues": normalized_structured,  # REAL nested object
        "updatedExtractedValues":normalized_structured,
        "credits":"null",
        "createdAt":datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        
    }

    collection.insert_one(doc)

    return str(doc["_id"])