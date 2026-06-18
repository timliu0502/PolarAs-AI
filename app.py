from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
KNOWLEDGE_PATH = BASE_DIR / "knowledge" / "finance_knowledge.json"

TOKEN_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")


def load_knowledge() -> list[dict[str, str]]:
    with KNOWLEDGE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
PORT = int(os.getenv("PORT", "8000"))
KNOWLEDGE = load_knowledge()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def term_vector(text: str) -> dict[str, float]:
    vector: dict[str, float] = {}
    for token in tokenize(text):
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    shared = set(a) & set(b)
    numerator = sum(a[token] * b[token] for token in shared)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return numerator / (norm_a * norm_b)


KNOWLEDGE_VECTORS = [
    term_vector(f"{item['title']} {item['content']} {' '.join(item.get('tags', []))}")
    for item in KNOWLEDGE
]


def retrieve_context(query: str, limit: int = 4) -> list[dict[str, str]]:
    query_vector = term_vector(query)
    ranked = sorted(
        zip(KNOWLEDGE, KNOWLEDGE_VECTORS),
        key=lambda pair: cosine_similarity(query_vector, pair[1]),
        reverse=True,
    )
    return [item for item, _ in ranked[:limit]]


def number_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    income = number_or_zero(profile.get("monthlyIncome"))
    fixed = number_or_zero(profile.get("fixedExpenses"))
    flexible = number_or_zero(profile.get("flexibleExpenses"))
    savings = number_or_zero(profile.get("currentSavings"))
    debt = number_or_zero(profile.get("debt"))
    goal_amount = number_or_zero(profile.get("goalAmount"))
    months = max(int(number_or_zero(profile.get("months")) or 1), 1)

    spending = fixed + flexible
    surplus = income - spending
    target_monthly = goal_amount / months if goal_amount else 0.0
    savings_rate = surplus / income if income > 0 else 0.0

    return {
        "monthly_income": income,
        "monthly_spending": spending,
        "monthly_surplus": surplus,
        "current_savings": savings,
        "debt": debt,
        "goal": profile.get("goal", "build better money habits"),
        "goal_amount": goal_amount,
        "months": months,
        "target_monthly_savings": target_monthly,
        "savings_rate": savings_rate,
        "risk_level": profile.get("riskLevel", "medium"),
    }


def format_money(value: float) -> str:
    return f"${value:,.0f}"


def offline_response(
    message: str,
    profile_summary: dict[str, Any],
    context: list[dict[str, str]],
    reason: str | None = None,
) -> str:
    surplus = profile_summary["monthly_surplus"]
    target = profile_summary["target_monthly_savings"]
    savings_rate = profile_summary["savings_rate"] * 100

    if surplus < 0:
        first_step = (
            "Your monthly cash flow is currently negative. Start by finding 1-2 flexible "
            "expenses you can reduce so your cash flow becomes positive again."
        )
    elif target and surplus < target:
        gap = target - surplus
        first_step = (
            f"Your goal requires about {format_money(target)} per month. Your current "
            f"monthly surplus is about {format_money(surplus)}, so you are short by "
            f"{format_money(gap)}. You could extend the timeline or reduce non-essential "
            "spending to close the gap."
        )
    else:
        first_step = (
            f"Your monthly surplus is about {format_money(surplus)}, and your savings "
            f"rate is about {savings_rate:.1f}%. That is enough to support a clear "
            "automatic savings plan."
        )

    retrieved = "\n".join(f"- {item['title']}: {item['content']}" for item in context[:3])
    if reason:
        intro = (
            "I am currently using offline demo mode because the OpenAI online request failed. "
            f"Reason: {reason}\n\n"
        )
    else:
        intro = (
            "I am currently in offline demo mode because `OPENAI_API_KEY` was not detected. "
        )

    return (
        f"{intro}Here is a rule-based response using the local knowledge base:\n\n"
        f"{first_step}\n\n"
        "Suggested actions:\n"
        "1. Build a small emergency fund before taking more investment risk.\n"
        "2. If you have high-interest debt, make a debt payoff plan a priority.\n"
        "3. Break the goal into a monthly amount and set up automatic transfers.\n\n"
        f"Retrieved RAG knowledge snippets:\n{retrieved}\n\n"
        "Reminder: this is not formal financial advice. It is for learning and planning drafts only."
    )


