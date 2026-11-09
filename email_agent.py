from gmail_service import (
    get_gmail_service,
    get_unread_emails,
    send_reply,
    mark_email_as_read
)

from llm_service import (
    classify_email_intent,
    extract_cargo_details,
    get_missing_fields,
    generate_missing_info_reply,
    generate_reply
)

from rate_service import get_rate
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
    # STEP 2: EXTRACT SHIPMENT DETAILS
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

    # =====================================================
    # EXTRACT FIELDS
    # =====================================================

    origin = cargo_details.get(
        "origin"
    )

    destination = cargo_details.get(
        "destination"
    )

    shipment_mode = cargo_details.get(
        "shipment_mode"
    )

    shipment_type = cargo_details.get(
        "shipment_type"
    )

    container_count = cargo_details.get(
        "container_count"
    )

    container_type = cargo_details.get(
        "container_type"
    )

    weight_kg = cargo_details.get(
        "weight_kg"
    )

    cargo_type = cargo_details.get(
        "cargo_type"
    )

    ready_date = cargo_details.get(
        "ready_date"
    )

    volume_cbm = cargo_details.get(
        "volume_cbm"
    )

    length_cm = cargo_details.get(
    "length_cm"
    )

    width_cm = cargo_details.get(
        "width_cm"
    )

    height_cm = cargo_details.get(
        "height_cm"
    )

    pieces = cargo_details.get(
        "pieces"
    )

    # =====================================================
    # STEP 2A: CHECK MISSING INFORMATION
    # =====================================================

    print(
        "\n========== CHECKING REQUIRED INFORMATION =========="
    )

    missing_fields = get_missing_fields(
        cargo_details
    )

    print(
        "Missing fields:",
        missing_fields
    )

    # =====================================================
    # MISSING INFORMATION
    # =====================================================

    if missing_fields:

        print(
            "\n⚠️ Required shipment information is missing."
        )

        print(
            "Generating clarification email..."
        )

        clarification_reply = generate_missing_info_reply(
            email_body=email["body"],
            cargo_details=cargo_details,
            missing_fields=missing_fields
        )

        print(
            "\n========== CLARIFICATION REPLY =========="
        )

        print(
            clarification_reply
        )

        # =================================================
        # GROQ REVIEW OF CLARIFICATION
        # =================================================

        print(
            "\n========== GROQ REVIEW =========="
        )

        review_result = review_reply(
            customer_email=email["body"],
            cargo_details=cargo_details,
            pricing_result={
                "found": False,
                "match_type": "missing_information"
            },
            draft_reply=clarification_reply
        )

        print(
            json.dumps(
                review_result,
                indent=4
            )
        )

        # =================================================
        # CHECK REVIEW
        # =================================================

        if review_result.get("approved") is not True:

            print(
                "\n❌ CLARIFICATION REPLY REJECTED"
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

            print(
                "\nEmail remains unread."
            )

            return "failed"

        # =================================================
        # SEND CLARIFICATION EMAIL
        # =================================================

        print(
            "\n✅ CLARIFICATION REPLY APPROVED"
        )

        print(
            "\n========== SENDING CLARIFICATION EMAIL =========="
        )

        try:

            send_result = send_reply(
                service=service,
                email=email,
                reply_body=clarification_reply
            )

            print(
                "\n✅ Clarification reply sent successfully!"
            )

            print(
                "Sent message ID:",
                send_result["id"]
            )

        except Exception as e:

            print(
                "\n❌ ERROR SENDING CLARIFICATION REPLY"
            )

            print(e)

            print(
                "\nEmail remains unread."
            )

            return "failed"

        # =================================================
        # MARK ORIGINAL EMAIL AS READ
        # =================================================

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
                "\n⚠️ Clarification reply was sent, "
                "but the original email could not be marked as read."
            )

            print(e)

            return "sent_not_marked"

        return "success"

    # =====================================================
    # VALIDATION AFTER MISSING-FIELD CHECK
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

    if not shipment_mode:

        print(
            "\n❌ Shipment mode could not be determined."
        )

        print(
            "Email remains unread."
        )

        return "failed"

    # =====================================================
    # STEP 3: EXCEL RATE LOOKUP
    # =====================================================

    print(
        "\n========== EXCEL RATE LOOKUP =========="
    )

    print(
        "Shipment mode:",
        shipment_mode
    )

    print(
        "Origin:",
        origin
    )

    print(
        "Destination:",
        destination
    )

    if shipment_type:

        print(
            "Shipment type:",
            shipment_type
        )

    if container_type:

        print(
            "Container type:",
            container_type
        )

    if container_count:

        print(
            "Container count:",
            container_count
        )

    if weight_kg is not None:

        print(
            "Weight:",
            weight_kg,
            "KG"
        )

    print(
        "\nSearching Excel rate sheets..."
    )

    rate_result = get_rate(

        shipment_mode=shipment_mode,
        origin=origin,
        destination=destination,
        shipment_type=shipment_type,
        container_type=container_type,
        container_count=container_count,
        weight_kg=weight_kg,
        shipment_date=ready_date,
        cargo_type=cargo_type,
        length_cm=length_cm,
        width_cm=width_cm,
        height_cm=height_cm,
        pieces=pieces,
        volume_cbm=volume_cbm
    )

    print(
        "\nRATE RESULT:"
    )

    print(
        json.dumps(
            rate_result,
            indent=4,
            default=str
        )
    )

    # =====================================================
    # STEP 3A: HANDLE RATE RESULT
    # =====================================================

    match_type = rate_result.get(
        "match_type"
    )

    # -----------------------------------------------------
    # CASE 1:
    # NO RATE AT ALL
    # -----------------------------------------------------

    if not rate_result.get("found") and match_type == "none":

        print(
            "\n❌ No applicable rate found."
        )

        print(
            "Generating no-rate reply..."
        )

        # IMPORTANT:
        # We DO generate a reply here.
        # The customer should be informed that
        # no applicable rate exists.

    # -----------------------------------------------------
    # CASE 2:
    # ALTERNATIVE EXISTS BUT QUANTITY IS INVALID
    # -----------------------------------------------------

    elif (
        not rate_result.get("found")
        and match_type == "alternative_quantity_exceeded"
    ):

        print(
            "\n⚠️ Requested rate is not applicable."
        )

        print(
            "An alternative exists, but the requested "
            "quantity is outside its allowed range."
        )

    # -----------------------------------------------------
    # CASE 3:
    # EXACT RATE
    # -----------------------------------------------------

    elif match_type == "exact":

        print(
            "\n✅ EXACT RATE FOUND"
        )

    # -----------------------------------------------------
    # CASE 4:
    # VALID ALTERNATIVE RATE
    # -----------------------------------------------------

    elif match_type == "alternative":

        print(
            "\n⚠️ EXACT RATE NOT AVAILABLE"
        )

        print(
            "✅ ALTERNATIVE RATE FOUND"
        )

        print(
            "Requested:",
            rate_result.get(
                "requested_container_type"
            )
        )

        print(
            "Alternative:",
            rate_result.get(
                "alternative_container_type"
            )
        )

    # -----------------------------------------------------
    # UNKNOWN RESULT
    # -----------------------------------------------------

    else:

        print(
            "\n⚠️ Unexpected rate result."
        )

        print(
            "Email remains unread."
        )

        return "failed"

    # =====================================================
    # STEP 4: GENERATE AI REPLY
    # =====================================================

    print(
        "\n========== AI DRAFT REPLY =========="
    )

    reply = generate_reply(
        email_body=email["body"],
        cargo_details=cargo_details,
        pricing_result=rate_result
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
        pricing_result=rate_result,
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