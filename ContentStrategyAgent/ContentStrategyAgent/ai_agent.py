import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Check the .env file inside the ContentStrategyAgent folder."
    )

client = Groq(api_key=GROQ_API_KEY)

MODEL = "openai/gpt-oss-120b"


def generate_strategy(
    company,
    industry,
    audience,
    tone,
    goal,
    previous_memory
):
    prompt = f"""
You are an AI Content Strategy Agent.

Company: {company}
Industry: {industry}
Target Audience: {audience}
Brand Tone: {tone}
Marketing Goal: {goal}

Previous knowledge from Hindsight memory:
{previous_memory}

Create a practical content strategy.

Include:
1. Content ideas
2. Recommended content types
3. Target audience approach
4. Posting strategy
5. Topics to focus on
6. Topics to avoid repeating
7. How previous performance can improve the new strategy

Keep the answer simple and well structured.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional content strategy assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI Error: {str(e)}"