from gmail_service import (
    get_gmail_service,
    get_unread_emails,
    send_reply,
    mark_email_as_read
)

from llm_service import (
    classify_email_intent,
    extract_cargo_details,
    generate_reply
)

from db_service import get_price
from review_service import review_reply

import json
import traceback


def process_email(service, email):

    print("\n")
    print("=" * 60)
    print("PROCESSING EMAIL")
    print("=" * 60)

    print("\nFrom:", email["sender"])
    print("Subject:", email["subject"])

    print("\nBody:")
    print(email["body"])

    # =====================================================
    # STEP 1: CLASSIFY EMAIL INTENT
    # =====================================================

    print(
        "\n========== GEMINI INTENT CLASSIFICATION =========="
    )

    intent_result = classify_email_intent(
        email["body"]
    )

    print(
        json.dumps(
            intent_result,
            indent=4
        )
    )

    intent = intent_result.get("intent")

    # =====================================================
    # NON-PRICING EMAIL
    # =====================================================

    if intent != "pricing":

        print(
            "\n⚠️ This email is NOT a pricing request."
        )

        print(
            "No reply will be generated."
        )

        print(
            "Email will remain unread."
        )

        return "skipped"

    print(
        "\n✅ Pricing request detected."
    )

    # =====================================================
    # STEP 2: EXTRACT CARGO DETAILS
    # =====================================================

    print(
        "\n========== GEMINI EXTRACTION =========="
    )

    cargo_details = extract_cargo_details(
        email["body"]
    )

    print(
        json.dumps(
            cargo_details,
            indent=4
        )
    )

    origin = cargo_details.get(
        "origin"
    )

    destination = cargo_details.get(
        "destination"
    )

    weight_kg = cargo_details.get(
        "weight_kg"
    )

    cargo_type = cargo_details.get(
        "cargo_type"
    )

    # =====================================================
    # VALIDATE REQUIRED INFORMATION
    # =====================================================

    if not origin:

        print(
            "\n❌ Origin not found."
        )

        print(
            "Email remains unread."
        )

        return "failed"

    if not destination:

        print(
            "\n❌ Destination not found."
        )

        print(
            "Email remains unread."
        )

        return "failed"

    if weight_kg is None:

        print(
            "\n❌ Weight not found."
        )

        print(
            "Email remains unread."
        )

        return "failed"

    # =====================================================
    # STEP 3: DATABASE PRICE LOOKUP
    # =====================================================

    print(
        "\n========== POSTGRESQL =========="
    )

    print(
        "Searching pricing table..."
    )

    price_result = get_price(
        origin=origin,
        destination=destination,
        weight_kg=weight_kg,
        cargo_type=cargo_type
    )

    if not price_result:

        print(
            "\n❌ No matching price found."
        )

        print(
            "No reply will be sent."
        )

        print(
            "Email remains unread."
        )

        return "failed"

    price = price_result["price"]

    currency = price_result["currency"]

    print(
        f"Price found: {price} {currency}"
    )

    # =====================================================
    # STEP 4: GENERATE REPLY
    # =====================================================

    print(
        "\n========== AI DRAFT REPLY =========="
    )

    reply = generate_reply(
        email_body=email["body"],
        cargo_details=cargo_details,
        price=price,
        currency=currency
    )

    print(
        "\n" + reply
    )

    # =====================================================
    # STEP 5: GROQ REVIEW
    # =====================================================

    print(
        "\n========== GROQ REVIEW =========="
    )

    review_result = review_reply(
        customer_email=email["body"],
        cargo_details=cargo_details,
        price=price,
        currency=currency,
        draft_reply=reply
    )

    print(
        json.dumps(
            review_result,
            indent=4
        )
    )

    # =====================================================
    # STEP 6: CHECK GROQ RESULT
    # =====================================================

    if review_result.get("approved") is not True:

        print(
            "\n❌ REPLY REJECTED"
        )

        issues = review_result.get(
            "issues",
            []
        )

        if issues:

            print(
                "\nIssues found:"
            )

            for issue in issues:

                print(
                    "-",
                    issue
                )

        else:

            print(
                "Groq did not provide specific issues."
            )

        print(
            "\nEmail remains unread."
        )

        return "failed"

    # =====================================================
    # STEP 7: SEND EMAIL
    # =====================================================

    print(
        "\n✅ REPLY APPROVED"
    )

    print(
        "\n========== SENDING EMAIL =========="
    )

    try:

        send_result = send_reply(
            service=service,
            email=email,
            reply_body=reply
        )

        print(
            "\n✅ Reply sent successfully!"
        )

        print(
            "Sent message ID:",
            send_result["id"]
        )

    except Exception as e:

        print(
            "\n❌ ERROR SENDING REPLY"
        )

        print(e)

        print(
            "\nEmail remains unread."
        )

        return "failed"

    # =====================================================
    # STEP 8: MARK ORIGINAL EMAIL AS READ
    # =====================================================

    try:

        mark_email_as_read(
            service,
            email["id"]
        )

        print(
            "✅ Original email marked as read."
        )

    except Exception as e:

        print(
            "\n⚠️ Reply was sent, but the original "
            "email could not be marked as read."
        )

        print(e)

        return "sent_not_marked"

    return "success"


def main():

    # =====================================================
    # CONNECT TO GMAIL
    # =====================================================

    print(
        "\nConnecting to Gmail..."
    )

    service = get_gmail_service()

    print(
        "Checking for unread emails..."
    )

    emails = get_unread_emails(
        service
    )

    if not emails:

        print(
            "\nNo unread emails found."
        )

        return

    print(
        f"\nFound {len(emails)} unread email(s)."
    )

    # =====================================================
    # PROCESS EVERY UNREAD EMAIL
    # =====================================================

    results = {
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "sent_not_marked": 0
    }

    for index, email in enumerate(
        emails,
        start=1
    ):

        print(
            f"\n\n######## EMAIL {index} "
            f"OF {len(emails)} ########"
        )

        try:

            result = process_email(
                service,
                email
            )

            if result in results:

                results[result] += 1

        except Exception as e:

            # =================================================
            # IMPORTANT:
            # One email failing must NOT stop the entire agent.
            # =================================================

            print(
                "\n❌ UNEXPECTED ERROR "
                "WHILE PROCESSING THIS EMAIL"
            )

            print(e)

            print(
                "\nThis email will remain unread."
            )

            results["failed"] += 1

            # Print technical traceback for debugging
            traceback.print_exc()

            continue

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    print(
        "\n\n"
        + "=" * 60
    )

    print(
        "PROCESSING COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"\nTotal emails found: {len(emails)}"
    )

    print(
        f"Successfully processed: "
        f"{results['success']}"
    )

    print(
        f"Skipped non-pricing emails: "
        f"{results['skipped']}"
    )

    print(
        f"Failed: "
        f"{results['failed']}"
    )

    print(
        f"Sent but not marked read: "
        f"{results['sent_not_marked']}"
    )


if __name__ == "__main__":

    main()