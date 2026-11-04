from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


def main() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    model = (os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b").strip()

    if not api_key:
        print("FAIL: GROQ_API_KEY is missing in .env")
        return
    if not api_key.startswith("gsk_"):
        print("FAIL: GROQ_API_KEY format looks invalid (expected prefix: gsk_)")
        return

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: GROQ_OK"}],
            temperature=0,
            max_tokens=10,
        )
        content = (response.choices[0].message.content or "").strip()
        print("PASS: Groq API key is valid.")
        print(f"Model: {model}")
        print(f"Response: {content}")
    except Exception as exc:
        print("FAIL: Groq API call failed.")
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
