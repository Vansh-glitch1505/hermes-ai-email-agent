import json

from llm_service import (
    extract_cargo_details,
    get_missing_fields,
    generate_missing_info_reply
)


# =========================================================
# TEST CUSTOMER EMAIL
# =========================================================

EMAIL_BODY = """
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


# =========================================================
# STEP 1: EXTRACT SHIPMENT DETAILS
# =========================================================

print("\n")
print("=" * 60)
print("STEP 1: GEMINI EXTRACTION")
print("=" * 60)

cargo_details = extract_cargo_details(
    EMAIL_BODY
)

print(
    json.dumps(
        cargo_details,
        indent=4
    )
)


# =========================================================
# STEP 2: CHECK MISSING INFORMATION
# =========================================================

print("\n")
print("=" * 60)
print("STEP 2: CHECKING MISSING INFORMATION")
print("=" * 60)

missing_fields = get_missing_fields(
    cargo_details
)

print(
    "Missing fields:",
    missing_fields
)


# =========================================================
# STEP 3: GENERATE CLARIFICATION REPLY
# =========================================================

if missing_fields:

    print("\n")
    print("=" * 60)
    print("STEP 3: GENERATING CLARIFICATION REPLY")
    print("=" * 60)

    reply = generate_missing_info_reply(
        email_body=EMAIL_BODY,
        cargo_details=cargo_details,
        missing_fields=missing_fields
    )

    print("\nAI REPLY:\n")
    print(reply)

else:

    print("\n")
    print("=" * 60)
    print("NO INFORMATION IS MISSING")
    print("=" * 60)

    print(
        "The system would continue to Excel rate lookup."
    )