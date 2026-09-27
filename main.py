import time
import traceback

from gmail_service import get_gmail_service
from email_agent import process_email
from gmail_service import get_unread_emails


# =========================================================
# SETTINGS
# =========================================================

CHECK_INTERVAL = 300   # Check Gmail every 60 seconds


# =========================================================
# PROCESS UNREAD EMAILS
# =========================================================

def check_for_new_emails(service):

    print("\n" + "=" * 60)
    print("CHECKING FOR NEW EMAILS")
    print("=" * 60)

    try:

        emails = get_unread_emails(service)

        if not emails:

            print("No unread emails found.")

            return

        print(
            f"Found {len(emails)} unread email(s)."
        )

        # -------------------------------------------------
        # Process every unread email
        # -------------------------------------------------

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

                print(
                    f"\nResult: {result}"
                )

            except Exception as e:

                print(
                    "\n❌ ERROR PROCESSING EMAIL"
                )

                print(e)

                print(
                    "\nEmail will remain unread."
                )

                traceback.print_exc()

                continue

    except Exception as e:

        print(
            "\n❌ ERROR CHECKING GMAIL"
        )

        print(e)

        traceback.print_exc()


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print("\n")
    print("=" * 60)
    print("AI CARGO EMAIL AGENT")
    print("=" * 60)

    print(
        "\nConnecting to Gmail..."
    )

    service = get_gmail_service()

    print(
        "✅ Gmail connected successfully."
    )

    print(
        f"\nAgent is now running continuously."
    )

    print(
        f"Checking for new emails every "
        f"{CHECK_INTERVAL} seconds."
    )

    print(
        "\nPress CTRL + C to stop the agent."
    )

    while True:

        try:

            check_for_new_emails(
                service
            )

            print(
                f"\nWaiting {CHECK_INTERVAL} seconds "
                f"before the next check..."
            )

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "\n\nAgent stopped by user."
            )

            break

        except Exception as e:

            print(
                "\n❌ UNEXPECTED ERROR "
                "IN MAIN LOOP"
            )

            print(e)

            traceback.print_exc()

            print(
                "\nAgent will continue running..."
            )

            time.sleep(
                CHECK_INTERVAL
            )


# =========================================================
# START AGENT
# =========================================================

if __name__ == "__main__":

    main()