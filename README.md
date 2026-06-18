# PolarAs

A financial assistant prototype built for an AI summer camp demo. It does not train a large language model from scratch. Instead, it combines the course concepts of LLMs, prompting, corpus/RAG, vector-style similarity search, and chatbot deployment.

## What This Project Does

- The frontend collects income, expenses, savings, debt, goals, and risk comfort.
- The backend retrieves related finance knowledge snippets from `knowledge/finance_knowledge.json`.
- The retrieved snippets and user profile are sent to the OpenAI Responses API.
- If no API key is set, the app automatically uses offline demo mode so the UI and RAG flow can still be shown in class.

## How To Run

In PowerShell, enter the project folder:

```powershell
cd "C:\Users\Tim\Documents\PolarAs AI"
```

Set your OpenAI API key:

```powershell
$env:OPENAI_API_KEY="your API key"
```

You can also create a local `.env` file in this folder:

```text
OPENAI_API_KEY=your API key
OPENAI_MODEL=gpt-5.4-mini
PORT=8001
```

The `.env` file is ignored by Git, so it is safer than putting the key directly into code.

Optional: switch models. The default is `gpt-5.5`. If your account does not have access to that model, use a model your account can access:

```powershell
$env:OPENAI_MODEL="gpt-5.4-mini"
```

Start the app:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:8000
```

## Camp Demo Explanation

1. `knowledge/finance_knowledge.json` is my corpus.
2. `app.py` uses term-frequency vectors and cosine similarity as a simplified vector search system.
3. Every time the user asks a question, the system retrieves related knowledge first, then puts the snippets, budget profile, and chat history into the prompt.
4. The OpenAI model generates the natural-language response.
5. The prompt includes safety boundaries: no guaranteed returns, no specific buy/sell instructions, and no claim to be a licensed financial advisor.

## File Structure

```text
.
├── app.py
├── knowledge/
│   └── finance_knowledge.json
├── static/
│   ├── app.js
│   ├── index.html
│   └── styles.css
└── README.md
```

## Important Reminder

This project is for learning and demo purposes only. It is not formal financial advice. For real investing, tax, legal, or major financial decisions, consult a qualified professional.
