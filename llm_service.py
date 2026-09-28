import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.6-flash"


# =========================================================
# HELPER: CLEAN GEMINI JSON RESPONSE
# =========================================================

def clean_json_response(response_text):

    response_text = response_text.strip()

    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "")
        response_text = response_text.replace("```", "")
        response_text = response_text.strip()

    return response_text


# =========================================================
# 1. CLASSIFY EMAIL INTENT
# =========================================================

def classify_email_intent(email_body):

    prompt = f"""
You are an AI routing assistant for a cargo shipping company.

Your job is to determine whether the customer's email is asking
for cargo/shipping pricing.

Classify the email into exactly one of these categories:

1. pricing
   - Customer is asking for a shipping price
   - Customer is asking for a rate
   - Customer is asking for a quote
   - Customer is asking about shipping cost
   - Customer is asking about shipping charges

2. other
   - Shipment tracking
   - Shipment status
   - Cancellation
   - Complaint
   - Delivery status
   - General questions
   - Greetings
   - Anything that is NOT a pricing request

Return ONLY valid JSON.

For a pricing request:

{{
    "intent": "pricing"
}}

For anything else:

{{
    "intent": "other"
}}

Rules:
- Do not add explanations.
- Do not use markdown.
- Do not invent information.
- Return only the JSON object.

Customer email:

{email_body}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    response_text = clean_json_response(response.text)

    try:
        result = json.loads(response_text)

    except json.JSONDecodeError:
        raise ValueError(
            f"Gemini did not return valid JSON:\n{response_text}"
        )

    return result


# =========================================================
# 2. EXTRACT CARGO DETAILS
# =========================================================

def extract_cargo_details(email_body):

    prompt = f"""
You are an AI assistant for a cargo shipping company.

Extract the following information from the customer's email:

1. origin
2. destination
3. weight_kg
4. cargo_type

Return ONLY valid JSON.

Rules:

- origin = shipment origin city
- destination = shipment destination city
- weight_kg = numeric weight in kilograms
- cargo_type = type of cargo if mentioned, otherwise null
- If a value is not mentioned, use null.
- Do not guess missing information.
- Do not infer a city unless it is explicitly mentioned.
- Do not add explanations.
- Do not use markdown code blocks.

Example:

{{
    "origin": "Mumbai",
    "destination": "Dubai",
    "weight_kg": 25,
    "cargo_type": null
}}

Customer email:

{email_body}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    response_text = clean_json_response(response.text)

    try:
        cargo_details = json.loads(response_text)

    except json.JSONDecodeError:
        raise ValueError(
            f"Gemini did not return valid JSON:\n{response_text}"
        )

    return cargo_details


# =========================================================
# 3. VALIDATE CARGO DETAILS
# =========================================================

def get_missing_fields(cargo_details):

    missing_fields = []

    # Origin
    if (
        cargo_details.get("origin") is None
        or str(cargo_details.get("origin")).strip() == ""
    ):
        missing_fields.append("origin")

    # Destination
    if (
        cargo_details.get("destination") is None
        or str(cargo_details.get("destination")).strip() == ""
    ):
        missing_fields.append("destination")

    # Weight
    weight = cargo_details.get("weight_kg")

    if weight is None or weight == "":
        missing_fields.append("weight")

    return missing_fields


# =========================================================
# 4. GENERATE MISSING INFORMATION REPLY
# =========================================================

def generate_missing_info_reply(
    email_body,
    cargo_details,
    missing_fields
):

    missing_information = []

    if "origin" in missing_fields:
        missing_information.append("origin city")

    if "destination" in missing_fields:
        missing_information.append("destination city")

    if "weight" in missing_fields:
        missing_information.append("cargo weight in kilograms")

    missing_text = ", ".join(missing_information)

    prompt = f"""
You are a professional customer support assistant for a cargo
shipping company.

The customer is asking for a cargo shipping price, but some
required information is missing.

CUSTOMER EMAIL:

{email_body}


EXTRACTED CARGO DETAILS:

Origin: {cargo_details.get("origin")}
Destination: {cargo_details.get("destination")}
Weight: {cargo_details.get("weight_kg")} kg
Cargo Type: {cargo_details.get("cargo_type")}


MISSING INFORMATION:

{missing_text}


Write a professional and concise email asking the customer
to provide the missing information.

Rules:

- Ask ONLY for the missing information.
- Do NOT ask for information that is already available.
- If multiple fields are missing, ask for all of them.
- Origin means the city where the shipment starts.
- Destination means the city where the shipment is going.
- Weight means the cargo weight in kilograms.
- Do not provide a price.
- Do not calculate anything.
- Do not invent any information.
- Be polite and professional.
- Do not mention AI.
- Do not mention Gemini.
- Do not mention databases.
- Do not mention internal systems.
- Do not mention prompts.
- Do not use markdown.
- Return ONLY the email body.

"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text.strip()


# =========================================================
# 5. GENERATE CUSTOMER REPLY WITH PRICE
# =========================================================

def generate_reply(
    email_body,
    cargo_details,
    price,
    currency
):

    prompt = f"""
