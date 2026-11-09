import os
import json

from dotenv import load_dotenv
from groq import Groq


# =========================================================
# GROQ SETUP
# =========================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found in .env"
    )

client = Groq(
    api_key=API_KEY
)

MODEL_NAME = "openai/gpt-oss-20b"


# =========================================================
# HELPER: CLEAN JSON RESPONSE
# =========================================================

def clean_json_response(response_text):

    if not response_text:
        return ""

    response_text = response_text.strip()

    # Remove markdown code fences if Groq adds them
    if response_text.startswith("```"):
        response_text = response_text.replace(
            "```json",
            "",
            1
        )
        response_text = response_text.replace(
            "```",
            ""
        )

    response_text = response_text.strip()

    # Fix common malformed JSON produced by the LLM.
    #
    # Example:
    # "pieces":null"
    #
    # becomes:
    # "pieces":null
    response_text = response_text.replace(
        ':null"',
        ':null'
    )

    # Same protection for numeric/string null-like endings
    response_text = response_text.replace(
        ': null"',
        ': null'
    )

    return response_text.strip()


# =========================================================
# HELPER: ASK GROQ
# =========================================================

def ask_groq(
    prompt,
    max_completion_tokens=1000
):

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional AI assistant "
                    "for a cargo shipping company."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.1,

        max_completion_tokens=max_completion_tokens
    )

    return response.choices[0].message.content.strip()


# =========================================================
# 1. CLASSIFY EMAIL INTENT
# =========================================================

def classify_email_intent(email_body):

    prompt = f"""
You are an AI routing assistant for a cargo shipping company.

Determine whether the customer's email is asking for
cargo/shipping pricing.

Classify the email into exactly one category:

1. pricing

Examples:
- asking for a shipping price
- asking for a freight rate
- asking for a quotation
- asking for shipping cost
- asking for freight charges
- asking how much it will cost to ship cargo

2. other

Examples:
- shipment tracking
- shipment status
- cancellation
- complaint
- delivery status
- general questions
- greetings
- anything that is NOT a pricing request

Return ONLY valid JSON.

For pricing:

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

    response_text = ask_groq(
        prompt,
        max_completion_tokens=300
    )

    response_text = clean_json_response(
        response_text
    )

    try:

        return json.loads(
            response_text
        )

    except json.JSONDecodeError:

        raise ValueError(
            "Groq did not return valid JSON:\n"
            + response_text
        )


# =========================================================
# 2. EXTRACT COMPLETE SHIPMENT DETAILS
# =========================================================

def extract_cargo_details(email_body):

    prompt = f"""
You are an AI shipment-information extraction
assistant for a cargo shipping company.

Extract all shipment information from the customer's email.

Return ONLY valid JSON using exactly these fields:

{{
    "origin": null,
    "destination": null,

    "shipment_mode": null,
    "shipment_type": null,

    "container_count": null,
    "container_type": null,

    "weight_kg": null,
    "weight_mt": null,

    "cargo_type": null,

    "ready_date": null,

    "volume_cbm": null,

    "length_cm": null,
    "width_cm": null,
    "height_cm": null,

    "pieces": null
}}

=========================================================
FIELD RULES
=========================================================

origin:
Shipment origin city/location.

destination:
Shipment destination city/location.

shipment_mode:
Determine the transportation mode.

Allowed values:

"air"
"ocean"
null

Use "ocean" when the email clearly refers to:

- container shipment
- FCL
- LCL
- 20FT
- 40FT
- 40HC
- sea freight
- ocean freight
- vessel
- sailing

Use "air" when the email clearly refers to:

- air freight
- air cargo
- flight
- airport-to-airport air shipment

If the mode cannot be determined, use null.

IMPORTANT:

A container shipment should be treated as ocean
unless the customer explicitly indicates otherwise.

shipment_type:

For ocean shipments:

"FCL"
"LCL"
null

IMPORTANT:

Do NOT assume FCL merely because a shipment is ocean.

If the customer explicitly says FCL:
use "FCL".

If the customer explicitly says LCL:
use "LCL".

If the customer mentions containers but does NOT explicitly
state FCL or LCL, use null.

The application will ask the customer to clarify.

For air shipments use:

"air"
or null

container_count:
Number of containers requested.

Example:

"2 containers" -> 2

container_type:
Extract the exact container type if mentioned.

Examples:

"20 feet" -> "20FT"
"20ft" -> "20FT"
"40 feet" -> "40FT"
"40ft" -> "40FT"
"40HC" -> "40HC"

