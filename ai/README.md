# ai

Email → LLM extraction → PDF → S3 → MongoDB pipeline (unchanged; just moved into
its own folder). Downstream, [`../awery-backend`](../awery-backend) reads the
`extractedValues` this writes to Mongo and pushes it to Awery ERP.

```
main.py                    live IMAP listener + orchestration
azure_llm_agent.py         Azure OpenAI prompt + extract_structured_email_data()
gmailmongo.py              normalise + store_structured_in_mongo()
texttopdf.py               build merged PDF + upload to S3
email_attachment_fetcher.py / test_fetching_email.py   IMAP helpers
```

## Run

```bash
cd ai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env .env        # if not already present; fill in AZURE_OPENAI_* etc.
python main.py
```

`.env` keys used: `IMAP_SERVER`, `EMAIL_USER`, `EMAIL_PASS`, `AZURE_OPENAI_API_KEY`,
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`,
`AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `REGION`, `MONGO_URI`, `DB_NAME`, `FILE_DETAILS`.

Output document shape (stored in `tb_file_details.extractedValues`):

```jsonc
{
  "Customer": "Air Logistics Partners FZE",
  "Reg No": "TC-MAA",
  "ACFT Type": "A330-200F",
  "Bulk Reg No": "TC-MAB, TC-MAC",
  "Purposes": "...",
  "Flight Type": "Cargo",
  "Flight Schedule": { "fieldType": "table", "items": [ { "Date","Flight","Departure","From","Arrival","To","Load" } ] },
  "Flight Sectors":  { "fieldType": "table", "items": [ { "Sector","Flight No.","Country","Permit Type" } ] }
}
```
