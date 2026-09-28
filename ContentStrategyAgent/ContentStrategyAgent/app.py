import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Hindsight
try:
    from hindsight_client import Hindsight
except ImportError:
    Hindsight = None

# Groq
try:
    from groq import Groq
except ImportError:
    Groq = None


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

HINDSIGHT_API_URL = os.getenv(
    "HINDSIGHT_API_URL",
    "https://api.hindsight.vectorize.io"
).strip()

HINDSIGHT_API_KEY = os.getenv(
    "HINDSIGHT_API_KEY",
    ""
).strip()

HINDSIGHT_BANK_ID = os.getenv(
    "HINDSIGHT_BANK_ID",
    "content-strategy-agent"
).strip()

DATABASE = "content_strategy.db"


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            topic TEXT NOT NULL,
            content_type TEXT NOT NULL,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# HINDSIGHT CONNECTION
# ============================================================

def get_hindsight_client():
    """
    Creates the Hindsight client.

    Hindsight Cloud uses:
        https://api.hindsight.vectorize.io

    The API key is read from HINDSIGHT_API_KEY.
    """

    if Hindsight is None:
        return None

    if not HINDSIGHT_API_KEY:
        return None

    try:
        client = Hindsight(
            base_url=HINDSIGHT_API_URL,
            api_key=HINDSIGHT_API_KEY,
            timeout=30.0
        )

        return client

    except Exception as e:
        print("Hindsight connection error:", e)
        return None


def setup_hindsight_bank():
    """
    Makes sure the Hindsight memory bank exists.

    If the bank already exists, the error is safely ignored.
    """

    client = get_hindsight_client()

    if client is None:
        print("Hindsight is not configured.")
        return

    try:
        client.create_bank(
            bank_id=HINDSIGHT_BANK_ID,
            name="Content Strategy Agent"
        )

        print("Hindsight memory bank created.")

    except Exception as e:
        # Usually means the bank already exists.
        print("Hindsight bank setup:", e)


# ============================================================
# SAVE CONTENT TO HINDSIGHT
# ============================================================

def save_content_to_hindsight(
    title,
    topic,
    content_type,
    views,
    likes,
    comments,
    shares
):
    """
    Sends published content + performance data to Hindsight.

    This is the important part:
        SQLite = application database
        Hindsight = AI memory
    """

    client = get_hindsight_client()

    if client is None:
        return False, "Hindsight is not configured."

    memory_text = f"""
Published content performance record.

Title: {title}
Topic: {topic}
Content type: {content_type}

Performance:
Views: {views}
Likes: {likes}
Comments: {comments}
Shares: {shares}

This content was published by the Content Strategy Agent.
Use this information as historical content-performance memory
when creating future content strategies.
""".strip()

    try:
        document_id = "content_" + str(abs(hash(
            f"{title}|{topic}|{content_type}"
        )))

        client.retain(
            bank_id=HINDSIGHT_BANK_ID,
            content=memory_text,
            context="Published content performance history",
            document_id=document_id,
            retain_async=False
        )

        print("Content successfully retained in Hindsight.")

        return True, "Saved to Hindsight."

    except Exception as e:
        print("Hindsight retain error:", e)
        return False, str(e)


# ============================================================
# RECALL CONTENT FROM HINDSIGHT
# ============================================================

def recall_hindsight_memory(
    company,
    industry,
    audience,
    goal
):
    """
    Searches Hindsight for previous content performance
    relevant to the requested strategy.
    """

    client = get_hindsight_client()

    if client is None:
        return "Hindsight is not configured."

    query = f"""
Find previous published content and performance information
that can help create a content strategy.

Company: {company}
Industry: {industry}
Target audience: {audience}
Goal: {goal}

Look for:
- previous content topics
- content formats
- views
- likes
- comments
- shares
- patterns in successful content
- patterns in weaker content
""".strip()

    try:
        result = client.recall(
            bank_id=HINDSIGHT_BANK_ID,
            query=query,
            max_tokens=4000,
            budget="mid"
        )

        if not result.results:
            return "No previous content-performance memory found in Hindsight."

        memories = []

        for memory in result.results:
            text_value = getattr(memory, "text", None)

            if text_value:
                memory_type = getattr(memory, "type", "")
                if memory_type:
                    memories.append(
                        f"[{memory_type}] {text_value}"
                    )
                else:
                    memories.append(text_value)

        if not memories:
            return "No previous content-performance memory found in Hindsight."

        return "\n\n".join(memories)

    except Exception as e:
        print("Hindsight recall error:", e)
        return f"Hindsight recall error: {str(e)}"


