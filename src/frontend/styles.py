from __future__ import annotations

import streamlit as st


def inject_theme(dark: bool = False) -> None:
    if dark:
        background = "#111827"
        surface = "#1f2937"
        text = "#f3f4f6"
        muted = "#9ca3af"
        border = "#374151"
    else:
        background = "#f7f9fc"
        surface = "#ffffff"
        text = "#111827"
        muted = "#64748b"
        border = "#e5eaf2"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        :root {{
            color-scheme: {"dark" if dark else "light"};
            --background-color: {background};
            --secondary-background-color: {surface};
            --text-color: {text};
            --app-bg: {background};
            --surface: {surface};
            --text: {text};
            --muted: {muted};
            --border: {border};
            --blue: #2563eb;
            --blue-soft: #eff6ff;
            --primary-color: #2563eb;
        }}
        html, body, [class*="css"], [data-testid="stAppViewContainer"] {{
            font-family: 'DM Sans', sans-serif;
            background: var(--app-bg);
            color: var(--text);
        }}
        .stApp, [data-testid="stMain"] {{
            background: var(--app-bg);
            color: var(--text);
        }}
        header[data-testid="stHeader"] {{
            height: 0;
            background: transparent;
        }}
        [data-testid="stToolbar"] {{ display: none; }}
        [data-testid="stAppViewBlockContainer"] {{
            padding: 1.15rem 1.35rem 2rem;
            max-width: 100%;
        }}
        [data-testid="stSidebar"] {{
            background: var(--surface);
            border-right: 1px solid var(--border);
            min-width: 245px;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            padding: 1.1rem .85rem;
        }}
        h1, h2, h3, h4, p, label, [data-testid="stMarkdownContainer"] {{
            color: var(--text);
        }}
        [data-testid="stCaptionContainer"], .stCaption {{
            color: var(--muted);
        }}
        .brand-mark {{
            width: 42px; height: 42px; border-radius: 14px;
            display: inline-flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, #2563eb, #818cf8);
            color: white; font-weight: 700; font-size: 25px;
            box-shadow: 0 8px 18px rgba(37, 99, 235, .2);
        }}
        .brand-title {{ font-size: 1.22rem; font-weight: 700; margin: 0; }}
        .brand-tagline {{ color: var(--muted); font-size: .78rem; margin-top: 2px; }}
        .top-brand {{
            font-size: 1rem; font-weight: 700; margin: 0;
            color: var(--text);
        }}
        .page-heading {{ font-size: 1.45rem; font-weight: 700; margin: 0; }}
        .page-subtitle {{ color: var(--muted); margin: .25rem 0 1rem; }}
        .surface-card {{
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 16px; padding: 16px;
            box-shadow: 0 6px 20px rgba(15, 23, 42, .035);
        }}
        .welcome-card {{
            position: relative; overflow: hidden;
            background: linear-gradient(112deg, #eaf2ff 0%, #f2f4ff 58%, #e8f0ff 100%);
            border: 1px solid #dbeafe; border-radius: 17px;
            padding: 21px 24px; margin: 2px 0 14px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.8);
        }}
        .welcome-card h2 {{ color: #172554; margin: 0 0 8px; }}
        .welcome-card p {{ color: #475569; margin: 0; }}
        .welcome-sparkle {{
            position: absolute; right: 20px; top: 15px;
            color: #93c5fd; font-size: 2rem;
        }}
        .welcome-robot {{
            display: inline-flex; align-items: center; justify-content: center;
            float: left; width: 74px; height: 74px; margin-right: 18px;
            border-radius: 22px; background: rgba(255,255,255,.64);
            color: #2563eb; font-size: 2.8rem;
        }}
        .welcome-actions {{ display:flex; flex-wrap:wrap; gap:7px; margin-top:14px; }}
        .workspace-header {{
            min-height: 48px; display:flex; align-items:center;
            border-bottom: 1px solid var(--border);
            margin: -4px 0 10px; padding: 0 0 8px;
        }}
        .version-pill {{
            border: 1px solid #dbeafe;
            border-radius: 999px;
            padding: .38rem .55rem;
            background: var(--surface);
            color: #334155;
            text-align: center;
            white-space: nowrap;
            font-size: .73rem;
        }}
        .metric-card {{
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 15px; padding: 16px; min-height: 92px;
        }}
        .metric-label {{ color: var(--muted); font-size: .82rem; }}
        .metric-value {{ color: var(--text); font-size: 1.65rem; font-weight: 700; }}
        .stButton > button {{
            border-radius: 10px; transition: all .16s ease;
            border-color: var(--border);
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] > button {{
            min-height: 2.1rem;
            text-align: left;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {{
            text-align: center;
        }}
        .stButton > button:hover {{
            border-color: #93c5fd; color: var(--blue);
            box-shadow: 0 5px 14px rgba(37, 99, 235, .09);
        }}
        [data-testid="stRadio"] div[role="radiogroup"] {{
            gap: .3rem;
        }}
        [data-testid="stRadio"] div[role="radiogroup"] label {{
            border: 1px solid var(--border);
            background: var(--surface);
            border-radius: 11px;
            padding: .3rem .72rem;
            margin: 0;
            transition: all .15s ease;
        }}
        [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
            background: var(--blue-soft);
            border-color: #bfdbfe;
            color: #1d4ed8;
        }}
        [data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {{
            display: none;
        }}
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
            border-radius: 10px;
            background: var(--surface);
        }}
        [data-testid="stSidebar"] [data-testid="stExpander"] details summary {{
            font-weight: 650;
        }}
        [data-testid="stSidebar"] [data-testid="stExpander"] {{
            margin: .2rem 0;
        }}
        [data-testid="stChatMessage"] {{
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 15px; padding: 12px 14px;
            margin-bottom: 12px;
        }}
        [data-testid="stChatInput"] {{
            border-color: #bfdbfe; border-radius: 14px;
        }}
        .muted-caption {{ color: var(--muted); font-size: .83rem; }}
        [data-testid="stExpander"] {{
            border: 1px solid var(--border); border-radius: 12px;
            background: var(--surface);
        }}
        [data-testid="stFileUploader"] {{
            background: var(--surface);
            border-radius: 13px;
        }}
        [data-testid="stChatInput"] textarea {{
            background: var(--surface);
            color: var(--text);
        }}
        .context-title {{
            font-size: .98rem; font-weight: 700;
            padding-bottom: .45rem; border-bottom: 1px solid var(--border);
        }}
        .context-card {{
            border: 1px solid var(--border); border-radius: 14px;
            background: var(--surface); padding: 12px; margin: 0 0 9px;
        }}
        @media (max-width: 1050px) {{
            [data-testid="stAppViewBlockContainer"] {{ padding: .75rem; }}
            [data-testid="stSidebar"] {{ min-width: 220px; }}
            .version-pill {{ white-space: normal; }}
        }}
        @media (max-width: 750px) {{
            .welcome-card {{ padding: 16px; }}
            .welcome-robot {{ display:none; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