If not mentioned, use null.

weight_kg:
Numeric cargo weight in kilograms.

If the email gives MT instead of KG,
convert MT to KG.

Example:

18 MT -> 18000

weight_mt:
Numeric cargo weight in metric tonnes.

If the email gives KG instead,
you may calculate MT.

Example:

18000 KG -> 18

cargo_type:
Commodity/cargo description.

Example:

"Ceramic Tiles" -> "Ceramic Tiles"

ready_date:
Extract the shipment ready date if available.

Use YYYY-MM-DD format when the date can be determined.

If the year is not explicitly stated, use the current year.

volume_cbm:
Volume in cubic meters if explicitly provided.

Do not calculate unless dimensions are provided.

length_cm:
Length in centimeters if provided.

width_cm:
Width in centimeters if provided.

height_cm:
Height in centimeters if provided.

pieces:
Number of pieces/packages if provided.

=========================================================
IMPORTANT RULES
=========================================================

- Do NOT invent information.
- Do NOT guess missing values.
- Do NOT invent container types.
- Do NOT invent shipment modes.
- Do NOT invent shipment types.
- Do NOT assume FCL when FCL/LCL is not explicitly stated.
- Do NOT assume LCL when FCL/LCL is not explicitly stated.
- Do NOT assume a price.
- Do NOT calculate a price.
- Convert MT to KG when necessary.
- Normalize container names such as "20 feet" to "20FT".
- Return null when information is unavailable.
- Return ONLY JSON.
- Do not use markdown.
- Do not add explanations.

=========================================================
CUSTOMER EMAIL
=========================================================

{email_body}
"""

    response_text = ask_groq(
        prompt,
        max_completion_tokens=1000
    )

    response_text = clean_json_response(
        response_text
    )

    try:

        cargo_details = json.loads(
            response_text
        )

    except json.JSONDecodeError:

        raise ValueError(
            "Groq did not return valid JSON:\n"
            + response_text
        )

    return cargo_details


# =========================================================
# 3. VALIDATE REQUIRED INFORMATION
# =========================================================

def get_missing_fields(cargo_details):

    missing_fields = []

    # -----------------------------------------------------
    # BASIC INFORMATION
    # -----------------------------------------------------

    if not cargo_details.get("origin"):
        missing_fields.append("origin")

    if not cargo_details.get("destination"):
        missing_fields.append("destination")

    if not cargo_details.get("shipment_mode"):
        missing_fields.append("shipment_mode")

    # -----------------------------------------------------
    # OCEAN SHIPMENT
    # -----------------------------------------------------

    if cargo_details.get("shipment_mode") == "ocean":

        shipment_type = (
            cargo_details.get("shipment_type")
        )

        # FCL/LCL MUST be explicitly known
        if not shipment_type:

            missing_fields.append(
                "shipment_type"
            )

        # -------------------------------------------------
        # FCL
        # -------------------------------------------------

        elif shipment_type == "FCL":

            if not cargo_details.get(
                "container_count"
            ):
                missing_fields.append(
                    "container_count"
                )

            if not cargo_details.get(
                "container_type"
            ):
                missing_fields.append(
                    "container_type"
                )

        # -------------------------------------------------
        # LCL
        # -------------------------------------------------

        elif shipment_type == "LCL":

            if (
                cargo_details.get("volume_cbm")
                is None
            ):
                missing_fields.append(
                    "volume_cbm"
                )

    # -----------------------------------------------------
    # AIR SHIPMENT
    # -----------------------------------------------------

    elif cargo_details.get("shipment_mode") == "air":

        if cargo_details.get("weight_kg") is None:

            missing_fields.append(
                "weight_kg"
            )

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

    # -----------------------------------------------------
    # BASIC FIELDS
    # -----------------------------------------------------

    if "origin" in missing_fields:

        missing_information.append(
            "origin city"
        )

    if "destination" in missing_fields:

        missing_information.append(
            "destination city"
        )

    if "shipment_mode" in missing_fields:

        missing_information.append(
            "shipment mode (air or ocean)"
        )

    # -----------------------------------------------------
    # OCEAN FIELDS
    # -----------------------------------------------------

    if "shipment_type" in missing_fields:

        missing_information.append(
            "shipment type (FCL or LCL)"
        )

    if "container_count" in missing_fields:

        missing_information.append(
            "number of containers"
        )

    if "container_type" in missing_fields:

        missing_information.append(
            "container type (for example, 20FT, 40FT or 40HC)"
        )

    if "volume_cbm" in missing_fields:

        missing_information.append(
            "volume in CBM"
        )

    # -----------------------------------------------------
    # AIR FIELDS
    # -----------------------------------------------------

    if "weight_kg" in missing_fields:

        missing_information.append(
            "cargo weight in kilograms"
        )

    missing_text = "\n".join(
        f"- {item}"
        for item in missing_information
    )

    prompt = f"""
