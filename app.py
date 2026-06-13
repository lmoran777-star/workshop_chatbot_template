import ast
import copy
import json
import math
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

APP_ROOT = Path(__file__).parent
CONFIG_DIR = APP_ROOT / "config"
DATA_DIR = APP_ROOT / "company_data"
LOGO_DIR = APP_ROOT / "company_logo"
SUPPORTED_LOGO_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]

MODEL_ALIASES = {
    "glm5-1": "glm-5-1",
    "glm-5.1": "glm-5-1",
    "glm-5-1": "glm-5-1",
    "hypernoba": "hypernova-60b",
    "hypernova": "hypernova-60b",
    "hypernova-60b": "hypernova-60b",
}


def load_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        st.warning(f"Could not read {path.name}. Using defaults. Error: {exc}")
        return fallback


def get_secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def normalize_model(model: str) -> str:
    return MODEL_ALIASES.get(model.strip().lower(), model.strip())


def find_company_logo() -> Optional[Path]:
    """Return the first logo image saved in company_logo/."""
    if not LOGO_DIR.exists():
        return None
    for path in sorted(LOGO_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_LOGO_EXTENSIONS:
            return path
    return None


def read_text_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in [".txt", ".md", ".markdown", ".json", ".csv"]:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf" and PdfReader:
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    if suffix == ".docx" and Document:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    return ""


def read_uploaded_file(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    data = uploaded_file.getvalue()

    if suffix in [".txt", ".md", ".markdown", ".json", ".csv"]:
        return data.decode("utf-8", errors="ignore")

    temp_path = APP_ROOT / f".tmp_{uuid.uuid4().hex}{suffix}"
    try:
        temp_path.write_bytes(data)
        return read_text_file(temp_path)
    finally:
        try:
            temp_path.unlink()
        except Exception:
            pass


def chunk_text(source: str, text: str, max_chars: int = 1200) -> List[Dict[str, str]]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks = []
    for i in range(0, len(cleaned), max_chars):
        chunk = cleaned[i : i + max_chars]
        chunks.append({"source": source, "text": chunk})
    return chunks


def load_company_knowledge(uploaded_files=None) -> List[Dict[str, str]]:
    chunks: List[Dict[str, str]] = []

    if DATA_DIR.exists():
        for path in sorted(DATA_DIR.iterdir()):
            if path.name.startswith(".") or path.is_dir():
                continue
            text = read_text_file(path)
            chunks.extend(chunk_text(path.name, text))

    if uploaded_files:
        for uploaded in uploaded_files:
            text = read_uploaded_file(uploaded)
            chunks.extend(chunk_text(uploaded.name, text))

    return chunks


def tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9_]{3,}", text.lower())
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "are", "you", "your", "our",
        "para", "por", "con", "que", "los", "las", "una", "uno", "del", "como", "esta", "este",
    }
    return {w for w in words if w not in stop}


def search_chunks(query: str, chunks: List[Dict[str, str]], top_k: int = 4) -> List[Dict[str, str]]:
    q = tokenize(query)
    if not q or not chunks:
        return []

    scored: List[Tuple[int, Dict[str, str]]] = []
    for chunk in chunks:
        t = tokenize(chunk["text"])
        score = len(q.intersection(t))
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def estimate_tokens(text: str) -> int:
    """Tiny workshop-friendly estimate. Real counts depend on the model tokenizer."""
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        total += estimate_tokens(str(msg.get("role", "")))
        total += estimate_tokens(str(msg.get("content", "")))
        if msg.get("tool_calls"):
            total += estimate_tokens(json.dumps(msg.get("tool_calls"), ensure_ascii=False))
    return total


def estimate_tools_tokens(tools: List[Dict[str, Any]]) -> int:
    if not tools:
        return 0
    return estimate_tokens(json.dumps(tools, ensure_ascii=False))


def build_system_prompt(company: Dict[str, Any], personality: Dict[str, Any], model_cfg: Dict[str, Any]) -> str:
    lines = [
        f"You are {company.get('bot_name', 'the assistant')}.",
        f"Company/project: {company.get('company_name', 'Student company')}.",
        f"Bot goal: {company.get('bot_goal', 'Help users with questions about the company.')}.",
        f"Target users: {company.get('target_users', 'Customers or employees')}.",
        f"Main product/service: {company.get('product_service', 'Not specified')}.",
        "",
        "Personality and answer style:",
        f"- Role: {personality.get('role', 'Helpful company assistant')}",
        f"- Tone: {personality.get('tone', 'friendly and clear')}",
        f"- Language: {personality.get('language', 'same language as the user')}",
        f"- Answer length: {personality.get('answer_length', 'short but complete')}",
    ]

    for item in personality.get("do", []):
        lines.append(f"- Do: {item}")
    for item in personality.get("dont", []):
        lines.append(f"- Do not: {item}")
    for item in personality.get("safety_rules", []):
        lines.append(f"- Safety rule: {item}")

    lines.extend([
        "",
        "Use the company knowledge snippets when they are relevant.",
        "If you do not know the answer from the information available, say so clearly and suggest the next best step.",
        "Do not invent company policies, prices, legal conditions, or technical procedures.",
    ])

    if model_cfg.get("workshop_mode", True):
        lines.append("This is a workshop prototype, not a production system.")

    return "\n".join(lines)


