import os
import json
import base64

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]


def get_gmail_service():

    creds = None

    # =====================================================
    # RAILWAY / PRODUCTION
    # =====================================================

    railway_token = os.getenv("GMAIL_TOKEN_JSON")

    if railway_token:

        creds = Credentials.from_authorized_user_info(
            json.loads(railway_token),
            SCOPES
        )

    # =====================================================
    # LOCAL DEVELOPMENT
    # =====================================================

    elif os.path.exists("token.json"):

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # =====================================================
    # REFRESH / FIRST-TIME LOCAL AUTHENTICATION
    # =====================================================

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())

        else:

            # This should only happen locally.
            # Railway should use GMAIL_TOKEN_JSON.

            if not os.path.exists("credentials.json"):

                raise ValueError(
                    "Gmail authentication is not configured. "
                    "Set GMAIL_TOKEN_JSON in Railway variables."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(
                port=0
            )

        # Save token locally only
        if not railway_token:

            with open(
                "token.json",
                "w"
            ) as token:

                token.write(
                    creds.to_json()
                )

    # =====================================================
    # BUILD GMAIL SERVICE
    # =====================================================

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    return service


def extract_email_body(payload):

    if "parts" in payload:

        for part in payload["parts"]:

            if part["mimeType"] == "text/plain":

                data = part["body"].get("data")

                if data:

                    return base64.urlsafe_b64decode(
                        data
                    ).decode("utf-8")

            if "parts" in part:

                body = extract_email_body(part)

                if body:
                    return body

    else:

        data = payload["body"].get("data")

        if data:

            return base64.urlsafe_b64decode(
                data
            ).decode("utf-8")

    return ""


def get_unread_emails(service):

    results = service.users().messages().list(
        userId="me",
        q="in:inbox is:unread",
        maxResults=10
    ).execute()

    messages = results.get(
        "messages",
        []
    )

    emails = []

    for message_info in messages:

        message_id = message_info["id"]

        message = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
        ).execute()

        payload = message["payload"]

        headers = payload.get(
            "headers",
            []
        )

        sender = ""
        subject = ""
        message_id_header = ""
        references = ""

        for header in headers:

            name = header["name"].lower()

            if name == "from":
                sender = header["value"]

            elif name == "subject":
                subject = header["value"]

            elif name == "message-id":
                message_id_header = header["value"]

            elif name == "references":
                references = header["value"]

        body = extract_email_body(
            payload
        )

        emails.append({
            "id": message_id,
            "sender": sender,
            "subject": subject,
            "body": body,
            "message_id_header": message_id_header,
            "references": references
        })

    return emails


def send_reply(
    service,
    email,
    reply_body
):

    sender = email["sender"]

    subject = email["subject"]

    if not subject.lower().startswith("re:"):

        subject = "Re: " + subject

    message = MIMEText(
        reply_body,
        "plain",
        "utf-8"
    )

    message["To"] = sender

    message["Subject"] = subject

    if email.get("message_id_header"):

        message["In-Reply-To"] = (
            email["message_id_header"]
        )

        if email.get("references"):

            message["References"] = (
                email["references"]
                + " "
                + email["message_id_header"]
            )

        else:

            message["References"] = (
                email["message_id_header"]
            )

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    send_message = {
        "raw": raw_message,
        "threadId": email["id"]
    }

    result = service.users().messages().send(
        userId="me",
        body=send_message
    ).execute()

    return result


def mark_email_as_read(
    service,
    message_id
):

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "removeLabelIds": ["UNREAD"]
        }
    ).execute()