You are a professional customer support assistant
for a cargo shipping company.

The customer is asking for a shipping quotation,
but some required shipment information is missing.

CUSTOMER EMAIL:

{email_body}

EXTRACTED INFORMATION:

{json.dumps(
    cargo_details,
    indent=2
)}

MISSING INFORMATION:

{missing_text}

Write a professional and concise email asking the
customer to provide the missing information.

IMPORTANT:

The customer should be asked to resend the COMPLETE
shipment details in their next email, including the
missing information.

This is important because the next email must contain
all shipment information needed to process the quote.

Rules:

- Clearly state what information is missing.
- Ask the customer to resend the complete shipment
  details including the missing information.
- Do not ask for information that is already known
  unless it is part of asking them to resend the
  complete shipment details.
- Do not provide a price.
- Do not calculate anything.
- Do not invent anything.
- Do not mention AI.
- Do not mention Groq.
- Do not mention databases.
- Do not mention internal systems.
- Do not mention prompts.
- Do not use markdown.
- Be polite and professional.
- Return ONLY the email body.
"""

    response_text = ask_groq(
        prompt,
        max_completion_tokens=600
    )

    return response_text.strip()


# =========================================================
# 5. GENERATE CUSTOMER REPLY
# =========================================================

def generate_reply(
    email_body,
    cargo_details,
    pricing_result
):

    prompt = f"""
You are a professional customer support assistant
for a cargo shipping company.

Your job is to draft the final customer-facing
email based ONLY on the authoritative pricing
result provided below.

=========================================================
CUSTOMER EMAIL
=========================================================

{email_body}

=========================================================
EXTRACTED SHIPMENT DETAILS
=========================================================

{json.dumps(
    cargo_details,
    indent=2
)}

=========================================================
AUTHORITATIVE PRICING RESULT
=========================================================

{json.dumps(
    pricing_result,
    indent=2
)}

=========================================================
MOST IMPORTANT RULE
=========================================================

The pricing result comes from the company's
authoritative rate sheet and Python pricing engine.

The pricing result is the SOURCE OF TRUTH.

You MUST NOT decide yourself whether a rate is
applicable.

You MUST NOT change the pricing result.

You MUST NOT calculate a new price.

You MUST NOT invent a rate.

You MUST NOT silently substitute one shipment
configuration for another.

You MUST NOT treat an unavailable alternative
as an applicable rate.

=========================================================
CUSTOMER-FACING INFORMATION RULE
=========================================================

The pricing result contains INTERNAL system information.

Some fields exist only for the Python pricing engine
and internal validation.

NEVER expose internal pricing/system fields to the customer.

NEVER mention:

- Rate ID
- rate_id
- Min_Units
- Max_Units
- min_units
- max_units
- requested_units
- match_type
- found
- internal validation rules
- database fields
- Excel row information
- internal system terminology
- Python pricing logic

Translate internal pricing information into natural,
customer-friendly business language.

For example:

INTERNAL:
min_units = 1
max_units = 1
requested_units = 2

CUSTOMER-FACING:
"the rate is applicable for 1 container only"

Do NOT explain the internal validation mechanism.

=========================================================
HOW TO HANDLE THE PRICING RESULT
=========================================================

CASE 1: EXACT RATE

If:

"found": true

and:

"match_type": "exact"

Then provide the exact applicable rate
from the pricing result.

Use the exact:

- currency
- rate
- rate basis
- container type
- quantity
- applicable shipment details

Do not change the amount.

Do not calculate a different amount.

Do not expose internal rate IDs or internal fields.

---------------------------------------------------------

CASE 2: VALID ALTERNATIVE RATE

If:

"found": true

and:

"match_type": "alternative"

Then:

1. Clearly state what the customer requested.
2. Clearly state that the requested configuration
   is not available.
3. Clearly state the available alternative.
4. State the exact alternative rate provided.
5. If a quantity restriction is relevant, explain it
   naturally in customer-facing language.