# ============================================================
# GROQ
# ============================================================

def generate_ai_strategy(
    company,
    industry,
    audience,
    tone,
    goal,
    memory
):
    """
    Uses Groq to generate the actual content strategy.

    Hindsight memory is supplied to Groq as historical context.
    """

    if Groq is None:
        raise Exception(
            "Groq package is not installed. Run: pip install groq"
        )

    if not GROQ_API_KEY:
        raise Exception(
            "GROQ_API_KEY is missing from your .env file."
        )

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are an AI Content Strategy Agent.

Create a practical content strategy using the user's
requirements AND the historical performance memory from Hindsight.

USER REQUIREMENTS
-----------------
Company: {company}
Industry: {industry}
Target Audience: {audience}
Tone: {tone}
Goal: {goal}

HINDSIGHT MEMORY
----------------
{memory}

IMPORTANT:
- Use the historical memory when relevant.
- Identify patterns from previous content.
- Do not invent performance numbers that are not present.
- Clearly distinguish historical observations from new recommendations.
- Make the strategy practical and specific.
- Focus on social media/content marketing.
- Keep the answer easy to understand.

Return the strategy using this structure:

1. CONTENT STRATEGY
2. WHAT THE PAST DATA TELLS US
3. CONTENT PILLARS
4. RECOMMENDED CONTENT TYPES
5. CONTENT IDEAS
6. POSTING PLAN
7. HOW TO IMPROVE PERFORMANCE
8. KEY METRICS TO TRACK
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful AI content strategy expert "
                    "who uses historical performance data to create "
                    "evidence-informed content plans."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=2500
    )

    return response.choices[0].message.content


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# ADD PUBLISHED CONTENT
# ============================================================