def build_prompt(
    message: str,
    profile_summary: dict[str, Any],
    context: list[dict[str, str]],
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    context_text = "\n\n".join(
        f"[{item['title']}]\n{item['content']}" for item in context
    )
    recent_history = history[-6:]
    history_text = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')}"
        for item in recent_history
    )

    developer_prompt = f"""
You are PolarAs, a student-built financial assistant for an AI summer camp demo.
You help users understand budgeting, saving, debt payoff, risk, and long-term habits.

Important safety rules:
- You are not a licensed financial advisor.
- Do not promise investment returns.
- Do not recommend buying or selling a specific security, crypto, or fund.
- Prefer education, questions, tradeoffs, and simple next steps.
- If the user asks about taxes, legal issues, emergencies, or large investments, suggest consulting a qualified professional.
- Keep answers friendly, concrete, and easy for a student to explain.
- If the user writes Chinese, answer in Chinese. If the user writes English, answer in English.

User profile summary:
{json.dumps(profile_summary, ensure_ascii=False, indent=2)}

Retrieved knowledge base context:
{context_text}

Recent chat:
{history_text}
""".strip()

    return [
        {"role": "developer", "content": developer_prompt},
        {"role": "user", "content": message},
    ]


def call_openai(messages: list[dict[str, str]]) -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    payload = {
        "model": DEFAULT_MODEL,
        "input": messages,
        "max_output_tokens": 900,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Network error while calling OpenAI: {error.reason}") from error

    if data.get("output_text"):
        return data["output_text"]

    parts: list[str] = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                parts.append(content.get("text", ""))
    text = "\n".join(part for part in parts if part).strip()
    if not text:
        raise RuntimeError("OpenAI returned no text output")
    return text


def json_response(handler: BaseHTTPRequestHandler, status: int, data: dict[str, Any]) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def static_response(handler: BaseHTTPRequestHandler, path: Path, content_type: str) -> None:
    body = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class FinanceAIHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            static_response(self, STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        static_files = {
            "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/static/polaras-logo.svg": ("polaras-logo.svg", "image/svg+xml; charset=utf-8"),
        }
        if self.path in static_files:
            filename, content_type = static_files[self.path]
            static_response(self, STATIC_DIR / filename, content_type)
            return

        if self.path == "/api/health":
            json_response(
                self,
                200,
                {
                    "ok": True,
                    "model": DEFAULT_MODEL,
                    "has_api_key": bool(os.getenv("OPENAI_API_KEY")),
                    "knowledge_items": len(KNOWLEDGE),
                },
            )
            return

        json_response(self, 404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            json_response(self, 404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            body = json.loads(raw_body or "{}")
            message = str(body.get("message", "")).strip()
            profile = body.get("profile") or {}
            history = body.get("history") or []

            if not message:
                json_response(self, 400, {"error": "Message is required"})
                return

            profile_summary = build_profile_summary(profile)
            context = retrieve_context(
                f"{message} {profile_summary['goal']} {profile_summary['risk_level']}"
            )
            prompt = build_prompt(message, profile_summary, context, history)

            try:
                answer = call_openai(prompt)
                mode = "openai"
                api_error = None
            except Exception as error:
                api_error = str(error)
                answer = offline_response(message, profile_summary, context, api_error)
                mode = "offline"
                print(f"OpenAI fallback: {error}")

            json_response(
                self,
                200,
                {
                    "answer": answer,
                    "mode": mode,
                    "model": DEFAULT_MODEL,
                    "apiError": api_error,
                    "profileSummary": profile_summary,
                    "sources": [
                        {"title": item["title"], "tags": item.get("tags", [])}
                        for item in context
                    ],
                },
            )
        except Exception as error:
            json_response(self, 500, {"error": str(error)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, PORT), FinanceAIHandler)
    if host == "0.0.0.0":
        print(f"PolarAs is listening on 0.0.0.0:{PORT}")
        print(f"Local preview: http://127.0.0.1:{PORT}")
    else:
        print(f"PolarAs is running at http://{host}:{PORT}")
    if (os.getenv("OPENAI_API_KEY") or "").strip():
        print("OPENAI_API_KEY detected. Online OpenAI responses are enabled.")
    else:
        print("OPENAI_API_KEY not detected. Offline demo mode is enabled.")
    server.serve_forever()


if __name__ == "__main__":
    main()