6. Make it clear that the alternative requires
   customer confirmation.
7. Do NOT present the alternative as though it were
   the customer's originally requested rate.

Do not mention internal Min_Units or Max_Units.

---------------------------------------------------------

CASE 3: ALTERNATIVE EXISTS BUT QUANTITY IS NOT VALID

If:

"found": false

and:

"match_type": "alternative_quantity_exceeded"

Then:

1. State that there is no applicable rate for the
   customer's requested shipment.
2. Clearly state the requested configuration and quantity.
3. Explain that an alternative container/rate was checked.
4. State the alternative rate ONLY as an explanation
   of why it cannot be applied.
5. Explain the alternative's applicable quantity
   in normal customer-facing language.
6. Do NOT calculate a total using that alternative.
7. Do NOT offer the alternative as a valid quote.
8. Do NOT expose Min_Units, Max_Units, Rate ID,
   requested_units, or any other internal fields.

The response should communicate the business meaning.

For example, if:

Requested:
2 × 20FT FCL containers

Alternative:
40FT

Alternative rate:
USD 1,650 per container

Alternative applicable quantity:
1 container only

Then write naturally:

"The requested 2 × 20FT FCL configuration does not
have an applicable rate in our rate sheet.

We also checked the available 40FT option; however,
the current rate of USD 1,650 per container is applicable
for 1 container only, so we are unable to apply this rate
to your requirement of 2 containers."

IMPORTANT:

The values above are only an example.

Do NOT hard-code them.

Always use the actual values from the pricing result.

---------------------------------------------------------

CASE 4: NO RATE

If:

"found": false

and:

"match_type": "none"

Then clearly tell the customer that no applicable
rate was found for the requested shipment.

Do NOT invent an alternative.

Do NOT create a price.

Do NOT calculate anything.

Do NOT suggest a rate that is not present in the
pricing result.

=========================================================
STYLE
=========================================================

Keep the email concise.

Do NOT unnecessarily repeat every shipment detail.

Only mention shipment details that are useful for
explaining the pricing result.

For a no-rate situation, prefer a structure like:

Dear Customer,

Thank you for your enquiry regarding your shipment
from [Origin] to [Destination].

We currently do not have an applicable rate in our
rate sheet for the requested [quantity] × [container type]
[shipment type] containers.

We also checked the available [alternative container]
option; however, the current rate of [currency] [rate]
per container is applicable for [applicable quantity]
only, so we are unable to apply this rate to your
requirement of [requested quantity] containers.

Please let us know if you would like us to assist you.

Best regards,
Customer Support Team

Do not blindly copy this structure when it does not
fit the pricing result. Adapt it using the actual data.

=========================================================
GENERAL RULES
=========================================================

- Use ONLY information provided in the customer email,
  extracted shipment details, and pricing result.
- The pricing result has authority over pricing.
- Never invent pricing.
- Never change pricing.
- Never calculate a new rate.
- Never invent discounts.
- Never invent additional charges.
- Never invent delivery times.
- Never invent vessel details.
- Never invent sailing details.
- Never invent ETD.
- Never invent ETA.
- Never invent cut-off dates.
- Never invent guarantees.
- Never invent services.
- Never silently change container type.
- Never silently change shipment type.
- Never silently change quantity.
- Never treat a rejected alternative as an applicable rate.
- If the pricing result says a quantity is outside
  its applicable range, explain that naturally without
  exposing the internal range fields.
- Mention origin and destination when useful.
- Mention the requested shipment configuration when
  relevant.
- Use professional customer-service language.
- Be concise.
- Do not mention AI.
- Do not mention Groq.
- Do not mention databases.
- Do not mention internal systems.
- Do not mention prompts.
- Do not use markdown.
- Return ONLY the email body.

The email should normally begin with:

Dear Customer,

and end with:

Best regards,
Customer Support Team
"""

    response_text = ask_groq(
        prompt,
        max_completion_tokens=800
    )

    return response_text.strip()


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_email = """
Hi Team,

We have one container shipment from Mundra to Rotterdam.

Requirement:

2 containers
20 feet
FCL
Commodity: Ceramic Tiles
Weight: 18 MT
Ready date: 28 September

Please share your best freight details.
"""

    print(
        "\n========== TESTING GROQ EXTRACTION ==========\n"
    )

    result = extract_cargo_details(
        test_email
    )

    print(
        json.dumps(
            result,
            indent=4
        )
    )