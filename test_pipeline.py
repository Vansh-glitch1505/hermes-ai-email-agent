import json

from llm_service import (
    classify_email_intent,
    extract_cargo_details,
    generate_reply
)

from rate_service import get_rate

from review_service import review_reply


# =========================================================
# MANAGER TEST EMAIL
# =========================================================

EMAIL = """
Hi Team,

We have one container shipment from Mundra to Rotterdam.

Requirement:

2 containers

20 feet
Commodity: Ceramic Tiles
Weight: 18 MT
Ready date: 28 September

Please share your best freight and sailing details.
"""


print("\n")
print("=" * 70)
print("HERMES AI EMAIL AGENT - PIPELINE TEST")
print("=" * 70)


# =========================================================
# STEP 1: INTENT
# =========================================================

print("\n========== STEP 1: INTENT CLASSIFICATION ==========")

intent_result = classify_email_intent(EMAIL)

print(
    json.dumps(
        intent_result,
        indent=4
    )
)


# =========================================================
# STEP 2: EXTRACTION
# =========================================================

print("\n========== STEP 2: SHIPMENT EXTRACTION ==========")

cargo_details = extract_cargo_details(EMAIL)

print(
    json.dumps(
        cargo_details,
        indent=4
    )
)


# =========================================================
# STEP 3: RATE LOOKUP
# =========================================================

print("\n========== STEP 3: EXCEL RATE LOOKUP ==========")

rate_result = get_rate(
    shipment_mode=cargo_details.get("shipment_mode"),
    origin=cargo_details.get("origin"),
    destination=cargo_details.get("destination"),
    shipment_type=cargo_details.get("shipment_type"),
    container_type=cargo_details.get("container_type"),
    container_count=cargo_details.get("container_count"),
    weight_kg=cargo_details.get("weight_kg"),
    shipment_date="2026-09-28",
    cargo_type=cargo_details.get("cargo_type")
)

print(
    json.dumps(
        rate_result,
        indent=4,
        default=str
    )
)


# =========================================================
# STOP IF NO RATE
# =========================================================

if not rate_result.get("found"):

    print("\n❌ No rate found.")
    print("Stopping test.")

    exit()


# =========================================================
# STEP 4: GENERATE REPLY
# =========================================================

print("\n========== STEP 4: AI DRAFT REPLY ==========")

reply = generate_reply(
    email_body=EMAIL,
    cargo_details=cargo_details,
    pricing_result=rate_result
)

print("\nAI DRAFT:")
print("-" * 70)
print(reply)
print("-" * 70)


# =========================================================
# STEP 5: GROQ REVIEW
# =========================================================

print("\n========== STEP 5: GROQ REVIEW ==========")

review_result = review_reply(
    customer_email=EMAIL,
    cargo_details=cargo_details,
    pricing_result=rate_result,
    draft_reply=reply
)

print(
    json.dumps(
        review_result,
        indent=4
    )
)


# =========================================================
# FINAL RESULT
# =========================================================

print("\n")
print("=" * 70)
print("PIPELINE TEST COMPLETE")
print("=" * 70)

if review_result.get("approved") is True:

    print("\n✅ FINAL RESULT: APPROVED")
    print("The draft passed the Groq quality check.")

else:

    print("\n❌ FINAL RESULT: REJECTED")

    print("\nIssues:")

    for issue in review_result.get("issues", []):
        print("-", issue)