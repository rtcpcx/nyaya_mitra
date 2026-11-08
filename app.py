import json
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from src.config import (
    CONSTITUTION_DIR,
    DATABASE_PATH,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    OPEN_INDIA_LAW_DIR,
)
from src.database import database_stats, search_sources
from src.dataset_manager import setup_all
from src.service import respond_to_turn, respond_without_llm

st.set_page_config(
    page_title="NYAYA MITRA — Indian Legal Assistant",
    page_icon="⚖️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1040px; padding-top: 2rem; padding-bottom: 7rem;}
    [data-testid="stChatMessage"] {border: 1px solid rgba(128,128,128,.16); border-radius: 14px; padding: .8rem 1rem;}
    [data-testid="stChatInput"] {border-radius: 16px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚖️ NYAYA MITRA")
st.caption("Your Indian legal information companion. Tell me what happened, and we’ll work through it one step at a time.")
st.caption("Not a law firm or a substitute for an advocate. Do not share passwords, OTPs, full bank/card numbers or unnecessary identity details.")

st.session_state.setdefault("messages", [])
st.session_state.setdefault("last_result", None)
st.session_state.setdefault("case_location", "")
st.session_state.setdefault("response_language", "English")
st.session_state.setdefault("queued_prompt", "")

with st.sidebar:
    st.subheader("Your conversation")
    if st.button("＋ Start a new conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["last_result"] = None
        st.rerun()

    st.text_input(
        "Where is this happening?",
        key="case_location",
        placeholder="City and state, e.g. Guwahati, Assam",
        help="Location helps avoid mixing laws from different Indian states.",
    )
    st.selectbox(
        "Response language",
        ["English", "Hindi", "Assamese", "Bengali", "Tamil", "Telugu", "Marathi", "Other (specify in your message)"],
        key="response_language",
    )

    st.divider()
    st.subheader("Legal database")
    stats = database_stats(DATABASE_PATH, OPEN_INDIA_LAW_DIR, CONSTITUTION_DIR)
    if stats.get("database_exists"):
        st.success(f"Search index ready · {stats.get('indexed_rows', 0):,} records")
    else:
        st.warning("The nationwide legal database has not been indexed yet.")

    if st.button("Download / update legal database", use_container_width=True):
        progress_bar = st.progress(0)
        status = st.empty()

        def progress(message):
            status.write(message)

        try:
            with st.spinner("Downloading and indexing legal sources. The first setup can take time..."):
                result = setup_all(progress=progress)
            progress_bar.progress(100)
            st.success(f"Database ready: {result['stats']['indexed_rows']:,} records.")
            st.rerun()
        except Exception as exc:
            st.error(f"Database setup failed: {exc}")

    st.caption("The local corpus is a research index. It may be incomplete or out of date; linked official text and Gazette notifications must be checked.")
    st.caption("Chat history is session-only. Raw turn files are disabled by default; downloadable exports remain available in the developer panel.")
    st.divider()
    st.subheader("AI connection")
    provider_host = LLM_BASE_URL.split("://")[-1].split("/")[0]
    if LLM_API_KEY:
        st.success(f"Connected configuration · {provider_host}")
        st.caption(f"Model: {LLM_MODEL}")
    else:
        st.warning("No LLM API key configured. Basic intake and local source lookup remain available; AI-generated replies are disabled.")

    st.warning("For immediate danger, arrest/custody, police or court notices, hearings, deadlines or major rights, contact emergency services or a qualified local advocate promptly.")

    with st.expander("Search the legal source library"):
        manual_query = st.text_input("Search words / provision", key="manual_source_query")
        if st.button("Search source library", disabled=not manual_query.strip()):
            try:
                st.session_state["manual_source_results"] = search_sources(
                    manual_query, DATABASE_PATH, 8
                )
            except Exception as exc:
                st.error(f"Search failed: {exc}")
        for item in st.session_state.get("manual_source_results", []):
            st.markdown(f"**{item['title']} · {item.get('section') or 'Provision'}**")
            st.write(item["text"])
            st.caption(
                f"{item['source_type']} · {item['jurisdiction']} · "
                f"status: {item['status'] or 'not supplied'} · year: {item['year'] or 'not supplied'}"
            )
            if item.get("source_url"):
                st.markdown(f"[Open source document]({item['source_url']})")
            st.divider()


def render_sources(sources):
    if not sources:
        st.info("I couldn't find a sufficiently relevant passage in the local legal index for this turn. I won't guess at a specific law.")
        return
    with st.expander(f"Legal sources checked ({len(sources)})"):
        for source in sources:
            st.markdown(
                f"**{source.get('title', 'Untitled')}**"
                + (f" · {source.get('section')}" if source.get("section") else "")
            )
            st.caption(
                f"{source.get('jurisdiction', 'Jurisdiction not supplied')} · "
                f"{source.get('source_type', 'source')} · "
                f"status: {source.get('status') or 'not supplied'} · "
                f"year: {source.get('year') or 'not supplied'}"
            )
            st.write(source.get("text", ""))
            if source.get("source_url"):
                st.markdown(f"[Open source document]({source['source_url']})")
            st.divider()


def render_draft(draft):
    if draft:
        with st.expander("Requested draft · advocate review required"):
            st.warning("This is a factual starting draft, not a verified legal notice. Check every fact and have a qualified local advocate review it before sending or filing.")
            st.code(draft, language="text")


def render_suggested_actions(actions, key_prefix):
    """Render follow-up buttons that submit complete prompts to the assistant."""
    valid_actions = [
        action for action in (actions or [])
        if isinstance(action, dict)
        and str(action.get("label") or "").strip()
        and str(action.get("prompt") or "").strip()
    ][:3]
    if not valid_actions:
        return
    st.markdown("**Quick next steps**")
    columns = st.columns(len(valid_actions))
    for index, action in enumerate(valid_actions):
        with columns[index]:
            if st.button(
                str(action["label"])[:48],
                key=f"{key_prefix}_quick_action_{index}",
                use_container_width=True,
                help="Send this request directly to NYAYA MITRA",
            ):
                st.session_state["queued_prompt"] = str(action["prompt"])[:1000]
                st.rerun()


# Replay the current session's conversation.
for message_index, message in enumerate(st.session_state["messages"]):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        metadata = message.get("metadata")
        if message["role"] == "assistant" and metadata:
            if metadata.get("case_summary"):
                with st.expander("What I understand so far"):
                    st.write(metadata["case_summary"])
            if metadata.get("risk_level") in {"prompt", "urgent"}:
                st.warning(
                    "Safety triage: this may need prompt legal attention. "
                    "Please do not rely on an AI response for a deadline or formal process."
                )
            render_sources(metadata.get("retrieved_sources", []))
            render_draft(metadata.get("draft", ""))
            render_suggested_actions(
                metadata.get("suggested_actions", []),
                key_prefix=f"history_{message_index}",
            )

queued_prompt = st.session_state.pop("queued_prompt", "")
prompt = queued_prompt or st.chat_input(
    "Describe what happened, or answer the last question…",
    max_chars=12000,
)

if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.status("Understanding your situation and checking relevant sources…", expanded=False) as status:
                if LLM_API_KEY:
                    result = respond_to_turn(
                        prompt,
                        st.session_state["messages"],
                        st.session_state["case_location"],
                        st.session_state["response_language"],
                    )
                else:
                    result = respond_without_llm(
                        prompt,
                        st.session_state["messages"],
                        st.session_state["case_location"],
                    )
                status.update(label="Response ready", state="complete", expanded=False)

            assistant_text = result["reply"]
            if result.get("next_question"):
                assistant_text += "\n\n" + result["next_question"]
            st.markdown(assistant_text)

            if result.get("case_summary"):
                with st.expander("What I understand so far"):
                    st.write(result["case_summary"])
            if result.get("risk_level") in {"prompt", "urgent"}:
                st.warning(
                    "This may need prompt legal attention. Do not rely on an AI response "
                    "for a deadline, police/court process or formal filing."
                )
            render_sources(result.get("retrieved_sources", []))
            render_draft(result.get("draft", ""))

            timings = result.get("timings_ms", {})
            st.caption(
                "This turn · "
                f"retrieval {timings.get('retrieval', 0):.0f} ms · "
                f"AI generation {timings.get('generation', 0):.0f} ms · "
                f"total {timings.get('total', 0):.0f} ms"
            )

            st.session_state["messages"].append(
                {"role": "assistant", "content": assistant_text, "metadata": result}
            )
            st.session_state["last_result"] = {
                "input": prompt,
                "location": st.session_state["case_location"],
                "language": st.session_state["response_language"],
                "result": result,
            }

            # Do not persist potentially sensitive legal narratives on disk by default.
            # Enable only for a controlled local test bench with SAVE_RAW_OUTPUTS=true.
            if os.getenv("SAVE_RAW_OUTPUTS", "false").strip().casefold() == "true":
                output_dir = Path("raw_outputs")
                output_dir.mkdir(exist_ok=True)
                filename = datetime.now(timezone.utc).strftime("chat_turn_%Y%m%d_%H%M%S_%f_utc.json")
                (output_dir / filename).write_text(
                    json.dumps(st.session_state["last_result"], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            render_suggested_actions(
                result.get("suggested_actions", []),
                key_prefix="latest",
            )
        except Exception as exc:
            st.error(f"I couldn't complete this turn: {exc}")
            st.caption("Your message remains visible in this conversation. You can send it again after correcting the issue.")

latest = st.session_state.get("last_result")
if latest:
    with st.expander("Developer / test bench · raw output and timings"):
        result = latest["result"]
        st.json(
            {
                "timings_ms": result.get("timings_ms"),
                "source_mode": result.get("source_mode"),
                "risk_level": result.get("risk_level"),
                "triage": result.get("triage"),
                "case_summary": result.get("case_summary"),
                "model_output": result.get("model_output"),
                "database_note": result.get("database_note"),
            }
        )
        st.download_button(
            "Download this turn's raw JSON",
            json.dumps(latest, ensure_ascii=False, indent=2),
            file_name="nyaya_mitra_chat_turn.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Download full conversation",
            json.dumps(st.session_state["messages"], ensure_ascii=False, indent=2),
            file_name="nyaya_mitra_conversation.json",
            mime="application/json",
            use_container_width=True,
        )
