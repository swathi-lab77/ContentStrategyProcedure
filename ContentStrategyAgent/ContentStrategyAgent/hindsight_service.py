import os

from hindsight_client import Hindsight


client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)


BANK_ID = "content-strategy-agent"


def remember(text):
    try:
        client.retain(
            bank_id=BANK_ID,
            content=text
        )
        return True
    except Exception as e:
        print("Hindsight retain error:", e)
        return False


def recall(query):
    try:
        result = client.recall(
            bank_id=BANK_ID,
            query=query
        )

        return str(result)

    except Exception as e:
        print("Hindsight recall error:", e)
        return ""