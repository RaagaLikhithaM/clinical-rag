"""
frontend/app.py

Streamlit chat interface for the Clinical Protocol RAG system.

The layout has two columns. The left column handles PDF upload and
ingestion. The right column is the chat window where the user asks
questions and sees cited answers.

All API calls go to the FastAPI server running on localhost:8000.
We follow the DermETAS pattern of keeping all pipeline logic out of
the frontend — the UI only calls the API and displays results.
"""

import requests
import streamlit as st

API_BASE = "http://localhost:8000"


# ══ Page config ════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Clinical Protocol Assistant",
    page_icon="🏥",
    layout="wide",
)

st.title("Clinical Protocol Assistant")
st.caption(
    "Upload clinical guidelines and ask evidence-based questions. "
    "All answers are grounded in the uploaded documents."
)


# ══ Session state ══════════════════════════════════════════════════════════════

# We store the chat history in session state so it persists across
# Streamlit reruns. Each message is a dict with role and content keys.
if "messages" not in st.session_state:
    st.session_state.messages = []

if "ingested_files" not in st.session_state:
    st.session_state.ingested_files = []


# ══ Layout ═════════════════════════════════════════════════════════════════════

left_col, right_col = st.columns([1, 2])


# ══ Left column: file upload ═══════════════════════════════════════════════════

with left_col:
    st.subheader("Knowledge Base")
    st.write(
        "Upload PDF clinical guidelines. The system will extract and "
        "index them so you can ask questions against their content."
    )

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if st.button("Ingest Documents") and uploaded_files:
        with st.spinner("Extracting and indexing documents..."):
            files_payload = [
                ("files", (f.name, f.getvalue(), "application/pdf"))
                for f in uploaded_files
            ]
            try:
                response = requests.post(
                    f"{API_BASE}/ingest", files=files_payload, timeout=120
                )
                response.raise_for_status()
                results = response.json()

                for result in results:
                    if result["status"] == "success":
                        st.success(
                            f"{result['source']} — "
                            f"{result['pages']} pages, "
                            f"{result['chunks']} chunks indexed"
                        )
                        if result["source"] not in st.session_state.ingested_files:
                            st.session_state.ingested_files.append(
                                result["source"]
                            )
                    elif result["status"] == "already_ingested":
                        st.info(f"{result['source']} was already indexed.")
                    else:
                        st.warning(f"{result['source']} — no text extracted.")

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot reach the API server. "
                    "Run: uvicorn server.main:app --reload"
                )
            except Exception as e:
                st.error(f"Ingestion failed: {e}")

    if st.session_state.ingested_files:
        st.markdown("**Indexed documents**")
        for fname in st.session_state.ingested_files:
            st.write(f"- {fname}")


# ══ Right column: chat ═════════════════════════════════════════════════════════

with right_col:
    st.subheader("Ask a Clinical Question")

    # Display existing chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.write(f"- {source}")
            if message.get("top_score"):
                st.caption(
                    f"Retrieval confidence: {message['top_score']:.0%}"
                )

    # Chat input
    user_input = st.chat_input(
        "Ask a question about the uploaded clinical guidelines..."
    )

    if user_input:
        # Show the user message immediately
        st.session_state.messages.append({
            "role":    "user",
            "content": user_input,
        })
        with st.chat_message("user"):
            st.markdown(user_input)

        # Call the query endpoint
        with st.chat_message("assistant"):
            with st.spinner("Searching guidelines..."):
                try:
                    response = requests.post(
                        f"{API_BASE}/query",
                        json={"question": user_input},
                        timeout=60,
                    )
                    response.raise_for_status()
                    data = response.json()

                    st.markdown(data["answer"])

                    if data.get("sources"):
                        with st.expander("Sources"):
                            for source in data["sources"]:
                                st.write(f"- {source}")

                    if data.get("top_score"):
                        st.caption(
                            f"Retrieval confidence: "
                            f"{data['top_score']:.0%}"
                        )

                    st.session_state.messages.append({
                        "role":      "assistant",
                        "content":   data["answer"],
                        "sources":   data.get("sources", []),
                        "top_score": data.get("top_score", 0.0),
                    })

                except requests.exceptions.ConnectionError:
                    st.error(
                        "Cannot reach the API server. "
                        "Run: uvicorn server.main:app --reload"
                    )
                except Exception as e:
                    st.error(f"Query failed: {e}")