ALLOWED_MATH_NAMES = {
    name: getattr(math, name)
    for name in [
        "ceil", "floor", "sqrt", "sin", "cos", "tan", "log", "log10", "exp", "pow", "pi", "e"
    ]
}


def safe_calculator(expression: str) -> str:
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant, ast.Add, ast.Sub,
        ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.Load, ast.Call, ast.Name,
    )
    try:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return "Calculator error: expression contains unsupported syntax."
            if isinstance(node, ast.Name) and node.id not in ALLOWED_MATH_NAMES:
                return f"Calculator error: unsupported name '{node.id}'."
        result = eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, ALLOWED_MATH_NAMES)
        return str(result)
    except Exception as exc:
        return f"Calculator error: {exc}"


def execute_tool(name: str, arguments: Dict[str, Any], chunks: List[Dict[str, str]], company: Dict[str, Any]) -> str:
    if name == "calculator":
        return safe_calculator(str(arguments.get("expression", "")))

    if name == "current_datetime":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if name == "search_company_data":
        query = str(arguments.get("query", ""))
        results = search_chunks(query, chunks, top_k=4)
        if not results:
            return "No relevant company data found."
        return "\n\n".join(f"Source: {r['source']}\n{r['text']}" for r in results)

    if name == "create_support_ticket":
        issue = str(arguments.get("issue_summary", "No summary provided"))
        email = str(arguments.get("user_email", "not provided"))
        ticket_id = "TICKET-" + uuid.uuid4().hex[:8].upper()
        return (
            f"Created demo support ticket {ticket_id}. "
            f"Issue: {issue}. User email: {email}. "
            f"Escalation contact: {company.get('contact_email', 'not configured')}."
        )

    return f"Unknown tool: {name}"


def build_tools(tools_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    available = []
    tools = tools_cfg.get("tools", {})

    if tools.get("calculator", {}).get("enabled", False):
        available.append({
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Calculate a simple math expression, such as prices, discounts, or measurements.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "A simple math expression, for example '120*0.21'"}
                    },
                    "required": ["expression"],
                },
            },
        })

    if tools.get("current_datetime", {}).get("enabled", False):
        available.append({
            "type": "function",
            "function": {
                "name": "current_datetime",
                "description": "Get the current date and time.",
                "parameters": {"type": "object", "properties": {}},
            },
        })

    if tools.get("search_company_data", {}).get("enabled", False):
        available.append({
            "type": "function",
            "function": {
                "name": "search_company_data",
                "description": "Search uploaded company documents for relevant information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for in the company documents"}
                    },
                    "required": ["query"],
                },
            },
        })

    if tools.get("create_support_ticket", {}).get("enabled", False):
        available.append({
            "type": "function",
            "function": {
                "name": "create_support_ticket",
                "description": "Create a demo support ticket when a user needs human help.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_summary": {"type": "string", "description": "Short summary of the problem"},
                        "user_email": {"type": "string", "description": "User email if they provided one"},
                    },
                    "required": ["issue_summary"],
                },
            },
        })

    return available


def active_tool_names(tools_cfg: Dict[str, Any]) -> List[str]:
    return [name for name, cfg in tools_cfg.get("tools", {}).items() if cfg.get("enabled")]


