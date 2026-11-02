"""Static CSS for a calm procurement workspace."""

from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    """Apply static visual rules without interpolating untrusted content."""
    st.markdown(
        """
<style>
:root { --ink:#17343b; --muted:#62767a; --line:#dce5e2; --teal:#087f75; }
.stApp, [data-testid="stSidebar"] { font-family:"Segoe UI",Arial,sans-serif;
  font-size:1rem; line-height:1.55; }
.stApp p, .stApp label { letter-spacing:.005em; }
[data-testid="stCaptionContainer"] p { color:#455f65; font-size:.96rem;
  line-height:1.55; font-weight:400; }
[data-testid="stMetricLabel"] p { color:#50676d; font-size:.9rem; font-weight:600; }
[data-testid="stExpander"] [data-testid="stCaptionContainer"] p,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] p {
  color:#344d53; }
.stApp { background:radial-gradient(ellipse at 90% 0%,#e1eeea 0%,transparent 45%),
  #f5f7f8; color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1280px; padding-top:2rem; padding-bottom:4rem; }
h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
h1 { font-weight:700; } h2,h3 { font-weight:650; }
[data-testid="stSidebar"] { background:#edf3f2; border-right:1px solid var(--line); }
[data-testid="stSidebar"] h1 { font-size:1.25rem; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:1.1rem; }
.workspace-hero { background:linear-gradient(115deg,#153d43,#1e5e5c); color:#fff;
  padding:2rem 2.25rem; border-radius:22px; margin:0 0 .8rem;
  box-shadow:0 14px 38px #153d4317; position:relative; overflow:hidden; }
.workspace-hero::after { content:""; position:absolute; right:-65px; top:-120px;
  width:360px; height:360px; border:1px solid #ffffff20; border-radius:50%;
  box-shadow:0 0 0 48px #ffffff06,0 0 0 96px #ffffff04; pointer-events:none; }
.workspace-hero h1 { color:#fff; font-size:2.25rem; margin:.25rem 0; padding:0; }
.workspace-hero p { color:#d3e5e3; margin:.65rem 0 0; max-width:650px; }
.eyebrow { font-size:.7rem; font-weight:700; letter-spacing:.18em; color:#9ed9ca; }
.st-key-screen [role="radiogroup"] { background:#fff; border:1px solid var(--line);
  padding:.45rem; border-radius:14px; gap:.3rem; box-shadow:0 4px 16px #17343b05; }
.st-key-screen [role="radiogroup"] > label { flex:1; padding:.65rem .7rem;
  border-radius:10px; margin:0; transition:background .18s,box-shadow .18s; }
.st-key-screen [role="radiogroup"] > label:has(input:checked) {
  background:#e3f2ed; box-shadow:inset 0 0 0 1px #b9dcd2; }
.st-key-screen [role="radiogroup"] > label:hover { background:#f0f6f3; }
.st-key-screen [role="radiogroup"] p { font-size:.82rem; font-weight:600; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border-radius:14px; overflow:hidden; box-shadow:0 4px 20px #17343b06; }
[data-testid="stFileUploaderDropzone"] { background:#fff; border:1px dashed #a3c8bf;
  border-radius:16px; padding:1.6rem; }
[data-testid="stAlert"] { border-radius:12px; border:1px solid #17343b0a; }
[data-testid="stExpander"] { background:#ffffffb8; }
button:focus-visible, input:focus-visible { outline:3px solid #359c8c!important;
  outline-offset:3px; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line);
  border-radius:14px; padding:1rem 1.15rem; box-shadow:0 4px 20px #17343b05; }
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { font-size:1.65rem; font-weight:650; }
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {
  border-color:var(--line); border-radius:14px; background:#ffffffd9;
  box-shadow:0 4px 18px #17343b06; }
div.stButton > button[kind="primary"] { background:var(--teal); border-color:var(--teal);
  border-radius:10px; font-weight:650; }
div.stButton > button, div.stDownloadButton > button { border-radius:10px;
  transition:transform .16s,box-shadow .16s; }
div.stButton > button:not(:disabled):hover,
div.stDownloadButton > button:not(:disabled):hover {
  transform:translateY(-1px); box-shadow:0 5px 14px #17343b15; }
.st-key-cancel_run button { background:#fff1f0; border-color:#e5aaa5; color:#a52727; }
.st-key-cancel_run button:hover { background:#ffe3e0; color:#8b1c1c; }
@keyframes fadeInSlide { from { opacity:0; transform:translateY(8px); }
  to { opacity:1; transform:translateY(0); } }
@keyframes softPulse { 50% { box-shadow:0 0 0 5px rgba(8,127,117,.10); } }
.animated-card { animation:fadeInSlide .3s ease-out both; }
.winner-banner { background:#e8f5f0; border:1px solid #b9ded1; border-radius:16px;
  padding:1.1rem 1.25rem; animation:fadeInSlide .3s ease-out both; }
.pipeline-active { animation:softPulse 1.6s ease-in-out infinite; }
@media (max-width:760px) { .workspace-hero { padding:1.4rem; }
  .workspace-hero h1 { font-size:1.8rem; }
  .st-key-screen [role="radiogroup"] > label { flex:1 1 40%; }
  .block-container { padding-left:1rem; padding-right:1rem; } }
@media (prefers-reduced-motion:reduce) { *,*::before,*::after {
  animation:none!important; transition:none!important; transform:none!important; } }
</style>
""",
        unsafe_allow_html=True,
    )
