import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_db_connection():

    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    return connection


def get_price(origin, destination, weight_kg, cargo_type=None):

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        query = """
            SELECT
                price,
                currency
            FROM pricing
            WHERE LOWER(origin) = LOWER(%s)
              AND LOWER(destination) = LOWER(%s)
              AND min_weight <= %s
              AND max_weight >= %s
            ORDER BY id
            LIMIT 1;
        """

        cursor.execute(
            query,
            (
                origin,
                destination,
                weight_kg,
                weight_kg
            )
        )

        result = cursor.fetchone()

        cursor.close()

        if result:
            price, currency = result

            return {
                "price": price,
                "currency": currency
            }

        return None

    finally:

        connection.close()


if __name__ == "__main__":

    result = get_price(
        "Mumbai",
        "Dubai",
        25
    )

    print("\n========== DATABASE RESULT ==========")

    print(result)