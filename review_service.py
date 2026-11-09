import os
import json
from dotenv import load_dotenv
from groq import Groq


# =========================================================
# ENVIRONMENT SETUP
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


# =========================================================
# REVIEW AI REPLY
# =========================================================

def review_reply(
    customer_email,
    cargo_details,
    pricing_result,
    draft_reply
):

    prompt = f"""
You are a careful quality-control reviewer for a cargo
shipping customer support system.

Your job is to check whether the AI-generated email is
factually correct, consistent with the customer's request,
and safe to send.

Do NOT reject a response simply because it does not provide
a price when the system is waiting for missing shipment
information.

CUSTOMER EMAIL:
{customer_email}

EXTRACTED CARGO DETAILS:
{json.dumps(cargo_details, indent=2)}

AUTHORITATIVE EXCEL PRICING RESULT:
{json.dumps(pricing_result, indent=2, default=str)}

AI-GENERATED DRAFT:
{draft_reply}

========================================================
IMPORTANT REVIEW PRINCIPLE
========================================================

The type of response matters.

There are three normal situations:

1. COMPLETE QUOTATION
   The shipment information is complete and a rate was found.

2. ALTERNATIVE RATE
   The requested configuration is unavailable but an
   applicable alternative exists.

3. MISSING INFORMATION / CLARIFICATION
   Required shipment information is missing, so the system
   asks the customer to provide or confirm it.

A clarification email is a VALID response.

Do not expect every email to contain a freight rate.

========================================================
GENERAL CHECKS
========================================================

Check the following when they are relevant to the response:

1. Origin is not incorrectly changed.
2. Destination is not incorrectly changed.
3. Shipment mode is not incorrectly changed.
4. Shipment type is not incorrectly invented.
5. Container count is not incorrectly changed.
6. Container type is not incorrectly changed.
7. Weight is not incorrectly changed.
8. Currency is correct when a price is provided.
9. Price is correct when a price is provided.
10. The response is consistent with the authoritative
    Excel pricing result.
11. The response does not invent unsupported information.
12. The response is professional and understandable.

Only flag an issue when it is a meaningful factual,
business, or safety problem.

Do NOT reject a response for minor wording differences,
formatting differences, or reasonable professional phrasing.

========================================================
MISSING INFORMATION / CLARIFICATION
========================================================

If the pricing result indicates that required information
is missing, the draft is EXPECTED to request that information.

For example, if:

- shipment_type is missing
- container_type is missing
- container_count is missing
- volume_cbm is missing
- weight_kg is missing
- origin is missing
- destination is missing

then asking the customer for that information is correct.

In this situation:

- Do NOT require the draft to provide a freight rate.
- Do NOT require the draft to provide transit time.
- Do NOT reject the draft because no price is provided.
- Do NOT reject the draft because the customer is asked
  for additional information.
- Approve the draft if it correctly asks for the missing
  information.
- The draft may ask the customer to resend the complete
  shipment details.
- The draft must not invent a price.
- The draft must not invent transit time.
- The draft must not invent vessel, sailing, ETD, ETA,
  cut-off, or availability information.

IMPORTANT:

If a customer mentions containers but does not explicitly
state FCL or LCL, the system must NOT assume FCL or LCL.

Therefore, asking the customer to confirm FCL or LCL is
CORRECT and should be approved.

========================================================
COMPLETE QUOTATION
========================================================

If the pricing result contains a valid applicable rate:

The draft should:

- Use the correct origin and destination.
- Use the correct shipment mode.
- Use the applicable rate from Excel.
- Use the correct currency.
- Use the correct price calculation.
- Use the correct weight or billable quantity when relevant.
- Use transit time and routing only when supported by Excel.
- Use rate validity when supported by Excel.

The draft must NOT:

- Invent a different rate.
- Invent discounts.
- Invent additional fees.
- Invent guarantees.
- Invent vessel names.
- Invent sailing dates.
- Invent ETD or ETA.
- Invent cut-off dates.
- Invent availability.
- Claim services that are not supported by the pricing data.

========================================================
ALTERNATIVE RATE
========================================================

If match_type is "alternative":

The requested configuration is unavailable.

The draft should:

- Clearly identify the requested configuration.
- Clearly identify the alternative configuration.
- Use the alternative rate from Excel.
- Use the correct rate basis.
- Use the correct quantity rules.
- Ask the customer for confirmation if appropriate.

The draft must NOT present the alternative rate as if it
were the requested configuration.

IMPORTANT:

Do not approve an alternative rate simply because an
alternative exists.

The alternative must follow the Min_Units and Max_Units
rules in the authoritative pricing result.

If the pricing result says that the alternative quantity
is outside the allowed range, the draft must NOT apply
that rate.

========================================================
NO APPLICABLE RATE
========================================================

If the pricing result indicates that no applicable rate
exists:

The draft should clearly communicate that no applicable
rate is currently available.

It must NOT invent or substitute a rate.

If the pricing result contains a rejected alternative,
the draft may explain why that alternative cannot be
applied.

========================================================
DO NOT OVER-REVIEW
========================================================

Do not reject a draft merely because:

- It asks for missing information.
- It does not provide a price when information is missing.
- It does not provide transit time when information is missing.
- It uses slightly different professional wording.
- It asks the customer to resend complete shipment details.
- It does not repeat every field from the original email.
- It does not use the exact same wording as the customer.

Reject only when there is a meaningful problem such as:

- Incorrect price.
- Incorrect currency.
- Incorrect route.
- Incorrect shipment configuration.
- Invented information.
- Incorrect quantity calculation.
- Applying an invalid rate.
- Misrepresenting an alternative rate.
- Claiming unsupported sailing or schedule information.

========================================================
OUTPUT
========================================================

Do not explain your reasoning.

Return ONLY valid JSON.

If the email is correct:

{{
    "approved": true,
    "issues": []
}}

If there is a meaningful problem:

{{
    "approved": false,
    "issues": [
        "short description of the problem"
    ]
}}
"""


    # =====================================================
    # CALL GROQ
    # =====================================================

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful cargo email quality-control "
                    "reviewer. Be strict about factual accuracy "
                    "and pricing, but do not reject valid "
                    "clarification emails. Return only JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_completion_tokens=1500
    )


    # =====================================================
    # DEBUG RESPONSE
    # =====================================================

    print(
        "\n========== GROQ RAW RESPONSE =========="
    )

    print(
        response
    )

    print(
        "======================================="
    )


    # =====================================================
    # EXTRACT RESPONSE
    # =====================================================

    response_text = response.choices[0].message.content


    if not response_text:

        raise ValueError(
            "Groq returned an empty response. "
            f"Finish reason: {response.choices[0].finish_reason}"
        )


    response_text = response_text.strip()


    # =====================================================
    # REMOVE MARKDOWN IF PRESENT
    # =====================================================

    if response_text.startswith("```"):

        response_text = response_text.replace(
            "```json",
            ""
        )

        response_text = response_text.replace(
            "```",
            ""
        )

        response_text = response_text.strip()


    # =====================================================
    # PARSE JSON
    # =====================================================

    try:

        review_result = json.loads(
            response_text
        )

    except json.JSONDecodeError:

        print(
            "\n⚠️ Groq returned invalid JSON:"
        )

        print(
            repr(response_text)
        )

        raise ValueError(
            "Groq did not return valid JSON."
        )


    # =====================================================
    # BASIC VALIDATION
    # =====================================================

    if "approved" not in review_result:

        raise ValueError(
            "Groq response does not contain "
            "'approved'."
        )


    if "issues" not in review_result:

        review_result["issues"] = []


    return review_result