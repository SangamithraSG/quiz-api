"""
ai_service.py (quiz app)

Uses Groq API (free tier) to generate quiz questions.
Groq is fast and free. Get your key at: https://console.groq.com/keys
"""

import json
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _build_prompt(topic: str, difficulty: str, count: int) -> str:
    return f"""Generate {count} multiple-choice quiz questions about "{topic}" at {difficulty} difficulty level.

Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.
Each item must have exactly these fields:
{{"question_text": "The question", "option_a": "First choice", "option_b": "Second choice", "option_c": "Third choice", "option_d": "Fourth choice", "correct_option": "A", "explanation": "Why this is correct"}}

Rules:
- correct_option must be exactly one of: A, B, C, D
- Return exactly {count} questions
- Return ONLY the JSON array, nothing else, no backticks"""


def _get_cache_key(topic: str, difficulty: str, count: int) -> str:
    safe_topic = topic.lower().replace(" ", "_")[:50]
    return f"ai_quiz_{safe_topic}_{difficulty}_{count}"


def generate_questions(topic: str, difficulty: str, count: int) -> list:
    # Check cache first
    cache_key = _get_cache_key(topic, difficulty, count)
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"Cache hit for {topic}")
        return cached

    if not settings.GEMINI_API_KEY:
        raise Exception("API key not set. Add GEMINI_API_KEY to settings.py")

    prompt = _build_prompt(topic, difficulty, count)

    # Groq API request
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are a quiz generator. Always respond with valid JSON arrays only. No markdown, no explanation, just the raw JSON array."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        raise Exception("AI service timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to AI service.")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"Groq error {status_code}: {e.response.text}")
        if status_code == 429:
            raise Exception("AI service rate limit reached. Please try again later.")
        elif status_code == 401:
            raise Exception("Invalid API key. Check your GEMINI_API_KEY in settings.py.")
        else:
            raise Exception(f"AI service error: {status_code}")

    # Parse Groq response (same format as OpenAI)
    try:
        data = response.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response: {response.text[:300]}")
        raise Exception("AI service returned unexpected format.")

    # Clean markdown if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])
    raw_text = raw_text.strip()

    # Extract JSON array
    start = raw_text.find("[")
    end = raw_text.rfind("]") + 1
    if start != -1 and end > start:
        raw_text = raw_text[start:end]

    try:
        questions = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}. Raw: {raw_text[:300]}")
        raise Exception("AI returned invalid JSON. Please try again.")

    if not isinstance(questions, list):
        raise Exception("AI returned unexpected data format.")

    # Validate questions
    required = ["question_text", "option_a", "option_b", "option_c",
                "option_d", "correct_option", "explanation"]
    valid = []
    for q in questions:
        if all(f in q for f in required):
            q["correct_option"] = str(q["correct_option"]).strip().upper()
            if q["correct_option"] in ["A", "B", "C", "D"]:
                valid.append(q)

    if not valid:
        raise Exception("AI generated no valid questions. Please try again.")

    valid = valid[:count]
    cache.set(cache_key, valid, timeout=settings.AI_CACHE_TIMEOUT)
    logger.info(f"Generated {len(valid)} questions for '{topic}'")

    return valid