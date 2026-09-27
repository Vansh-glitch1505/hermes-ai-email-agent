import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

client = Groq(api_key=API_KEY)


def review_reply(
    customer_email,
    cargo_details,
    price,
    currency,
    draft_reply
):
    prompt = f"""
You are a strict quality-control reviewer for a cargo shipping
customer support system.

Your job is to review an AI-generated email before it is sent
to the customer.

CUSTOMER EMAIL:
{customer_email}

EXTRACTED CARGO DETAILS:
{json.dumps(cargo_details, indent=2)}

AUTHORITATIVE DATABASE PRICE:
{price} {currency}

AI-GENERATED DRAFT:
{draft_reply}

Check the draft carefully.

You MUST verify:

1. Origin is correct.
2. Destination is correct.
3. Weight is correct.
4. The price exactly matches the database price.
5. The currency exactly matches the database currency.
6. The response answers the customer's question.
7. The response does not invent pricing, discounts,
   delivery times, guarantees, or other unsupported information.
8. The response is professional and appropriate for a customer.
9. The response does not contradict the customer email
   or the extracted information.

Return ONLY valid JSON in exactly this format:

{{
    "approved": true,
    "issues": []
}}

If there is any important problem:

{{
    "approved": false,
    "issues": [
        "description of the problem"
    ]
}}

Do not use markdown.
Do not add explanations outside the JSON.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict email quality-control "
                    "reviewer. Return only valid JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_completion_tokens=500
    )

    response_text = response.choices[0].message.content.strip()

    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "")
        response_text = response_text.replace("```", "")
        response_text = response_text.strip()

    try:
        review_result = json.loads(response_text)
    except json.JSONDecodeError:
        raise ValueError(
            f"Groq did not return valid JSON:\n{response_text}"
        )

    return review_result