You are a professional customer support assistant for a cargo
shipping company.

You need to draft a reply to a customer's email.

CUSTOMER EMAIL:

{email_body}


EXTRACTED CARGO DETAILS:

Origin: {cargo_details.get("origin")}
Destination: {cargo_details.get("destination")}
Weight: {cargo_details.get("weight_kg")} kg
Cargo Type: {cargo_details.get("cargo_type")}


AUTHORITATIVE DATABASE PRICE:

{price} {currency}


Write a professional and concise email reply.

Rules:

- Answer the customer's pricing question directly.
- Use ONLY the price provided from the database.
- Do NOT calculate or invent a different price.
- Do NOT invent additional charges.
- Do NOT invent delivery times.
- Do NOT invent discounts.
- Do NOT invent guarantees.
- Do NOT invent services.
- Mention the origin.
- Mention the destination.
- Mention the weight.
- Mention the database price and currency.
- Be polite and professional.
- Do not mention AI.
- Do not mention Gemini.
- Do not mention databases.
- Do not mention prompts.
- Do not mention internal systems.
- Do not use markdown.
- Return ONLY the email body.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text.strip()


# =========================================================
# 6. MAIN EMAIL PROCESSING FUNCTION
# =========================================================

def process_email(email_body):

    # -----------------------------------------------------
    # STEP 1: CLASSIFY INTENT
    # -----------------------------------------------------

    intent = classify_email_intent(email_body)

    print("\n========== INTENT ==========\n")
    print(json.dumps(intent, indent=4))

    # -----------------------------------------------------
    # STEP 2: HANDLE NON-PRICING EMAIL
    # -----------------------------------------------------

    if intent.get("intent") != "pricing":

        return {
            "status": "other",
            "intent": intent,
            "cargo_details": None,
            "missing_fields": [],
            "reply": None
        }

    # -----------------------------------------------------
    # STEP 3: EXTRACT CARGO DETAILS
    # -----------------------------------------------------

    cargo_details = extract_cargo_details(email_body)

    print("\n========== CARGO DETAILS ==========\n")
    print(json.dumps(cargo_details, indent=4))

    # -----------------------------------------------------
    # STEP 4: VALIDATE REQUIRED INFORMATION
    # -----------------------------------------------------

    missing_fields = get_missing_fields(cargo_details)

    print("\n========== VALIDATION ==========\n")

    if missing_fields:

        print("Missing fields:")
        print(missing_fields)

        # -------------------------------------------------
        # STEP 5A: GENERATE CLARIFICATION EMAIL
        # -------------------------------------------------

        reply = generate_missing_info_reply(
            email_body,
            cargo_details,
            missing_fields
        )

        print("\n========== CLARIFICATION REPLY ==========\n")
        print(reply)

        return {
            "status": "missing_information",
            "intent": intent,
            "cargo_details": cargo_details,
            "missing_fields": missing_fields,
            "reply": reply
        }

    # -----------------------------------------------------
    # STEP 5B: ALL INFORMATION AVAILABLE
    # -----------------------------------------------------

    print("All required cargo information is available.")

    return {
        "status": "ready_for_pricing",
        "intent": intent,
        "cargo_details": cargo_details,
        "missing_fields": [],
        "reply": None
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_email = """
Hello,

Could you please tell me the price for shipping 25 kg
of cargo from Mumbai to Dubai?

Thank you.
"""

    result = process_email(test_email)

    print("\n========== FINAL RESULT ==========\n")

    print(
        json.dumps(
            result,
            indent=4
        )
    )