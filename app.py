import json
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from src.config import DATABASE_PATH, LLM_API_KEY, OPEN_INDIA_LAW_DIR, CONSTITUTION_DIR
from src.database import database_stats, search_sources
from src.dataset_manager import setup_all
from src.service import analyze_problem, analyze_without_llm
from src.triage import triage_text

st.set_page_config(page_title="Nyaya Mitra — Indian Legal Assistant", page_icon="⚖️", layout="wide")
st.title("⚖️ Nyaya Mitra")
st.caption("A nationwide Indian legal information assistant. Not a substitute for an advocate.")

with st.sidebar:
    st.subheader("Legal database")
    stats=database_stats(DATABASE_PATH,OPEN_INDIA_LAW_DIR,CONSTITUTION_DIR)
    if stats.get("database_exists"):
        st.success(f"Search index ready · {stats.get('indexed_rows',0):,} records")
        st.caption("Source types: " + ", ".join(f"{k}: {v:,}" for k,v in stats.get("source_types",{}).items()))
    else:
        st.warning("Nationwide database has not been indexed yet.")
    if st.button("Download and index nationwide legal database", type="primary", use_container_width=True):
        bar=st.progress(0)
        status=st.empty()
        def progress(message): status.write(message)
        try:
            with st.spinner("Downloading and indexing. This can take a while on the first run..."):
                result=setup_all(progress=progress)
            bar.progress(100)
            st.success(f"Database ready: {result['stats']['indexed_rows']:,} indexed rows.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    st.caption("Default download includes central/state legislation, regulator material and Constitution. Court judgments are optional and very large.")
    st.divider()
    st.subheader("AI connection")
    if LLM_API_KEY:
        st.success("Groq API key detected")
    else:
        st.warning("Groq key not configured. Database search works; AI-generated analysis is disabled.")
        st.caption("Add LLM_API_KEY to .env when you obtain your key, then restart Streamlit.")
    st.divider()
    st.warning("For immediate danger, arrest/custody, police or court notices, deadlines, or high-stakes disputes, contact a qualified local advocate promptly.")

st.subheader("Search Indian legal sources")
search_query=st.text_input("Search Acts, provisions, constitutional articles or regulations", placeholder="e.g. Article 21, consumer refund, employment termination, BNS theft")
if st.button("Search database", disabled=not search_query.strip()):
    try:
        st.session_state["search_results"]=search_sources(search_query,DATABASE_PATH,8)
    except Exception as exc: st.error(f"Search failed: {exc}")
for item in st.session_state.get("search_results",[]):
    with st.expander(f"{item['title']} · {item.get('section') or 'Provision'} · {item['jurisdiction']}"):
        st.write(item["text"])
        st.caption(f"Type: {item['source_type']} · Status: {item['status'] or 'not supplied'} · Year: {item['year'] or 'not supplied'}")
        if item.get("source_publisher"): st.caption("Publisher: "+item["source_publisher"])
        if item.get("source_url"): st.markdown(f"[Open source document]({item['source_url']})")

st.divider()
st.subheader("Describe what happened")
st.write("Use your own words. Include dates, location, people involved, and documents/messages you have. The assistant will not assume your allegations are proven.")
story=st.text_area("Your situation",height=220,placeholder="Example: On 12 March, I paid... The other party then... I have bank transfer proof...")
c1,c2=st.columns(2)
with c1: location=st.text_input("State / city in India (important for jurisdiction)",placeholder="e.g. Guwahati, Assam")
with c2: language=st.selectbox("Response language",["English","Hindi","Assamese","Bengali","Tamil","Telugu","Marathi","Other (specify in story)"])
if st.button("Analyse my situation",type="primary",disabled=not story.strip()):
    triage=triage_text(story)
    try:
        with st.spinner("Searching the local legal database and preparing the analysis..."):
            result=analyze_problem(story,location,language) if LLM_API_KEY else analyze_without_llm(story,location)
        st.session_state["last_result"]=result
        out=Path("raw_outputs"); out.mkdir(exist_ok=True)
        name=datetime.now(timezone.utc).strftime("case_%Y%m%d_%H%M%S_utc.json")
        (out/name).write_text(json.dumps({"input":story,"state_city":location,"language":language,"result":result},ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception as exc: st.error(f"Analysis failed: {exc}")

result=st.session_state.get("last_result")
if result:
    triage=result.get("triage",{})
    st.subheader("Initial risk triage")
    st.write(f"**Urgency:** {triage.get('level','unknown').upper()} · **Lawyer recommended by first-pass rules:** {triage.get('lawyer_recommended','unknown')}")
    for reason in triage.get("reasons",[]): st.write("- "+reason)
    for step in triage.get("immediate_steps",[]): st.write("- "+step)
    if triage.get("emergency_guidance"): st.error(triage["emergency_guidance"])
    if result.get("notice"): st.info(result["notice"])
    if result.get("intake"):
        intake=result["intake"]
        st.subheader("Structured intake")
        st.write(intake.get("short_summary",""))
        st.write(f"**Category:** {intake.get('category','unclear')} · **Jurisdiction:** {intake.get('jurisdiction','to confirm')}")
        for key,label in [("facts","Facts stated"),("timeline","Timeline"),("evidence_mentioned","Evidence mentioned"),("missing_information","Information still needed"),("disputed_or_unverified_points","Disputed / unverified points")]:
            if intake.get(key):
                st.markdown(f"**{label}**")
                for v in intake[key]: st.write("- "+v)
        for key,label in [("plain_language_assessment","Plain-language assessment"),("possible_options","Possible options"),("practical_next_steps","Practical next steps"),("questions_to_clarify","Questions to clarify"),("lawyer_recommendation","Lawyer recommendation"),("source_notes","Sources and verification")]:
            if result.get(key):
                st.subheader(label)
                st.write(result[key])
        if result.get("draft"):
            st.subheader("Draft — advocate review required")
            st.text_area("Factual draft",result["draft"],height=180)
    if result.get("retrieved_sources"):
        st.subheader("Retrieved legal sources")
        for i,src in enumerate(result["retrieved_sources"],1):
            with st.expander(f"{i}. {src['title']} · {src.get('section') or 'Provision'} · {src['jurisdiction']}"):
                st.write(src["text"])
                st.caption(f"{src['source_type']} · status: {src['status'] or 'not supplied'} · year: {src['year'] or 'not supplied'}")
                if src.get("source_url"): st.markdown(f"[Open source]({src['source_url']})")
    st.caption(result.get("database_note","This is general legal information, not legal advice. Verify current law and consult an advocate before consequential action."))
    st.download_button("Download raw analysis JSON",json.dumps(result,ensure_ascii=False,indent=2),file_name="nyayamitra_analysis.json",mime="application/json")