@app.route("/api/add-content", methods=["POST"])
def add_content():

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data received."
            }), 400

        title = str(data.get("title", "")).strip()
        topic = str(data.get("topic", "")).strip()
        content_type = str(data.get("content_type", "")).strip()
        performance = str(data.get("performance", "")).strip()

        if not title or not topic or not content_type or not performance:
            return jsonify({
                "success": False,
                "error": "Please fill all fields."
            }), 400

        # ----------------------------------------------------
        # Parse performance input
        #
        # Supported examples:
        #
        # 50000,4200,350,250
        #
        # OR:
        # {"views":50000,"likes":4200,"comments":350,"shares":250}
        # ----------------------------------------------------

        views = 0
        likes = 0
        comments = 0
        shares = 0

        # Try JSON first
        try:
            performance_data = json.loads(performance)

            if isinstance(performance_data, dict):
                views = int(performance_data.get("views", 0))
                likes = int(performance_data.get("likes", 0))
                comments = int(performance_data.get("comments", 0))
                shares = int(performance_data.get("shares", 0))

        except Exception:
            # Try comma-separated numbers
            parts = [
                part.strip()
                for part in performance.split(",")
            ]

            if len(parts) >= 4:
                views = int(parts[0])
                likes = int(parts[1])
                comments = int(parts[2])
                shares = int(parts[3])

            else:
                # Try key=value format
                # Example:
                # views=50000, likes=4200, comments=350, shares=250

                performance_lower = performance.lower()

                for part in parts:
                    if "=" not in part:
                        continue

                    key, value = part.split("=", 1)

                    key = key.strip().lower()
                    value = value.strip()

                    try:
                        value = int(value)
                    except ValueError:
                        value = 0

                    if key == "views":
                        views = value

                    elif key == "likes":
                        likes = value

                    elif key == "comments":
                        comments = value

                    elif key == "shares":
                        shares = value

        # ----------------------------------------------------
        # Save to SQLite
        # ----------------------------------------------------

        conn = get_db()

        cursor = conn.execute("""
            INSERT INTO content
            (
                title,
                topic,
                content_type,
                views,
                likes,
                comments,
                shares
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            topic,
            content_type,
            views,
            likes,
            comments,
            shares
        ))

        content_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # ----------------------------------------------------
        # IMPORTANT:
        # Save the same content to Hindsight
        # ----------------------------------------------------

        hindsight_saved, hindsight_message = save_content_to_hindsight(
            title=title,
            topic=topic,
            content_type=content_type,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares
        )

        return jsonify({
            "success": True,
            "message": "Content saved successfully.",
            "content_id": content_id,
            "hindsight_saved": hindsight_saved,
            "hindsight_message": hindsight_message
        })

    except ValueError:
        return jsonify({
            "success": False,
            "error": (
                "Performance numbers must be numbers. "
                "Example: 50000,4200,350,250"
            )
        }), 400

    except Exception as e:
        print("Add content error:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# GET SAVED CONTENT
# ============================================================

@app.route("/api/content", methods=["GET"])
def get_content():

    try:
        conn = get_db()

        rows = conn.execute("""
            SELECT
                id,
                title,
                topic,
                content_type,
                views,
                likes,
                comments,
                shares
            FROM content
            ORDER BY id DESC
        """).fetchall()

        conn.close()

        # Return arrays because your current frontend
        # uses item[1], item[2], etc.
        content_list = []

        for row in rows:
            content_list.append([
                row["id"],
                row["title"],
                row["topic"],
                row["content_type"],
                row["views"],
                row["likes"],
                row["comments"],
                row["shares"]
            ])

        return jsonify({
            "success": True,
            "content": content_list
        })

    except Exception as e:
        print("Get content error:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# GENERATE STRATEGY
# ============================================================

@app.route("/api/strategy", methods=["POST"])
def strategy():

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No strategy data received."
            }), 400

        company = str(data.get("company", "")).strip()
        industry = str(data.get("industry", "")).strip()
        audience = str(data.get("audience", "")).strip()
        tone = str(data.get("tone", "")).strip()
        goal = str(data.get("goal", "")).strip()

        if not company:
            return jsonify({
                "success": False,
                "error": "Company is required."
            }), 400

        if not industry:
            return jsonify({
                "success": False,
                "error": "Industry is required."
            }), 400

        if not audience:
            return jsonify({
                "success": False,
                "error": "Audience is required."
            }), 400

        if not tone:
            return jsonify({
                "success": False,
                "error": "Tone is required."
            }), 400

        if not goal:
            return jsonify({
                "success": False,
                "error": "Goal is required."
            }), 400

        # ----------------------------------------------------
        # STEP 1
        # Recall previous content from Hindsight
        # ----------------------------------------------------

        memory = recall_hindsight_memory(
            company=company,
            industry=industry,
            audience=audience,
            goal=goal
        )

        print("\n========== HINDSIGHT MEMORY ==========")
        print(memory)
        print("======================================\n")

        # ----------------------------------------------------
        # STEP 2
        # Ask Groq to create strategy using memory
        # ----------------------------------------------------

        generated_strategy = generate_ai_strategy(
            company=company,
            industry=industry,
            audience=audience,
            tone=tone,
            goal=goal,
            memory=memory
        )

        # ----------------------------------------------------
        # Return both strategy + memory to frontend
        # ----------------------------------------------------

        return jsonify({
            "success": True,
            "strategy": generated_strategy,
            "memory": memory
        })

    except Exception as e:
        print("Strategy generation error:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# HINDSIGHT TEST ENDPOINT
# ============================================================

@app.route("/api/hindsight-test", methods=["GET"])
def hindsight_test():

    client = get_hindsight_client()

    if client is None:
        return jsonify({
            "success": False,
            "message": (
                "Hindsight client is not configured. "
                "Check HINDSIGHT_API_KEY and hindsight-client."
            )
        })

    try:
        result = client.recall(
            bank_id=HINDSIGHT_BANK_ID,
            query="previous published content performance"
        )

        memories = []

        for item in result.results:
            text_value = getattr(item, "text", None)

            if text_value:
                memories.append(text_value)

        return jsonify({
            "success": True,
            "bank_id": HINDSIGHT_BANK_ID,
            "memory_count": len(memories),
            "memories": memories
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    print("")
    print("==========================================")
    print("   CONTENT STRATEGY AGENT")
    print("==========================================")
    print("")

    # Create SQLite database/table
    init_database()

    # Try to prepare Hindsight bank
    setup_hindsight_bank()

    print("Database:", DATABASE)
    print("Hindsight URL:", HINDSIGHT_API_URL)
    print("Hindsight Bank:", HINDSIGHT_BANK_ID)

    if GROQ_API_KEY:
        print("Groq API key: configured")
    else:
        print("WARNING: GROQ_API_KEY is missing")

    if HINDSIGHT_API_KEY:
        print("Hindsight API key: configured")
    else:
        print("WARNING: HINDSIGHT_API_KEY is missing")

    print("")
    print("Open this in your browser:")
    print("http://127.0.0.1:5000")
    print("")
    print("==========================================")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )