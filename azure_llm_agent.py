import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# ---------------------------------------------------------
# LLM PROMPT TEMPLATE
# ---------------------------------------------------------
EMAIL_PARSE_PROMPT = """
You are an advanced aviation document parser.  
You receive unstructured aviation mission request emails containing:

- Mission details

- Flight sectors & overflight/landing/technical permits

- Aircraft type & registration

- Multi-date flight schedules

- Permit countries & permit categories

- DG/Hazmat references (IGNORE for output) 

Your job:  
1. Understand the email context regardless of its format or spelling quality  
2. Extract all relevant values  
3. Output them ONLY as JSON in the exact schema described below  
4. Never include explanation, only JSON 
5.Extract ONLY the information required in the schema.
6.ALWAYS capture ALL rows and ALL countries (never skip anything).
7.Normalize broken text formats, spacing, shorthand, and inconsistent styles. 

-----------------------------------------------------

### PERMIT TYPE NORMALIZATION RULE



You must map raw text to ONLY the following permitted values:



- "OVF" → Overflight Permit

- "OV" → Overflight Permit

- "OVERFLIGHT" → Overflight Permit

- "FIR" (Ethiopia FIR, South Sudan FIR, etc.) → Overflight Permit

- "Landing" / "LDG" / "LNDG" / "Arrival" → Landing Permit

- "Tech Stop" / "Technical Stop" / "Fuel Stop"/TECH → Technical Stop Permit

- "Special" / "Non-standard" → Special Flight Permit

- "DG" -> "Dangerous Goods Permit"

- "TFC" → "Traffic Rights Permit"

- "TLP" → "Technical Landing Permit"


❗ NEVER output values like:

- “FIR Overflight”

- “FIR OVF”

- “Airspace Permit”

- “Unknown Permit”

- or any text not in the standardized list above.


You ALWAYS:

- extract **all** mission, sector, permit, aircraft.  

- never omit countries or entries (if 3 permits are there, output 3 rows; if 7 schedule rows, output all 7)

- normalize text (resolve broken spacing, misspellings, shorthand)

- extract flight sectors properly even if formats differ

- output ONLY JSON (no explanation)

- ensure tables contain **every row**, even if repeated flight numbers exist

### IMPORTANT — MULTI-PERMIT LINES & SPLITTING RULES

Many lines list multiple permits for the same sector/country (for example:
"Türkiye TFC" on one line and "Türkiye DG Approval" on the next, or
"Jordan OVF, Jordan Landing" on a single line). **You MUST** treat each permit occurrence as a separate permit row.

Rules:
- If multiple permit tokens appear for the same country (on one line or across adjacent lines), produce **one table row per permit token** — do not merge tokens into a single row.
- Split permit lists on common separators: comma `,`, semicolon `;`, slash `/`, vertical bar `|`, the words `and`, `&`, `+`, and on newlines.
- Trim and normalize each token before mapping to the normalized Permit Type list below.
- Map phrases that include the word **Approval** or **Approval for** (e.g., `DG Approval`, `DG Approval required`) to the canonical value for the permit token (`DG` → `Dangerous Goods`).
- If the same country appears twice with different tokens (e.g., `Türkiye TFC` and `Türkiye DG Approval`), output two separate rows both using the same Sector and Flight No, with Permit Types `Traffic Rights Permit` and `Dangerous Goods` respectively.
- Always preserve the original Sector and Flight No fields on every generated row.
-----------------------------------------------------
### PART A — FORMS OUTPUT (Key → Value mapping)
Return this structure:

{
    "Customer Type": None,
    "Customer : "<Extracted Charterer Name>",
    "Operator": None,
    "Flight Type": "<Extracted Flight Type if any>",
    "Purposes": "<Mission Purpose or Mission Name>",
    "Reg No": "<Primary Aircraft Registration>",
    "ACFT Type": "<Aircraft Type>",
    "Bulk Reg No": "<Comma separated alt registrations>"
}

-----------------------------------------------------
### PART B — TABLE OUTPUT
Produce TWO tables with this structure:
IMPORTANT: If a flight number has multiple countries/permits, create separate rows.

{
    "Flight Schedule": {
        "fieldType": "table",
        "items": [
            {
            "Date": "<Parsed Date or DateTime>",
            "Flight": "<Flight Number>",
            "Departure": "<Departure UTC Date & Time>",
            "From": "<Origin ICAO full form (Abbreviation)>",
            "Arrival": "<Arrival UTC Date & Time>,
            "To": "<Destination ICAO full form (Abbreviation)>",
            "Load": "<Extract the load exactly as written in the email content (no assumptions, no fixed words, no normalization)>
        }
        ]
    },

    "Flight Sectors": {
        "fieldType": "table",
        "items": [
            {
                "Sector": "<Origin ICAO> - <Destination ICAO>",
                "Flight No.": "<Flight Number>",
                "Country": "<Permit Country>",
                "Permit Type": "<Permit Type>"
            }
        ]
    }
}

-----------------------------------------------------
### AIRPORT NAME EXPANSION RULE
For any ICAO code (e.g., EDDP), return:
"Leipzig/Halle Airport (EDDP)"

If unknown, return:
"<ICAO> - Unknown Airport"

-----------------------------------------------------
### FINAL INSTRUCTION

Take the email content below and return ONLY **one complete JSON object**
containing both Forms + Tables exactly in the schema above.
NO extra text. NO explanations. ONLY JSON.
Do not wrap the JSON in json ...
Do not output multiple JSON blocks.
Do not include extra text, explanations, or comments.
Return only the final combined JSON object exactly in this structure:
{
  "<fieldName>": <value or null>,
  "<fieldName>": <value or null>,
  "<tableName>": {
      "fieldType": "table",
      "items": [
          { row1 },
          { row2 },
          ...
      ]
  },
  "<anotherTableName>": {
      "fieldType": "table",
      "items": [ ... ]
  }
}


-------------------- EMAIL CONTENT START --------------------
{{EMAIL_CONTENT}}
-------------------- EMAIL CONTENT END --------------------
"""


# ---------------------------------------------------------
# FUNCTION TO CALL LLM
# ---------------------------------------------------------
def extract_structured_email_data(email_content: str):
    """
    Takes raw email text and returns structured JSON output parsed by LLM.
    """

    if not email_content or not email_content.strip():
        return {"error": "Empty content provided"}

    # Insert content into prompt
    final_prompt = EMAIL_PARSE_PROMPT.replace("{{EMAIL_CONTENT}}", email_content.strip())

    client = AzureOpenAI(
        api_key=AZURE_API_KEY,
        azure_endpoint=AZURE_ENDPOINT,
        api_version=AZURE_API_VERSION,
    )

    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0
        )
        llm_output = response.choices[0].message.content
        return llm_output
    
    except Exception as e:
        return {"error": str(e)}