def make_runtime_tools_config(tools_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Let students toggle tools from the UI without editing JSON permanently."""
    runtime_cfg = copy.deepcopy(tools_cfg)
    tool_items = runtime_cfg.get("tools", {})

    if "tool_enabled_overrides" not in st.session_state:
        st.session_state.tool_enabled_overrides = {
            name: bool(cfg.get("enabled", False)) for name, cfg in tool_items.items()
        }

    for name, cfg in tool_items.items():
        if name not in st.session_state.tool_enabled_overrides:
            st.session_state.tool_enabled_overrides[name] = bool(cfg.get("enabled", False))
        cfg["enabled"] = bool(st.session_state.tool_enabled_overrides[name])

    return runtime_cfg


def compactif_chat(
    messages: List[Dict[str, Any]],
    model_cfg: Dict[str, Any],
    tools: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    api_key = get_secret("COMPACTIF_API_KEY")
    base_url = get_secret("COMPACTIF_BASE_URL", model_cfg.get("base_url", "https://api.compactif.ai/v1"))
    model = normalize_model(model_cfg.get("default_model", "glm-5-1"))
    started = time.perf_counter()

    if not api_key:
        content = (
            "Demo mode: add COMPACTIF_API_KEY in Streamlit secrets to connect the real model. "
            "I can still show the UI flow, tool toggles, logo, and configuration structure."
        )
        latency = time.perf_counter() - started
        estimated_prompt = estimate_messages_tokens(messages) + estimate_tools_tokens(tools)
        estimated_completion = estimate_tokens(content)
        return {
            "demo_mode": True,
            "content": content,
        }, {
            "response_time_s": latency,
            "prompt_tokens": estimated_prompt,
            "completion_tokens": estimated_completion,
            "total_tokens": estimated_prompt + estimated_completion,
            "usage_source": "estimated",
            "model": model,
            "api_calls": 0,
        }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(model_cfg.get("temperature", 0.4)),
        "max_tokens": int(model_cfg.get("max_tokens", 800)),
    }

    if tools and model_cfg.get("use_tools", True):
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    latency = time.perf_counter() - started

    if response.status_code >= 400:
        raise RuntimeError(f"Compactif API error {response.status_code}: {response.text[:500]}")

    data = response.json()
    message = data["choices"][0]["message"]
    usage = data.get("usage") or {}

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    usage_source = "api" if total_tokens is not None else "estimated"

    if total_tokens is None:
        prompt_tokens = estimate_messages_tokens(messages) + estimate_tools_tokens(tools)
        completion_tokens = estimate_tokens(str(message.get("content", "")))
        if message.get("tool_calls"):
            completion_tokens += estimate_tokens(json.dumps(message.get("tool_calls"), ensure_ascii=False))
        total_tokens = prompt_tokens + completion_tokens

    return message, {
        "response_time_s": latency,
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
        "usage_source": usage_source,
        "model": model,
        "api_calls": 1,
    }


def merge_metrics(total: Dict[str, Any], part: Dict[str, Any]) -> Dict[str, Any]:
    total["response_time_s"] = float(total.get("response_time_s", 0)) + float(part.get("response_time_s", 0))
    total["prompt_tokens"] = int(total.get("prompt_tokens", 0)) + int(part.get("prompt_tokens", 0))
    total["completion_tokens"] = int(total.get("completion_tokens", 0)) + int(part.get("completion_tokens", 0))
    total["total_tokens"] = int(total.get("total_tokens", 0)) + int(part.get("total_tokens", 0))
    total["api_calls"] = int(total.get("api_calls", 0)) + int(part.get("api_calls", 0))
    if part.get("usage_source") != "api":
        total["usage_source"] = "estimated"
    total["model"] = part.get("model", total.get("model"))
    return total


def chat_with_tools(
    messages: List[Dict[str, Any]],
    model_cfg: Dict[str, Any],
    tools: List[Dict[str, Any]],
    chunks: List[Dict[str, str]],
    company: Dict[str, Any],
    tool_names: List[str],
    max_rounds: int = 3,
) -> Tuple[str, Dict[str, Any]]:
    current_messages = list(messages)
    metrics = {
        "response_time_s": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "usage_source": "api",
        "api_calls": 0,
        "model": normalize_model(model_cfg.get("default_model", "glm-5-1")),
        "tools_sent": tool_names,
        "tools_called": [],
    }

    for _ in range(max_rounds):
        message, part_metrics = compactif_chat(current_messages, model_cfg, tools)
        metrics = merge_metrics(metrics, part_metrics)

        if isinstance(message, dict) and message.get("demo_mode"):
            metrics["usage_source"] = "estimated"
            return message["content"], metrics

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content") or "I could not generate a response.", metrics

        current_messages.append(message)
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            raw_args = fn.get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except Exception:
                args = {}

            metrics["tools_called"].append(name)
            result = execute_tool(name, args, chunks, company)
            current_messages.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "name": name,
                "content": result,
            })

    return "I used the available tools, but I need a bit more information to finish the answer.", metrics


def metrics_text(metrics: Optional[Dict[str, Any]]) -> str:
    if not metrics:
        return ""
    source = "real API usage" if metrics.get("usage_source") == "api" else "estimated tokens"
    tools_sent = metrics.get("tools_sent") or []
    tools_called = metrics.get("tools_called") or []
    called_text = ", ".join(tools_called) if tools_called else "none"
    return (
        f"⏱️ {metrics.get('response_time_s', 0):.2f}s · "
        f"🧮 {metrics.get('total_tokens', 0)} tokens ({source}) · "
        f"prompt {metrics.get('prompt_tokens', 0)} / completion {metrics.get('completion_tokens', 0)} · "
        f"model {metrics.get('model', 'unknown')} · "
        f"tools sent {len(tools_sent)} · tools called: {called_text}"
    )


def reset_chat(welcome: str):
    st.session_state.messages = [{"role": "assistant", "content": welcome}]


def main():
    st.set_page_config(page_title="Workshop Chatbot Template", page_icon="🤖", layout="centered")

    company = load_json(CONFIG_DIR / "company.json", {})
    personality = load_json(CONFIG_DIR / "personality.json", {})
    tools_cfg = load_json(CONFIG_DIR / "tools.json", {})
    model_cfg = load_json(CONFIG_DIR / "model.json", {})
    runtime_tools_cfg = make_runtime_tools_config(tools_cfg)

    logo_path = find_company_logo()

    with st.sidebar:
        st.header("Workshop controls")
        selected_model = st.selectbox(
            "Model",
            ["glm-5-1", "hypernova-60b"],
            index=0 if normalize_model(model_cfg.get("default_model", "glm-5-1")) == "glm-5-1" else 1,
        )
        model_cfg["default_model"] = selected_model

        st.write("**Company**")
        st.write(company.get("company_name", "Student company"))

        st.write("**Logo**")
        uploaded_logo = st.file_uploader(
            "Temporary logo preview",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=False,
            help="For a permanent logo, save an image in the company_logo folder in the GitHub repo.",
        )
        if uploaded_logo is not None:
            st.session_state.preview_logo = uploaded_logo.getvalue()
            st.session_state.preview_logo_name = uploaded_logo.name
        if logo_path:
            st.caption(f"Permanent logo loaded: company_logo/{logo_path.name}")
        else:
            st.caption("No permanent logo yet. Add one image to company_logo/.")

        st.write("**Tool toggles**")
        st.caption("Turn tools on/off and ask the same question again to compare tokens and response time.")
        for name, cfg in tools_cfg.get("tools", {}).items():
            default_value = bool(st.session_state.tool_enabled_overrides.get(name, cfg.get("enabled", False)))
            st.session_state.tool_enabled_overrides[name] = st.checkbox(
                name,
                value=default_value,
                help=cfg.get("student_note", ""),
                key=f"toggle_{name}",
            )

        runtime_tools_cfg = make_runtime_tools_config(tools_cfg)
        enabled = active_tool_names(runtime_tools_cfg)
        st.write("**Enabled now**")
        st.write(", ".join(enabled) if enabled else "No tools enabled")

        if st.button("Reset chat"):
            reset_chat(company.get("welcome_message", "Hello! How can I help?"))

        st.info("Edit JSON files in /config, add data to /company_data, and add a logo to /company_logo.")

    if st.session_state.get("preview_logo"):
        st.image(st.session_state.preview_logo, width=96)
    elif logo_path:
        st.image(str(logo_path), width=96)

    st.title(company.get("bot_name", "Workshop Chatbot"))
    st.caption(company.get("bot_goal", "A simple chatbot template students can personalize."))

    uploaded_files = st.file_uploader(
        "Optional: upload company files for this session",
        type=["txt", "md", "json", "csv", "pdf", "docx"],
        accept_multiple_files=True,
        help="For permanent data, add files to the company_data folder in the repository.",
    )

    chunks = load_company_knowledge(uploaded_files)
    st.caption(f"Loaded {len(chunks)} knowledge chunks from company_data and uploaded files.")

    if "messages" not in st.session_state:
        reset_chat(company.get("welcome_message", "Hello! How can I help?"))

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            caption = metrics_text(msg.get("metrics"))
            if caption:
                st.caption(caption)

    user_input = st.chat_input("Ask the bot something...")
    if not user_input:
        return

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    relevant = search_chunks(user_input, chunks, top_k=4)
    knowledge_block = ""
    if relevant:
        knowledge_block = "\n\nRelevant company knowledge snippets:\n" + "\n\n".join(
            f"Source: {r['source']}\n{r['text']}" for r in relevant
        )

    system_prompt = build_system_prompt(company, personality, model_cfg) + knowledge_block

    api_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    api_messages.extend([
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages[-10:]
    ])

    tools = build_tools(runtime_tools_cfg)
    tool_names = active_tool_names(runtime_tools_cfg)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, metrics = chat_with_tools(
                    api_messages,
                    model_cfg,
                    tools,
                    chunks,
                    company,
                    tool_names,
                )
            except Exception as exc:
                answer = f"There was an error calling the model: {exc}"
                metrics = {
                    "response_time_s": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "usage_source": "estimated",
                    "api_calls": 0,
                    "model": normalize_model(model_cfg.get("default_model", "glm-5-1")),
                    "tools_sent": tool_names,
                    "tools_called": [],
                }
            st.markdown(answer)
            st.caption(metrics_text(metrics))

    st.session_state.messages.append({"role": "assistant", "content": answer, "metrics": metrics})


if __name__ == "__main__":
    main()
