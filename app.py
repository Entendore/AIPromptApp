import sys, os, json, re, math
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QSplitter, QTextEdit, QLabel,
    QPushButton, QToolButton, QComboBox, QFrame, QDialog,
    QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QAbstractItemView, QButtonGroup,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QMimeData
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QTextCursor, QTextCharFormat,
    QKeySequence, QShortcut, QPainterPath, QAction
)

# ═══════════════════════ DATA ═══════════════════════

SECS = [
    {"id":"role","t":"Role & Identity","ic":"\uf507","ibg":"rgba(212,168,67,.12)","ic2":"#d4a843",
     "ph":"e.g., You are a senior data scientist with 10 years of experience in ML, specializing in NLP...","tip":"Primes the model's expertise.","def":True},
    {"id":"context","t":"Context & Background","ic":"\uf5fd","ibg":"rgba(92,184,122,.12)","ic2":"#5cb87a",
     "ph":"e.g., We're building a chatbot for customer support. 5000 tickets/day. Satisfaction 3.2/5...","tip":"Less guessing, better output.","def":True},
    {"id":"task","t":"Task & Objective","ic":"\uf140","ibg":"rgba(224,145,69,.12)","ic2":"#e09145",
     "ph":"e.g., Analyze the top 100 support tickets, categorize into 5-8 groups, propose a decision tree...","tip":"Use action verbs. Define 'done'.","def":True},
    {"id":"format","t":"Output Format","ic":"\uf00a","ibg":"rgba(95,168,212,.12)","ic2":"#5fa8d4",
     "ph":"e.g., Return JSON:\n{ \"categories\": [{ \"name\": string, \"count\": number }],\n  \"tree\": { ... } }","tip":"Eliminates format failures.","def":False},
    {"id":"constraints","t":"Constraints & Rules","ic":"\uf3ed","ibg":"rgba(212,95,95,.12)","ic2":"#d45f5f",
     "ph":"e.g.,\n- No jargon for non-technical readers\n- Each category needs 3+ examples\n- Max 800 words","tip":"Focus and prevent failures.","def":False},
    {"id":"negative","t":"Negative Prompt","ic":"\uf05e","ibg":"rgba(255,100,100,.1)","ic2":"#ff6b6b",
     "ph":"e.g.,\n- Do NOT start with \"Sure!\" or \"Here is...\"\n- Never assume prior knowledge\n- No bullet points","tip":"What NOT to do.","def":False},
    {"id":"examples","t":"Examples (Few-Shot)","ic":"\uf0eb","ibg":"rgba(180,140,220,.12)","ic2":"#b48cdc",
     "ph":"e.g.,\nInput: \"Internet drops every 30 min\"\nCategory: \"Connectivity\"\nReasoning: Repetitive, time-patterned","tip":"1-2 examples boost consistency.","def":False},
    {"id":"tone","t":"Tone & Style","ic":"\uf53f","ibg":"rgba(212,168,67,.12)","ic2":"#d4a843",
     "ph":"e.g., Clear, professional tone as if presenting to a VP. Short paragraphs. Concrete data over vague statements.","tip":"'Like a NYT tech columnist.'","def":False},
]

MODELS = [
    {"name":"GPT-4.1","cpT":3.2,"inC":2.0,"outC":8.0,"ctx":1048576,"color":"#10a37f"},
    {"name":"GPT-4o","cpT":3.5,"inC":2.5,"outC":10.0,"ctx":128000,"color":"#10a37f"},
    {"name":"Claude 4 Sonnet","cpT":3.8,"inC":3.0,"outC":15.0,"ctx":200000,"color":"#cc785c"},
    {"name":"Claude 4 Opus","cpT":3.5,"inC":15.0,"outC":75.0,"ctx":200000,"color":"#cc785c"},
    {"name":"Gemini 2.5 Pro","cpT":3.6,"inC":1.25,"outC":10.0,"ctx":1048576,"color":"#4285f4"},
    {"name":"Gemini 2.5 Flash","cpT":3.8,"inC":0.15,"outC":0.6,"ctx":1048576,"color":"#34a853"},
    {"name":"DeepSeek V3","cpT":3.2,"inC":0.27,"outC":1.1,"ctx":131072,"color":"#5b6ef7"},
    {"name":"Llama 4 Maverick","cpT":3.5,"inC":0.20,"outC":0.8,"ctx":1048576,"color":"#0668e1"},
]

FILLER = [
    (re.compile(r"in today'?s fast[- ]paced world",re.I),""),
    (re.compile(r"in today'?s world",re.I),""),
    (re.compile(r"it goes without saying",re.I),""),
    (re.compile(r"it is important to note",re.I),""),
    (re.compile(r"it should be noted",re.I),""),
    (re.compile(r"needless to say",re.I),""),
    (re.compile(r"at the end of the day",re.I),""),
    (re.compile(r"in this day and age",re.I),""),
    (re.compile(r"for all intents and purposes",re.I),""),
    (re.compile(r"in order to ",re.I),"to "),
    (re.compile(r"due to the fact that",re.I),"because"),
    (re.compile(r"for the purpose of ",re.I),"to "),
    (re.compile(r"in the event that ",re.I),"if "),
    (re.compile(r"a large number of ",re.I),"many "),
    (re.compile(r"a significant amount of ",re.I),""),
    (re.compile(r"the fact that ",re.I),""),
]

COMPRESS_RULES = [
    (re.compile(r"\bplease\b",re.I),""),
    (re.compile(r"\bkindly\b",re.I),""),
    (re.compile(r"\bcertainly\b",re.I),""),
    (re.compile(r"\bin order to ",re.I),"to "),
    (re.compile(r"\bdue to the fact that ",re.I),"because "),
    (re.compile(r"\bat the present time ",re.I),"now "),
    (re.compile(r"\bin the event that ",re.I),"if "),
    (re.compile(r"\ba large number of ",re.I),"many "),
    (re.compile(r"\ba significant amount of ",re.I),""),
    (re.compile(r"\bfor the purpose of ",re.I),"to "),
    (re.compile(r"\bit is important to ",re.I),""),
    (re.compile(r"\bneedless to say[,.]?\s*",re.I),""),
    (re.compile(r"\bin this day and age ",re.I),""),
    (re.compile(r"\bat the end of the day[,.]?\s*",re.I),""),
    (re.compile(r"\bvery ",re.I),""),
    (re.compile(r"\breally ",re.I),""),
    (re.compile(r"\bjust ",re.I),""),
    (re.compile(r"\bactually ",re.I),""),
    (re.compile(r"\bbasically ",re.I),""),
    (re.compile(r"\bliterally ",re.I),""),
    (re.compile(r"\bin terms of ",re.I),"for "),
    (re.compile(r"\bwith regard to ",re.I),"for "),
    (re.compile(r"\bin addition to ",re.I),"plus "),
    (re.compile(r"\ba lot of ",re.I),"many "),
    (re.compile(r"\beach and every ",re.I),"every "),
    (re.compile(r"\bfirst and foremost ",re.I),"first "),
]

VAGUE = [
    (re.compile(r"\b(make it|do it|fix it|help me with it)\b",re.I),"Specify exactly what"),
    (re.compile(r"\bgood\b",re.I),"Replace with criteria"),
    (re.compile(r"\bbetter\b",re.I),"Define with metrics"),
    (re.compile(r"\bsome\b",re.I),"Use a number"),
    (re.compile(r"\bvarious\b",re.I),"List specifics"),
    (re.compile(r"\betc\.?\b",re.I),"Complete the list"),
    (re.compile(r"\bstuff\b",re.I),"Be specific"),
    (re.compile(r"\bnice\b",re.I),"Describe precisely"),
    (re.compile(r"\bproperly\b",re.I),'Define "properly"'),
    (re.compile(r"\bappropriate\b",re.I),"Specify what"),
    (re.compile(r"\brelevant\b",re.I),"List what's relevant"),
]

ACTION_VERBS = ["analyze","write","create","design","build","generate","extract","transform",
    "review","explain","summarize","compare","evaluate","list","identify","propose",
    "develop","implement","optimize","classify","refactor","debug","test","document",
    "research","outline","draft","refine","convert","translate"]

VAGUE_PHRASES = ["do something","do it","help me","make it good","make it better","fix it"]

TEMPLATES = [
    {"name":"Blog Post Writer","cat":"writing","d":"Long-form content with SEO",
     "data":{"role":"You are an experienced content strategist who has written for top-tier publications. You understand SEO, engagement, and narrative.",
     "context":"I need a blog post for our tech blog. Audience: engineering managers and senior devs. Position us as thought leaders.",
     "task":"Write a comprehensive blog post explaining a complex technical topic accessibly while maintaining depth. Include hook, subheadings, takeaways, CTA.",
     "format":"Markdown:\n- H1 (under 60 chars, keyword)\n- Meta description (2-3 sentences)\n- Hook intro\n- 4-6 H2 sections\n- Code example per section\n- Key Takeaways bullets\n- CTA",
     "constraints":"- 1500-2000 words\n- No filler phrases\n- All claims substantiated\n- Active voice\n- 3-5 internal links in [brackets]",
     "negative":"- Do NOT start with a question\n- No exclamations in headings\n- No generic image suggestions",
     "examples":"","tone":"Authoritative but approachable. Like a senior engineer at lunch."}},
    {"name":"Code Reviewer","cat":"coding","d":"Thorough review with fixes",
     "data":{"role":"You are a principal engineer with deep expertise in architecture, patterns, and clean code.",
     "context":"Production service, user-facing. Priority: reliability, readability, maintainability. SOLID principles.",
     "task":"Review for: bugs, edge cases, performance, security, organization, best practices, testability. Explain why + suggest fix.",
     "format":"## Critical\n- [Line X] Issue → Fix\n## Warnings\n## Suggestions\n## Positives\nScore (1-10) + summary",
     "constraints":"- Prioritize bugs over style\n- No over-engineering\n- Be concise\n- Reference line numbers",
     "negative":"- Do NOT rewrite everything\n- No passive voice","examples":"",
     "tone":"Direct, constructive. Like a respected senior colleague."}},
    {"name":"Data Analysis","cat":"analysis","d":"Data to actionable insights",
     "data":{"role":"Data analyst who finds actionable patterns and communicates to technical and business audiences.",
     "context":"Dataset summary provided. Goal: extract insights for business decisions.",
     "task":"Analyze systematically. Identify trends, outliers, correlations, anomalies. Executive report with recommendations.",
     "format":"## Executive Summary (3-5 bullets)\n## Overview (metrics table)\n## Findings\n## Anomalies\n## Recommendations\n## Methodology",
     "constraints":"- Quantify all claims\n- Correlation ≠ causation\n- Flag low-confidence\n- Max 1200 words",
     "negative":"- Do NOT claim causation without caveats\n- No pie charts","examples":"",
     "tone":"Objective, data-driven. Honest about uncertainty."}},
    {"name":"API Docs","cat":"coding","d":"Complete API reference",
     "data":{"role":"Technical writer specializing in developer docs.",
     "context":"New API endpoint for developer portal. Must be self-contained for integration without support.",
     "task":"Write complete API docs with everything needed for a successful first request.",
     "format":"## Endpoint\n**Method** `METHOD /path`\n**Auth**\n**Request** (headers, params, body, curl + JS)\n**Response** (schema + JSON, errors)\n**Gotchas**",
     "constraints":"- Correct examples\n- Realistic values\n- Rate limits\n- One common mistake",
     "negative":"- Do NOT use YOUR_API_KEY without calling it out\n- Never omit errors","examples":"",
     "tone":"Clean, precise. Like Stripe docs."}},
    {"name":"PRD Writer","cat":"analysis","d":"Ideas to actionable PRDs",
     "data":{"role":"Senior PM at startups and big tech. Thinks in user problems, metrics, trade-offs.",
     "context":"Product idea to PRD. Team: engineers, designers, PM. 2-week sprints.",
     "task":"Transform idea into structured PRD. Identify ambiguities, make assumptions.",
     "format":"## Overview\n## Problem\n## Goals & Metrics\n## User Stories (acceptance criteria)\n## Requirements: Must/Should/Nice\n## Out of Scope\n## Open Questions",
     "constraints":"- Specific metrics\n- Max 5 must-haves\n- Testable criteria\n- Flag dependencies",
     "negative":"- Do NOT put nice-to-haves in must\n- No vague criteria","examples":"",
     "tone":"Structured, decisive."}},
    {"name":"Story Opener","cat":"creative","d":"Immersive story openings",
     "data":{"role":"Literary fiction writer. Immersive prose, complex characters, hook openings.",
     "context":"Story opening: tone, character, intrigue. Literary fiction with speculative elements.",
     "task":"Write 500-800 words. Sensory detail, voice, emotional connection. End demanding continuation.",
     "format":"Prose only.","constraints":"- No info dumps\n- Show don't tell\n- 3+ sensory details\n- No cliché openings",
     "negative":"- No second person\n- Never start with weather","examples":"",
     "tone":"Lush, precise. Donna Tartt meets Ishiguro."}},
    {"name":"Meeting Notes","cat":"writing","d":"Decisions and actions",
     "data":{"role":"Executive assistant producing notes people actually read.",
     "context":"Raw notes/transcript. Cross-functional. Not everyone attended.",
     "task":"Structured summary: decisions, action items with owners/deadlines, open questions.",
     "format":"## Meeting: [Title]\nDate/Attendees/Duration\n## Decisions\n## Actions table\n## Discussion\n## Open Questions",
     "constraints":"- Don't attribute opinions unless stated\n- Every action needs owner + deadline\n- Under 500 words",
     "negative":"- No transcript\n- No own commentary","examples":"",
     "tone":"Neutral, efficient."}},
    {"name":"Architecture","cat":"coding","d":"Design and document systems",
     "data":{"role":"Staff architect at millions of req/day. Thinks in trade-offs.",
     "context":"System architecture. 5-8 engineers, 2-3 months.",
     "task":"Design addressing requirements. High-level, components, data flow, critical decisions with trade-offs.",
     "format":"## Requirements\n## Architecture (text diagram)\n## Components\n## Data Model\n## Critical Paths\n## Trade-offs\n## Risks",
     "constraints":"- Real technologies\n- Justify choices\n- Failure modes\n- Estimate team/timeline",
     "negative":"- No default microservices without justification\n- No single best without alternatives","examples":"",
     "tone":"Pragmatic, experienced."}},
]

QUICK_INSERTS = [
    ("Format",[
        ("JSON output","format","Return as valid JSON. No text before or after."),
        ("Markdown + headers","format","Markdown with H2/H3 headers. Table of contents at top."),
        ("Numbered list","format","Numbered list. Each item: one clear sentence."),
        ("Comparison table","format","Markdown table: Feature | Option A | Option B | Recommendation."),
        ("Code + comments","format","Code blocks with inline comments. Brief explanation after each block."),
    ]),
    ("Constraints",[
        ("No jargon","constraints","- Plain language for general audience\n- Define technical terms on first use"),
        ("Be concise","constraints","- As concise as possible\n- Short sentences\n- Cut sentences without new info"),
        ("Cite sources","constraints","- Cite sources for factual claims\n- [Source: X] notation"),
        ("Edge cases","constraints","- Address at least 3 edge cases\n- Explain expected behavior"),
    ]),
    ("Negative",[
        ("No preamble","negative","- Do NOT start with \"Sure!\", \"Here is...\", \"Certainly!\"\n- Start directly with content"),
        ("No apologies","negative","- Do NOT apologize, say \"as an AI\", or include disclaimers\n- No hedging with \"I think\""),
        ("No repetition","negative","- Do NOT repeat the prompt back\n- Do NOT summarize what was asked"),
        ("No filler","negative","- No \"in conclusion\", \"it's worth noting\"\n- No unnecessary transitions"),
    ]),
    ("Tone",[
        ("Academic","tone","Formal academic tone. Precise terminology. Evidence-backed. Objective."),
        ("Conversational","tone","Like explaining to a curious friend over coffee. Casual but not sloppy."),
        ("Executive","tone","For a busy executive. Bottom line first. Bullets. Every sentence earns its place."),
        ("Technical","tone","For senior engineers. Precise technical language. Show code, don't describe."),
    ]),
]

FF = "'Space Grotesk','Segoe UI','Helvetica Neue',sans-serif"
MF = "'Consolas','JetBrains Mono','Courier New',monospace"

STYLE = f"""
QMainWindow, QDialog {{ background-color: #0e0e0e; }}
QWidget {{ color: #e8e4dd; font-family: {FF}; font-size: 13px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: #0e0e0e; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #2e2e2e; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #5a5550; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QTextEdit {{ background-color: #0e0e0e; border: 1px solid #2e2e2e; border-radius: 6px;
    padding: 8px; color: #e8e4dd; font-family: {FF}; font-size: 13px; selection-background-color: rgba(212,168,67,.3); }}
QTextEdit:focus {{ border-color: #d4a843; }}
QLineEdit {{ background-color: #0e0e0e; border: 1px solid #2e2e2e; border-radius: 6px;
    padding: 6px 8px; color: #e8e4dd; font-family: {FF}; font-size: 13px; }}
QLineEdit:focus {{ border-color: #d4a843; }}
QPushButton {{ border: 1px solid #2e2e2e; border-radius: 6px; padding: 6px 12px;
    background: transparent; color: #7a756f; font-family: {FF}; font-size: 12px; }}
QPushButton:hover {{ color: #e8e4dd; border-color: #7a756f; background: #1f1f1f; }}
QPushButton:pressed {{ background: #262626; }}
QPushButton:disabled {{ color: #3a3a3a; border-color: #2e2e2e; }}
QToolButton {{ border: none; background: transparent; color: #7a756f; border-radius: 5px;
    padding: 4px; font-size: 11px; }}
QToolButton:hover {{ color: #e8e4dd; background: rgba(212,168,67,.1); }}
QToolButton:disabled {{ color: #3a3a3a; }}
QComboBox {{ background: #1f1f1f; border: 1px solid #2e2e2e; border-radius: 6px;
    padding: 5px 10px; color: #7a756f; font-size: 12px; min-width: 60px; }}
QComboBox:hover {{ color: #e8e4dd; border-color: #7a756f; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: #1f1f1f; border: 1px solid #2e2e2e;
    color: #e8e4dd; selection-background-color: rgba(212,168,67,.2); }}
QTableWidget {{ background: transparent; border: none; gridline-color: #2e2e2e; }}
QTableWidget::item {{ padding: 4px; }}
QHeaderView::section {{ background: transparent; color: #5a5550; font-size: 10px;
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px;
    padding: 6px 8px; border: none; border-bottom: 1px solid #2e2e2e; }}
QLabel {{ background: transparent; }}
"""

ACCENT = "#d4a843"
OK = "#5cb87a"
WARN = "#e09145"
ERR = "#d45f5f"
INFO = "#5fa8d4"
VAGUE_C = "#b48cdc"
MUTED = "#7a756f"
MUTED2 = "#5a5550"
BORDER = "#2e2e2e"
CARD = "#1f1f1f"
BG = "#0e0e0e"

# ═══════════════════════ UTILITIES ═══════════════════════

def det_vars(texts):
    m = " ".join(texts)
    return list(set(re.findall(r"\{\{(\w+)\}\}", m)))

def apply_vars(text, vals):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: vals.get(m.group(1), m.group(0)), text)

def calc_score(st, sec_ord):
    filled = [i for i in sec_ord if st.get(i,"").strip()]
    tf = len(filled)
    tt = st.get("task","")
    tw = tt.strip().split() if tt.strip() else []

    c_len = 100 if len(tw)>=15 else 75 if len(tw)>=10 else 40 if len(tw)>=5 else 15 if len(tw)>=2 else 0
    c_verb = 100 if any(v in tt.lower() for v in ACTION_VERBS) else 0
    c_vague = 20 if any(p in tt.lower() for p in VAGUE_PHRASES) else 100
    c_ctx = 100 if len(st.get("context","").strip())>50 else 60 if len(st.get("context","").strip())>20 else 25 if st.get("context","").strip() else 0
    clarity = round(c_len*.35+c_verb*.35+c_vague*.15+c_ctx*.15)

    s_fmt = 100 if st.get("format","").strip() else 0
    s_con = 100 if st.get("constraints","").strip() else 0
    s_ex = 100 if st.get("examples","").strip() else 0
    s_neg = 100 if st.get("negative","").strip() else 0
    nums = len(re.findall(r"\d+", " ".join(st.values())))
    s_num = 100 if nums>=5 else 70 if nums>=3 else 35 if nums>=1 else 0
    spec = round(s_fmt*.25+s_con*.25+s_ex*.2+s_neg*.15+s_num*.15)

    comp = round((tf/len(SECS))*100)

    sr = 100 if st.get("role","").strip() else 0
    st2 = 100 if st.get("task","").strip() else 0
    sf = 100 if st.get("format","").strip() else 0
    sb = 100 if st.get("constraints","").strip() and st.get("negative","").strip() else (50 if st.get("constraints","").strip() or st.get("negative","").strip() else 0)
    sc = 100 if st.get("task","").strip() and st.get("role","").strip() else (40 if st.get("task","").strip() or st.get("role","").strip() else 0)
    struc = round(sr*.15+st2*.3+sf*.2+sb*.15+sc*.2)

    overall = round(clarity*.3+spec*.25+comp*.2+struc*.25)
    return overall, clarity, spec, comp, struc

def assemble_prompt(st, sec_ord, pats, split="full", apply_v=True, var_vals=None):
    vv = var_vals or {}
    parts = []
    if pats.get("ss"): parts.append("**Instructions:** Break into clear, numbered steps. Execute each sequentially.")
    if pats.get("cot"): parts.append("**Important:** Think step by step. Show reasoning before the final answer.")
    if pats.get("se"): parts.append("**After completing:** Review output against all requirements. Revise if missing or incorrect.")
    sys_i, usr_i = ["role","context","tone"], ["task","format","constraints","negative","examples"]
    ids = sec_ord if split=="full" else [i for i in sec_ord if i in (sys_i if split=="system" else usr_i)]
    for i in ids:
        v = st.get(i,"").strip()
        if v:
            s = next((s for s in SECS if s["id"]==i), None)
            txt = apply_vars(v, vv) if apply_v else v
            if s: parts.append(f"## {s['t'].upper()}\n{txt}")
    return "\n\n".join(parts)

def enhance_text(st, sec_ord):
    removed = 0
    for i in sec_ord:
        t = st.get(i,"")
        if not t.strip(): continue
        for pat, rep in FILLER:
            matches = pat.findall(t)
            if matches: removed += len(matches)
            t = pat.sub(rep, t)
        t = re.sub(r"  +"," ",t)
        t = re.sub(r"\n{3,}","\n\n",t)
        t = re.sub(r"^ +| +$","",t,flags=re.M)
        t = re.sub(r"\. ([a-z])",lambda m:m.group(0).upper(),t)
        st[i] = t.strip()
    return removed

def compress_text(text):
    cc = 0
    for pat, rep in COMPRESS_RULES:
        m = pat.findall(text)
        if m: cc += len(m)
        text = pat.sub(rep, text)
    text = re.sub(r"  +"," ",text)
    text = re.sub(r"\n{3,}","\n\n",text)
    return text.strip(), cc

def tok_est(text, cpt): return math.ceil(len(text)/cpt) if text else 0

def readability(text):
    if not text.strip(): return {}
    sents = [s for s in re.split(r"[.!?]+",text) if len(s.strip())>2]
    words = text.split()
    asl = len(words)/len(sents) if sents else 0
    awl = sum(len(w) for w in words)/len(words) if words else 0
    cx = sum(1 for w in words if len(w)>6)
    cxp = round(cx/len(words)*100) if words else 0
    fk = (.39*(len(words)/len(sents)) if sents else 0)+(11.8*awl)-15.59
    return {"asl":asl,"awl":awl,"cxp":cxp,"fk":fk}

# ═══════════════════════ CUSTOM WIDGETS ═══════════════════════

class ScoreRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(96, 96)
        self._val = 0
        self._col = QColor(ERR)

    def set_score(self, v, c):
        self._val = v
        self._col = QColor(c)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(6,6,84,84)
        pen = QPen(QColor(BORDER), 5)
        p.setPen(pen)
        p.drawArc(r, 0, 360*16)
        pen = QPen(self._col, 5, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        span = -int(self._val/100*360*16) if self._val>0 else 0
        if span: p.drawArc(r, 90*16, span)
        p.setPen(QColor("#e8e4dd"))
        p.setFont(QFont(FF, 18, QFont.Bold))
        p.drawText(r, Qt.AlignCenter, str(self._val))
        p.end()

class SubMetricRow(QWidget):
    def __init__(self, label, val, color, indent=False, parent=None):
        super().__init__(parent)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(indent*14 if indent else 0, 1, 0, 1)
        lo.setSpacing(6)
        dot = QLabel("●")
        dot.setFixedSize(6,6)
        dot.setStyleSheet(f"color:{color};font-size:6px;")
        lo.addWidget(dot)
        lb = QLabel(label)
        lb.setStyleSheet(f"font-size:{10 if indent else 11}px;color:{MUTED};")
        lo.addWidget(lb, 1)
        bar_bg = QFrame()
        bar_bg.setFixedWidth(indent*36+14 if indent else 50)
        bar_bg.setFixedHeight(3)
        bar_bg.setStyleSheet(f"background:{BORDER};border-radius:2px;")
        bar_lo = QHBoxLayout(bar_bg)
        bar_lo.setContentsMargins(0,0,0,0)
        bar_lo.setSpacing(0)
        fill = QFrame()
        fill.setFixedHeight(3)
        fill.setStyleSheet(f"background:{color};border-radius:2px;opacity:{0.7 if indent else 1};")
        fill.setFixedWidth(max(0, int(bar_bg.width()*val/100)))
        bar_lo.addWidget(fill)
        bar_lo.addStretch()
        lo.addWidget(bar_bg)
        vl = QLabel(f"{val}%")
        vl.setFixedWidth(30)
        vl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        vl.setStyleSheet(f"font-family:{MF};font-size:{9 if indent else 10}px;color:{MUTED if indent else '#e8e4dd'};")
        lo.addWidget(vl)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        bar = self.findChild(QFrame)
        if bar:
            fill = bar.findChild(QFrame)
            if fill:
                w = bar.width()
                vl = self.findChild(QLabel, "val_label")

class CheckItem(QWidget):
    def __init__(self, label, checked, parent=None):
        super().__init__(parent)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0,1,0,1)
        lo.setSpacing(6)
        icon = QLabel("✓" if checked else "✗")
        icon.setFixedSize(14,14)
        icon.setAlignment(Qt.AlignCenter)
        bg = OK if checked else CARD
        fg = "#0e0e0e" if checked else MUTED2
        icon.setStyleSheet(f"background:{bg};color:{fg};border-radius:3px;font-size:8px;font-weight:bold;")
        lo.addWidget(icon)
        lb = QLabel(label)
        lb.setStyleSheet(f"font-size:11px;color:{'#e8e4dd' if checked else MUTED2};")
        lo.addWidget(lb)
        lo.addStretch()

class SectionCard(QFrame):
    textChanged = Signal(str, str)
    toggled = Signal(str, bool)

    def __init__(self, sec, parent=None):
        super().__init__(parent)
        self.sec = sec
        self._open = sec.get("def", False)
        self._drag_over = False
        self.setup()

    def setup(self):
        self.setObjectName("sectionCard")
        self.setStyleSheet(f"""
            #sectionCard {{ background:{CARD};border:1px solid {BORDER};border-radius:10px; }}
            #sectionCard:hover {{ border-color: rgba(212,168,67,.2); }}
            #sectionCard[active="true"] {{ border-color:{ACCENT}; }}
            #secBtn {{ background:transparent;border:none;cursor:pointer;padding:10px; }}
            #secIcon {{ background:{self.sec['ibg']};color:{self.sec['ic2']};border-radius:7px;
                width:28px;height:28px; }}
            #secTitle {{ font-size:13px;font-weight:600;color:#e8e4dd; }}
            #secSnippet {{ font-size:11px;color:{MUTED}; }}
            #secCount {{ font-family:{MF};font-size:10px;color:{MUTED}; }}
            #secChev {{ color:{MUTED};font-size:10px; }}
            #moveBtn {{ border:none;background:transparent;color:{MUTED};border-radius:4px;
                padding:2px;font-size:9px; }}
            #moveBtn:hover {{ background:{f"rgba(212,168,67,.1)"};color:{ACCENT}; }}
            #dropZone {{ border:2px dashed {BORDER};border-radius:6px;padding:8px;margin-top:6px; }}
            #dropZone[active="true"] {{ border-color:{ACCENT};background:{f"rgba(212,168,67,.08)"}; }}
        """)
        mlo = QVBoxLayout(self)
        mlo.setContentsMargins(0,0,0,0)
        mlo.setSpacing(0)

        btn = QPushButton()
        btn.setObjectName("secBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setDefault(False)
        btn.setAutoDefault(False)
        blo = QHBoxLayout(btn)
        blo.setContentsMargins(10,8,8,8)
        blo.setSpacing(8)

        icon = QLabel()
        icon.setObjectName("secIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setText(self.sec["ic"])
        icon.setStyleSheet(f"font-family:'Font Awesome 6 Free';font-weight:900;background:{self.sec['ibg']};color:{self.sec['ic2']};border-radius:7px;width:28px;height:28px;")
        blo.addWidget(icon)

        right = QVBoxLayout()
        right.setSpacing(1)
        title = QLabel(self.sec["t"])
        title.setObjectName("secTitle")
        right.addWidget(title)
        snippet = QLabel(self.sec["tip"])
        snippet.setObjectName("secSnippet")
        right.addWidget(snippet)
        blo.addLayout(right, 1)

        move_up = QToolButton()
        move_up.setObjectName("moveBtn")
        move_up.setText("▲")
        move_up.setFixedSize(18,18)
        move_up.setToolTip("Move up")
        blo.addWidget(move_up)

        move_dn = QToolButton()
        move_dn.setObjectName("moveBtn")
        move_dn.setText("▼")
        move_dn.setFixedSize(18,18)
        move_dn.setToolTip("Move down")
        blo.addWidget(move_dn)

        copy_btn = QToolButton()
        copy_btn.setObjectName("moveBtn")
        copy_btn.setText("⧉")
        copy_btn.setFixedSize(18,18)
        copy_btn.setToolTip("Copy section")
        blo.addWidget(copy_btn)

        clear_btn = QToolButton()
        clear_btn.setObjectName("moveBtn")
        clear_btn.setText("✕")
        clear_btn.setFixedSize(18,18)
        clear_btn.setToolTip("Clear section")
        blo.addWidget(clear_btn)

        self.count_lbl = QLabel("0")
        self.count_lbl.setObjectName("secCount")
        blo.addWidget(self.count_lbl)

        chev = QLabel("▼")
        chev.setObjectName("secChev")
        blo.addWidget(chev)
        self.chev = chev

        mlo.addWidget(btn)

        self.content = QWidget()
        clo = QVBoxLayout(self.content)
        clo.setContentsMargins(10,0,10,10)
        clo.setSpacing(0)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText(self.sec["ph"])
        self.editor.setAcceptRichText(False)
        rows = 4 if self.sec["id"] in ("format","constraints","negative","examples") else 3
        self.editor.setFixedHeight(rows * 24 + 20)
        self.editor.setAcceptDrops(True)
        clo.addWidget(self.editor)

        self.drop_zone = QLabel("  Drop a .txt or .md file here  ")
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setAlignment(Qt.AlignCenter)
        self.drop_zone.setStyleSheet(f"""
            #dropZone {{ border:2px dashed {BORDER};border-radius:6px;padding:8px;
            font-size:11px;color:{MUTED2};margin-top:6px; }}
        """)
        clo.addWidget(self.drop_zone)

        self.content.setVisible(self._open)
        mlo.addWidget(self.content)

        btn.clicked.connect(self.toggle)
        move_up.clicked.connect(lambda: self.moveRequested.emit(-1))
        move_dn.clicked.connect(lambda: self.moveRequested.emit(1))
        copy_btn.clicked.connect(self.copy_section)
        clear_btn.clicked.connect(self.clear_section)
        self.editor.textChanged.connect(self._on_text_changed)

        self.moveRequested = Signal(int)
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._emit_changed)

    def toggle(self):
        self._open = not self._open
        self.content.setVisible(self._open)
        self.chev.setText("▲" if self._open else "▼")
        self.setProperty("active", self._open)
        self.style().unpolish(self)
        self.style().polish(self)
        self.toggled.emit(self.sec["id"], self._open)
        if self._open:
            self.editor.setFocus()

    def set_open(self, o):
        if self._open != o:
            self._open = o
            self.content.setVisible(o)
            self.chev.setText("▲" if o else "▼")
            self.setProperty("active", o)
            self.style().unpolish(self)
            self.style().polish(self)

    def _on_text_changed(self):
        txt = self.editor.toPlainText()
        self.count_lbl.setText(str(len(txt)))
        if txt.strip():
            self.snippet.setText(txt[:70]+("..." if len(txt)>70 else ""))
            self.setStyleSheet(self.styleSheet().replace(f"border:1px solid {BORDER}", f"border-left:3px solid {ACCENT};border-top:1px solid {BORDER};border-right:1px solid {BORDER};border-bottom:1px solid {BORDER}"))
        else:
            self.snippet.setText(self.sec["tip"])
            self.setStyleSheet(f"""
                #sectionCard {{ background:{CARD};border:1px solid {BORDER};border-radius:10px; }}
                #sectionCard:hover {{ border-color: rgba(212,168,67,.2); }}
                #sectionCard[active="true"] {{ border-color:{ACCENT}; }}
                #secBtn {{ background:transparent;border:none;cursor:pointer;padding:10px; }}
                #secIcon {{ background:{self.sec['ibg']};color:{self.sec['ic2']};border-radius:7px;
                    width:28px;height:28px; }}
                #secTitle {{ font-size:13px;font-weight:600;color:#e8e4dd; }}
                #secSnippet {{ font-size:11px;color:{MUTED}; }}
                #secCount {{ font-family:{MF};font-size:10px;color:{MUTED}; }}
                #secChev {{ color:{MUTED};font-size:10px; }}
                #moveBtn {{ border:none;background:transparent;color:{MUTED};border-radius:4px;
                    padding:2px;font-size:9px; }}
                #moveBtn:hover {{ background:{f"rgba(212,168,67,.1)"};color:{ACCENT}; }}
                #dropZone {{ border:2px dashed {BORDER};border-radius:6px;padding:8px;margin-top:6px; }}
                #dropZone[active="true"] {{ border-color:{ACCENT};background:{f"rgba(212,168,67,.08)"}; }}
            """)
        self._debounce.start()

    def _emit_changed(self):
        self.textChanged.emit(self.sec["id"], self.editor.toPlainText())

    def copy_section(self):
        txt = self.editor.toPlainText()
        if txt.strip():
            QApplication.clipboard().setText(txt)
            self._toast("Section copied")

    def clear_section(self):
        if self.editor.toPlainText().strip():
            self.editor.clear()

    def _toast(self, msg):
        w = self.window()
        if hasattr(w, "show_toast"): w.show_toast(msg)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.drop_zone.setProperty("active", True)
            self.drop_zone.style().unpolish(self.drop_zone)
            self.drop_zone.style().polish(self.drop_zone)

    def dragLeaveEvent(self, e):
        self.drop_zone.setProperty("active", False)
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

    def dropEvent(self, e):
        self.drop_zone.setProperty("active", False)
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path and re.match(r".*\.(txt|md|json|csv)$", path, re.I):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.editor.setPlainText(f.read())
                    self._toast(f"Imported {os.path.basename(path)}")
                except: pass
            break

# ═══════════════════════ DIALOGS ═══════════════════════

class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Engineering Guide")
        self.setFixedSize(560, 580)
        self.setStyleSheet(f"QDialog{{background:{BG};}} QLabel{{background:transparent;}} QPushButton{{min-width:80px;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(24,20,24,20)

        hdr = QHBoxLayout()
        t = QLabel("Prompt Engineering Guide")
        t.setStyleSheet(f"font-size:18px;font-weight:700;")
        hdr.addWidget(t)
        close = QPushButton("✕")
        close.setFixedSize(28,28)
        close.clicked.connect(self.close)
        hdr.addWidget(close)
        lo.addLayout(hdr)

        tips = [
            ("1. Be Specific","Instead of \"write about AI,\" say \"write a 500-word blog post explaining transformers for devs with 3+ years experience.\""),
            ("2. Provide Context","Who is the audience? What problem are you solving? What has been tried?"),
            ("3. Define Format","Markdown, JSON, table — specify exactly how you want the response."),
            ("4. Set Constraints","Word limits, forbidden phrases, required inclusions."),
            ("5. Use Examples","1-3 few-shot examples dramatically improve consistency."),
            ("6. Negative Prompts","\"Do NOT start with 'Sure!'\" — what NOT to do is surprisingly effective."),
            ("7. Use Variables","Type {{topic}} in sections, then fill values via Variables panel."),
        ]
        for title, body in tips:
            tl = QLabel(title)
            tl.setStyleSheet(f"color:{ACCENT};font-weight:600;font-size:13px;margin-top:10px;")
            lo.addWidget(tl)
            bl = QLabel(body)
            bl.setWordWrap(True)
            bl.setStyleSheet(f"color:{MUTED};font-size:12px;line-height:1.5;")
            lo.addWidget(bl)

        kb = QLabel("Ctrl+Z Undo  •  Ctrl+Shift+Z Redo  •  Ctrl+S Save  •  Ctrl+Shift+C Copy  •  Ctrl+E Enhance  •  Esc Close")
        kb.setWordWrap(True)
        kb.setStyleSheet(f"background:{f"rgba(212,168,67,.1)"};color:{ACCENT};font-size:11px;padding:10px;border-radius:8px;border:1px solid {f"rgba(212,168,67,.2)"};margin-top:10px;")
        lo.addWidget(kb)

class VariablesDialog(QDialog):
    def __init__(self, var_names, var_vals, parent=None):
        super().__init__(parent)
        self.var_vals = var_vals
        self.setWindowTitle("Variables")
        self.setFixedSize(420, 400)
        self.setStyleSheet(f"QDialog{{background:{BG};}} QLabel{{background:transparent;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(20,16,20,16)

        hdr = QHBoxLayout()
        t = QLabel("Variables")
        t.setStyleSheet(f"font-size:16px;font-weight:700;")
        hdr.addWidget(t)
        sub = QLabel("Use {{name}} in sections")
        sub.setStyleSheet(f"font-size:11px;color:{MUTED};")
        hdr.addWidget(sub)
        close = QPushButton("✕")
        close.setFixedSize(28,28)
        close.clicked.connect(self.close)
        hdr.addWidget(close)
        lo.addLayout(hdr)

        self.inputs = {}
        if not var_names:
            empty = QLabel("No variables detected.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color:{MUTED};font-size:12px;padding:30px;")
            lo.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_w = QWidget()
            slo = QVBoxLayout(scroll_w)
            for v in var_names:
                lb = QLabel(f"{{{v}}}")
                lb.setStyleSheet(f"font-family:{MF};font-size:12px;color:{ACCENT};font-weight:600;")
                slo.addWidget(lb)
                inp = QLineEdit(var_vals.get(v,""))
                inp.setPlaceholderText(f"Value for {v}")
                inp.textChanged.connect(lambda txt, n=v: self.var_vals.update({n: txt}))
                self.inputs[v] = inp
                slo.addWidget(inp)
            slo.addStretch()
            scroll.setWidget(scroll_w)
            lo.addWidget(scroll)

class HistoryDialog(QDialog):
    restore = Signal(int)

    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        self.setWindowTitle("History")
        self.setFixedSize(500, 450)
        self.setStyleSheet(f"QDialog{{background:{BG};}} QLabel{{background:transparent;}} QPushButton{{min-width:60px;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(20,16,20,16)

        hdr = QHBoxLayout()
        t = QLabel("History")
        t.setStyleSheet(f"font-size:16px;font-weight:700;")
        hdr.addWidget(t)
        close = QPushButton("✕")
        close.setFixedSize(28,28)
        close.clicked.connect(self.close)
        hdr.addWidget(close)
        lo.addLayout(hdr)

        if not history:
            empty = QLabel("No snapshots yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color:{MUTED};font-size:12px;padding:30px;")
            lo.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            sw = QWidget()
            slo = QVBoxLayout(sw)
            for h in history:
                card = QFrame()
                card.setStyleSheet(f"background:{BG};border:1px solid {BORDER};border-radius:7px;padding:10px;cursor:pointer;")
                card.setCursor(Qt.PointingHandCursor)
                clo = QVBoxLayout(card)
                clo.setContentsMargins(10,8,10,8)
                top = QHBoxLayout()
                nl = QLabel(h["label"])
                nl.setStyleSheet(f"font-weight:600;font-size:13px;")
                top.addWidget(nl)
                fc = sum(1 for v in h["s"].values() if v.strip())
                info = QLabel(f"{fc}/{len(SECS)}  •  {h['ts'].strftime('%H:%M')}")
                info.setStyleSheet(f"font-size:10px;color:{MUTED};font-family:{MF};")
                top.addWidget(info)
                clo.addLayout(top)
                prev = " ".join(v for v in h["s"].values() if v.strip())[:80]
                pl = QLabel(prev+"...")
                pl.setStyleSheet(f"font-size:11px;color:{MUTED};")
                clo.addWidget(pl)
                card.mousePressEvent = lambda e, hid=h["id"]: self.restore.emit(hid); self.close()
                slo.addWidget(card)
            slo.addStretch()
            scroll.setWidget(sw)
            lo.addWidget(scroll)

class QuickInsertDialog(QDialog):
    insert = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Insert")
        self.setFixedSize(460, 520)
        self.setStyleSheet(f"QDialog{{background:{BG};}} QLabel{{background:transparent;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(20,16,20,16)

        hdr = QHBoxLayout()
        t = QLabel("Quick Insert")
        t.setStyleSheet(f"font-size:16px;font-weight:700;")
        hdr.addWidget(t)
        close = QPushButton("✕")
        close.setFixedSize(28,28)
        close.clicked.connect(self.close)
        hdr.addWidget(close)
        lo.addLayout(hdr)

        sub = QLabel("Click to append to the relevant section.")
        sub.setStyleSheet(f"font-size:11px;color:{MUTED};margin-bottom:8px;")
        lo.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        sw = QWidget()
        slo = QVBoxLayout(sw)

        for cat, items in QUICK_INSERTS:
            cl = QLabel(cat.upper())
            cl.setStyleSheet(f"font-size:10px;font-weight:600;color:{MUTED};text-transform:uppercase;letter-spacing:.5px;margin-top:8px;")
            slo.addWidget(cl)
            for label, target, text in items:
                row = QFrame()
                row.setStyleSheet(f"background:transparent;border:1px solid transparent;border-radius:7px;padding:6px 8px;cursor:pointer;")
                row.setCursor(Qt.PointingHandCursor)
                rlo = QHBoxLayout(row)
                rlo.setContentsMargins(4,4,4,4)
                plus = QLabel("+")
                plus.setFixedSize(22,22)
                plus.setAlignment(Qt.AlignCenter)
                plus.setStyleSheet(f"background:{f"rgba(212,168,67,.12)"};color:{ACCENT};border-radius:5px;font-size:11px;font-weight:bold;")
                rlo.addWidget(plus)
                il = QLabel(label)
                il.setStyleSheet(f"font-weight:500;font-size:12px;")
                rlo.addWidget(il, 1)
                tgt = QLabel(target)
                tgt.setStyleSheet(f"font-size:9px;color:{MUTED};background:{BG};padding:1px 5px;border-radius:3px;")
                rlo.addWidget(tgt)
                row.mousePressEvent = lambda e, t=target, tx=text: self.insert.emit(t, tx); self.close()
                row.enterEvent = lambda e, r=row: r.setStyleSheet(f"background:{CARD};border:1px solid {BORDER};border-radius:7px;padding:6px 8px;cursor:pointer;")
                row.leaveEvent = lambda e, r=row: r.setStyleSheet(f"background:transparent;border:1px solid transparent;border-radius:7px;padding:6px 8px;cursor:pointer;")
                slo.addWidget(row)
        slo.addStretch()
        scroll.setWidget(sw)
        lo.addWidget(scroll)

class SaveTemplateDialog(QDialog):
    save = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save as Template")
        self.setFixedSize(380, 200)
        self.setStyleSheet(f"QDialog{{background:{BG};}} QLabel{{background:transparent;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(20,16,20,16)

        t = QLabel("Save as Template")
        t.setStyleSheet(f"font-size:16px;font-weight:700;margin-bottom:12px;")
        lo.addWidget(t)

        lo.addWidget(QLabel("Name"))
        self.name_inp = QLineEdit()
        self.name_inp.setPlaceholderText("My Custom Template")
        lo.addWidget(self.name_inp)

        lo.addWidget(QLabel("Description"))
        self.desc_inp = QLineEdit()
        self.desc_inp.setPlaceholderText("Short description...")
        lo.addWidget(self.desc_inp)

        btn = QPushButton("  Save Template  ")
        btn.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:600;border:none;border-radius:7px;padding:8px 16px;font-size:13px;")
        btn.clicked.connect(self._save)
        lo.addWidget(btn, alignment=Qt.AlignRight)

    def _save(self):
        n = self.name_inp.text().strip()
        if n: self.save.emit(n, self.desc_inp.text().strip())

class IODialog(QDialog):
    imported = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import / Export")
        self.setFixedSize(520, 400)
        self.setStyleSheet(f"QDialog{{background:{BG};}} QLabel{{background:transparent;}} QPushButton{{min-width:80px;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(20,16,20,16)

        t = QLabel("Import / Export")
        t.setStyleSheet(f"font-size:16px;font-weight:700;")
        lo.addWidget(t)

        btns = QHBoxLayout()
        exp = QPushButton("  Export JSON  ")
        exp.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:600;border:none;border-radius:7px;")
        exp.clicked.connect(self._export)
        btns.addWidget(exp)
        imp = QPushButton("  Import JSON  ")
        imp.clicked.connect(self._import_file)
        btns.addWidget(imp)
        lo.addLayout(btns)

        self.ta = QTextEdit()
        self.ta.setPlaceholderText("Or paste JSON here...")
        self.ta.setStyleSheet(f"font-family:{MF};font-size:11px;")
        lo.addWidget(self.ta)

        imp_t = QPushButton("  Import from text above  ")
        imp_t.clicked.connect(self._import_text)
        lo.addWidget(imp_t, alignment=Qt.AlignRight)

    def _export(self, data=None):
        if data is None: return
        j = json.dumps(data, indent=2)
        self.ta.setPlainText(j)
        path, _ = QFileDialog.getSaveFileName(self, "Export", f"prompt-forge-{int(datetime.now().timestamp())}.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f: f.write(j)

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
        if path:
            try:
                with open(path) as f: d = json.load(f)
                self.imported.emit(d)
                self.close()
            except: QMessageBox.warning(self, "Error", "Invalid JSON file")

    def _import_text(self):
        txt = self.ta.toPlainText().strip()
        if not txt: return
        try:
            self.imported.emit(json.loads(txt))
            self.close()
        except: QMessageBox.warning(self, "Error", "Invalid JSON")

# ═══════════════════════ MAIN WINDOW ═══════════════════════

class PromptForge(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prompt Forge — Craft Better Prompts")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 820)
        self.setStyleSheet(STYLE)

        self.st = {s["id"]: "" for s in SECS}
        self.sec_ord = [s["id"] for s in SECS]
        self.pats = {"cot": False, "se": False, "ss": False}
        self.var_vals = {}
        self.history = []
        self.h_id = 0
        self.undo_stack = []
        self.redo_stack = []
        self.last_pushed = ""
        self.split_tab = "full"
        self.custom_tpls = []
        self._compressed = None

        self.data_dir = Path.home() / ".prompt-forge"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "state.json"
        self.load_state()

        self.setup_ui()
        self.setup_shortcuts()
        self.refresh_all()

        self._auto_save = QTimer()
        self._auto_save.timeout.connect(self.save_state)
        self._auto_save.start(10000)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        mlo = QVBoxLayout(central)
        mlo.setContentsMargins(0,0,0,0)
        mlo.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(48)
        hdr.setStyleSheet(f"background:rgba(14,14,14,.92);border-bottom:1px solid {BORDER};")
        hlo = QHBoxLayout(hdr)
        hlo.setContentsMargins(16,0,16,0)
        logo = QLabel("  Prompt Forge  ")
        logo.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:700;font-size:13px;border-radius:7px;padding:4px 10px;")
        hlo.addWidget(logo)
        sub = QLabel("Craft prompts that actually work")
        sub.setStyleSheet(f"font-size:10px;color:{MUTED};")
        hlo.addWidget(sub)
        hlo.addStretch()

        for txt, fn in [("Guide",self.open_guide),("Reset",self.reset_all)]:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            hlo.addWidget(b)
        mlo.addWidget(hdr)

        # Toolbar
        tb = QFrame()
        tb.setFixedHeight(40)
        tb.setStyleSheet(f"background:rgba(22,22,22,.5);border-bottom:1px solid {BORDER};")
        tlo = QHBoxLayout(tb)
        tlo.setContentsMargins(16,4,16,4)
        tlo.setSpacing(5)

        enh = QPushButton("  Enhance  ")
        enh.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:600;border:none;border-radius:6px;font-size:12px;")
        enh.clicked.connect(self.magic_enhance)
        tlo.addWidget(enh)

        for txt, fn in [("Compress",self.compress_prompt),("Quick Add",self.open_qi),("Vars",self.open_vars)]:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            tlo.addWidget(b)
        self.var_badge = QLabel("")
        self.var_badge.setFixedSize(18,18)
        self.var_badge.setAlignment(Qt.AlignCenter)
        self.var_badge.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;border-radius:9px;font-size:9px;font-weight:700;display:none;")
        tlo.addWidget(self.var_badge)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(16)
        sep.setStyleSheet(f"background:{BORDER};")
        tlo.addWidget(sep)

        self.pat_btns = {}
        for key, label in [("cot","CoT"),("se","Self-Eval"),("ss","Steps")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.clicked.connect(lambda checked, k=key: self.toggle_pat(k))
            self.pat_btns[key] = b
            tlo.addWidget(b)

        tlo.addStretch()
        for txt, fn in [("Save Tpl",self.open_save_tpl),("History",self.open_hist),("IO",self.open_io)]:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            tlo.addWidget(b)
        save_b = QPushButton("💾")
        save_b.setFixedSize(28,28)
        save_b.setToolTip("Save snapshot (Ctrl+S)")
        save_b.clicked.connect(self.save_snapshot)
        tlo.addWidget(save_b)
        mlo.addWidget(tb)

        # Structure map
        self.struct_map = QFrame()
        self.struct_map.setFixedHeight(8)
        smlo = QHBoxLayout(self.struct_map)
        smlo.setContentsMargins(16,0,16,4)
        smlo.setSpacing(2)
        mlo.addWidget(self.struct_map)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;width:0;}")

        # Builder scroll
        builder_scroll = QScrollArea()
        builder_scroll.setWidgetResizable(True)
        builder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        builder_w = QWidget()
        self.builder_lo = QVBoxLayout(builder_w)
        self.builder_lo.setContentsMargins(16,8,16,8)
        self.builder_lo.setSpacing(8)
        builder_scroll.setWidget(builder_w)

        # Preview panel
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        preview_w = QWidget()
        preview_w.setFixedWidth(380)
        self.preview_lo = QVBoxLayout(preview_w)
        self.preview_lo.setContentsMargins(0,8,0,8)
        self.preview_lo.setSpacing(10)
        preview_scroll.setWidget(preview_w)

        splitter.addWidget(builder_scroll)
        splitter.addWidget(preview_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        mlo.addWidget(splitter, 1)

        # Templates section
        tpl_frame = QFrame()
        tpl_frame.setStyleSheet("background:transparent;")
        tfl = QVBoxLayout(tpl_frame)
        tfl.setContentsMargins(16,16,16,16)

        tpl_hdr = QHBoxLayout()
        tpl_t = QLabel("Templates")
        tpl_t.setStyleSheet(f"font-size:17px;font-weight:700;")
        tpl_hdr.addWidget(tpl_t)
        tpl_sub = QLabel("Proven starting structures")
        tpl_sub.setStyleSheet(f"font-size:12px;color:{MUTED};margin-left:8px;")
        tpl_hdr.addWidget(tpl_sub)
        tpl_hdr.addStretch()

        self.tpl_combo = QComboBox()
        self.tpl_combo.addItems(["All","Writing","Coding","Analysis","Creative","Custom"])
        self.tpl_combo.currentTextChanged.connect(self.render_templates)
        tpl_hdr.addWidget(self.tpl_combo)
        tfl.addLayout(tpl_hdr)

        self.tpl_grid = QGridLayout()
        self.tpl_grid.setSpacing(8)
        tfl.addLayout(self.tpl_grid)
        mlo.addWidget(tpl_frame)

        # Status bar for toasts
        self.toast_label = QLabel("")
        self.toast_label.setStyleSheet(f"background:{CARD};border:1px solid {ACCENT};color:#e8e4dd;padding:8px 16px;border-radius:8px;font-size:12px;")
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setVisible(False)
        self.statusBar().setFixedHeight(0)
        self.statusBar().addWidget(self.toast_label, 1)

        self._toast_timer = QTimer()
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self.toast_label.hide)

        self._create_sections()
        self._create_preview_panel()

    def _create_sections(self):
        self.section_cards = {}
        for i, sid in enumerate(self.sec_ord):
            sec = next(s for s in SECS if s["id"]==sid)
            card = SectionCard(sec)
            card.textChanged.connect(self._on_section_changed)
            card.moveRequested.connect(lambda d, s=sid: self._move_section(s, d))
            self.section_cards[sid] = card
            self.builder_lo.addWidget(card)

    def _rebuild_sections(self):
        for card in self.section_cards.values():
            self.builder_lo.removeWidget(card)
            card.setParent(None)
        for sid in self.sec_ord:
            self.builder_lo.addWidget(self.section_cards[sid])

    def _create_preview_panel(self):
        # Score card
        score_frame = QFrame()
        score_frame.setStyleSheet(f"background:{CARD};border:1px solid {BORDER};border-radius:10px;")
        slo = QVBoxLayout(score_frame)
        slo.setContentsMargins(14,12,14,12)

        sh = QHBoxLayout()
        st = QLabel("Quality Score")
        st.setStyleSheet(f"font-size:13px;font-weight:600;")
        sh.addWidget(st)
        self.score_label = QLabel("Empty")
        self.score_label.setStyleSheet(f"font-size:10px;font-weight:600;padding:2px 8px;border-radius:5px;background:{CARD};color:{MUTED};")
        sh.addWidget(self.score_label)
        slo.addLayout(sh)

        sr = QHBoxLayout()
        self.score_ring = ScoreRing()
        sr.addWidget(self.score_ring)

        self.sub_metrics_w = QWidget()
        self.sub_metrics_lo = QVBoxLayout(self.sub_metrics_w)
        self.sub_metrics_lo.setContentsMargins(0,0,0,0)
        self.sub_metrics_lo.setSpacing(2)
        sr.addLayout(self.sub_metrics_lo, 1)
        slo.addLayout(sr)

        # Checklist
        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background:{BORDER};")
        slo.addWidget(sep1)
        cl = QLabel("STRUCTURE CHECKLIST")
        cl.setStyleSheet(f"font-size:10px;font-weight:600;color:{MUTED};margin-bottom:4px;")
        slo.addWidget(cl)
        self.checklist_grid = QGridLayout()
        self.checklist_grid.setSpacing(2)
        self.checklist_grid.setColumnMinimumWidth(0, 120)
        slo.addLayout(self.checklist_grid)

        # Balance
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:{BORDER};")
        slo.addWidget(sep2)
        bl = QLabel("SECTION BALANCE")
        bl.setStyleSheet(f"font-size:10px;font-weight:600;color:{MUTED};margin-bottom:4px;")
        slo.addWidget(bl)
        self.balance_w = QWidget()
        self.balance_lo = QHBoxLayout(self.balance_w)
        self.balance_lo.setContentsMargins(0,0,0,0)
        self.balance_lo.setSpacing(1)
        slo.addWidget(self.balance_w)
        self.balance_labels = QHBoxLayout()
        self.balance_labels.setContentsMargins(0,2,0,0)
        self.balance_labels.setSpacing(0)
        slo.addLayout(self.balance_labels)

        # Suggestions
        sep3 = QFrame()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet(f"background:{BORDER};")
        slo.addWidget(sep3)
        self.suggs_lo = QVBoxLayout()
        self.suggs_lo.setSpacing(0)
        self.suggs_lo.setContentsMargins(0,4,0,0)
        slo.addLayout(self.suggs_lo)

        self.preview_lo.addWidget(score_frame)

        # Model metrics
        model_frame = QFrame()
        model_frame.setStyleSheet(f"background:{CARD};border:1px solid {BORDER};border-radius:10px;")
        mlo2 = QVBoxLayout(model_frame)
        mlo2.setContentsMargins(14,12,14,12)

        mh = QHBoxLayout()
        mt = QLabel("AI Model Metrics")
        mt.setStyleSheet(f"font-size:13px;font-weight:600;")
        mh.addWidget(mt)
        self.total_tok_label = QLabel("0 tokens")
        self.total_tok_label.setStyleSheet(f"font-family:{MF};font-size:10px;color:{MUTED};")
        mh.addWidget(self.total_tok_label)
        mlo2.addLayout(mh)

        self.model_table = QTableWidget()
        self.model_table.setColumnCount(5)
        self.model_table.setHorizontalHeaderLabels(["Model","Context Usage","Tokens","Cost","Fit"])
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.model_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.model_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.model_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.model_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.model_table.setColumnWidth(2, 65)
        self.model_table.setColumnWidth(3, 60)
        self.model_table.setColumnWidth(4, 55)
        self.model_table.setRowCount(len(MODELS))
        self.model_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.model_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.model_table.setShowGrid(False)
        mlo2.addWidget(self.model_table)

        self.model_tip = QLabel("")
        self.model_tip.setWordWrap(True)
        self.model_tip.setStyleSheet(f"font-size:11px;color:{MUTED};line-height:1.4;")
        sep4 = QFrame()
        sep4.setFixedHeight(1)
        sep4.setStyleSheet(f"background:{BORDER};")
        mlo2.addWidget(sep4)
        mlo2.addWidget(self.model_tip)

        self.preview_lo.addWidget(model_frame)

        # Preview
        prev_frame = QFrame()
        prev_frame.setStyleSheet(f"background:{CARD};border:1px solid {BORDER};border-radius:10px;")
        plo = QVBoxLayout(prev_frame)
        plo.setContentsMargins(14,12,14,12)

        ph = QHBoxLayout()
        self.split_btns = {}
        for key, label in [("full","Full"),("system","System"),("user","User")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(key=="full")
            b.setStyleSheet(f"border:none;font-size:11px;padding:4px 10px;")
            if key=="full": b.setStyleSheet(f"background:{f"rgba(212,168,67,.12)"};color:{ACCENT};border:none;font-size:11px;padding:4px 10px;border-radius:5px;")
            b.clicked.connect(lambda checked, k=key: self.set_split(k))
            self.split_btns[key] = b
            ph.addWidget(b)
        ph.addStretch()
        self.char_lbl = QLabel("0")
        self.char_lbl.setStyleSheet(f"font-family:{MF};font-size:10px;color:{MUTED};")
        ph.addWidget(self.char_lbl)
        self.word_lbl = QLabel("0w")
        self.word_lbl.setStyleSheet(f"font-family:{MF};font-size:10px;color:{MUTED};")
        ph.addWidget(self.word_lbl)
        plo.addLayout(ph)

        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setStyleSheet(f"QTextEdit{{background:{BG};font-family:{MF};font-size:12px;border:1px solid {BORDER};border-radius:8px;padding:12px;min-height:180px;}}")
        self.preview_box.setPlainText("Your assembled prompt will appear here...")
        plo.addWidget(self.preview_box)

        # Token chips
        tc = QHBoxLayout()
        tc.setSpacing(4)
        self.tok_labels = {}
        for key, color in [("gpt",ACCENT),("claude",INFO),("gemini",OK)]:
            l = QLabel(f"~0")
            l.setStyleSheet(f"font-family:{MF};font-size:9px;color:{MUTED};background:{BG};border:1px solid {BORDER};border-radius:4px;padding:1px 6px;")
            tc.addWidget(l)
            self.tok_labels[key] = l
        tc.addStretch()
        plo.addLayout(tc)

        # Readability
        sep5 = QFrame()
        sep5.setFixedHeight(1)
        sep5.setStyleSheet(f"background:{BORDER};")
        plo.addWidget(sep5)
        self.read_grid = QGridLayout()
        self.read_grid.setSpacing(3)
        plo.addLayout(self.read_grid)

        # Buttons
        btns = QHBoxLayout()
        self.copy_btn = QPushButton("  Copy Prompt  ")
        self.copy_btn.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:600;border:none;border-radius:7px;font-size:12px;")
        self.copy_btn.clicked.connect(self.copy_prompt)
        btns.addWidget(self.copy_btn)
        dl = QPushButton("↓")
        dl.setFixedSize(32,32)
        dl.setToolTip("Download")
        dl.clicked.connect(self.download_prompt)
        btns.addWidget(dl)
        plo.addLayout(btns)

        self.preview_lo.addWidget(prev_frame)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_snapshot)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.copy_prompt)
        QShortcut(QKeySequence("Ctrl+E"), self, self.magic_enhance)
        QShortcut(QKeySequence("Escape"), self, self._esc_close)

    def _esc_close(self):
        for w in self.findChildren(QDialog):
            if w.isVisible(): w.close(); return

    # ═══ STATE MANAGEMENT ═══

    def push_undo(self):
        j = json.dumps({"s":self.st,"o":self.sec_ord,"p":self.pats})
        if j == self.last_pushed: return
        self.last_pushed = j
        self.undo_stack.append(j)
        if len(self.undo_stack) > 50: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append(json.dumps({"s":self.st,"o":self.sec_ord,"p":self.pats}))
        d = json.loads(self.undo_stack.pop())
        self.st.update(d["s"])
        self.sec_ord = d["o"]
        self.pats.update(d["p"])
        self.last_pushed = json.dumps(d)
        self.refresh_all()

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(json.dumps({"s":self.st,"o":self.sec_ord,"p":self.pats}))
        d = json.loads(self.redo_stack.pop())
        self.st.update(d["s"])
        self.sec_ord = d["o"]
        self.pats.update(d["p"])
        self.last_pushed = json.dumps(d)
        self.refresh_all()

    def save_state(self):
        try:
            d = {"s":self.st,"o":self.sec_ord,"p":self.pats,"v":self.var_vals,"c":self.custom_tpls}
            self.data_file.write_text(json.dumps(d))
        except: pass

    def load_state(self):
        try:
            if self.data_file.exists():
                d = json.loads(self.data_file.read_text())
                if "s" in d: self.st.update({k:v for k,v in d["s"].items() if k in self.st})
                if "o" in d: self.sec_ord = [i for i in d["o"] if i in self.st]
                if "p" in d: self.pats.update(d["p"])
                if "v" in d: self.var_vals.update(d["v"])
                if "c" in d: self.custom_tpls = d["c"]
        except: pass

    # ═══ SECTION HANDLERS ═══

    def _on_section_changed(self, sid, text):
        self.st[sid] = text
        self.push_undo()
        self.update_preview()
        self.update_score()
        self.update_struct_map()
        self.update_var_badge()

    def _move_section(self, sid, direction):
        i = self.sec_ord.index(sid)
        ni = i + direction
        if ni < 0 or ni >= len(self.sec_ord): return
        self.push_undo()
        self.sec_ord[i], self.sec_ord[ni] = self.sec_ord[ni], self.sec_ord[i]
        self._rebuild_sections()
        self.update_struct_map()
        self.update_preview()

    # ═══ PREVIEW ═══

    def update_preview(self):
        text = assemble_prompt(self.st, self.sec_ord, self.pats, self.split_tab, True, self.var_vals)
        if not text:
            self.preview_box.setHtml(f'<span style="color:{MUTED};font-family:{FF}">Your assembled prompt will appear here...</span>')
        else:
            html = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            html = re.sub(r"^(## .+)$", lambda m: f'<span style="color:{ACCENT};font-weight:600">{m.group(1)}</span>', html, flags=re.M)
            html = re.sub(r"`([^`]+)`", lambda m: f'<span style="color:{OK};background:rgba(92,184,122,.1);padding:0 3px;border-radius:3px">{m.group(1)}</span>', html)
            html = re.sub(r"^(- .+)$", lambda m: f'<span style="color:{INFO}">{m.group(1)}</span>', html, flags=re.M)
            html = re.sub(r"\{\{(\w+)\}\}", lambda m: f'<span style="background:{f"rgba(212,168,67,.15)"};border:1px solid {f"rgba(212,168,67,.35)"};padding:0 3px;border-radius:3px;font-weight:500;color:{ACCENT}">{{{{{m.group(1)}}}}}</span>', html)
            for pat, hint in VAGUE:
                html = pat.sub(lambda m: f'<span style="background:rgba(180,140,220,.18);border-bottom:2px dotted {VAGUE_C};padding:0 1px;border-radius:2px" title="{hint}">{m.group(0)}</span>', html)
            self.preview_box.setHtml(html)

        self.char_lbl.setText(str(len(text)))
        words = len(text.split()) if text.strip() else 0
        self.word_lbl.setText(f"{words}w")
        self.tok_labels["gpt"].setText(f"~{tok_est(text,3.2)}")
        self.tok_labels["claude"].setText(f"~{tok_est(text,3.8)}")
        self.tok_labels["gemini"].setText(f"~{tok_est(text,3.6)}")

        self.update_readability(text)
        self.update_models(text)

    def set_split(self, tab):
        self.split_tab = tab
        for k, b in self.split_btns.items():
            if k == tab:
                b.setStyleSheet(f"background:{f'rgba(212,168,67,.12)'};color:{ACCENT};border:none;font-size:11px;padding:4px 10px;border-radius:5px;")
            else:
                b.setStyleSheet(f"border:none;font-size:11px;padding:4px 10px;color:{MUTED};")
        self.update_preview()

    # ═══ SCORE ═══

    def update_score(self):
        ov, cl, sp, co, st2 = calc_score(self.st, self.sec_ord)

        color = OK if ov>=80 else ACCENT if ov>=60 else WARN if ov>=35 else ERR
        self.score_ring.set_score(ov, color)

        levels = [(0,"Empty",MUTED,CARD),(1,"Rough",ERR,f"rgba(212,95,95,.12)"),(35,"Getting There",WARN,f"rgba(224,145,69,.12)"),(60,"Solid",ACCENT,f"rgba(212,168,67,.12)"),(80,"Strong",OK,f"rgba(92,184,122,.12)"),(92,"Excellent",OK,f"rgba(92,184,122,.12)")]
        lv = levels[0]
        for l in levels:
            if ov >= l[0]: lv = l
        self.score_label.setText(lv[1])
        self.score_label.setStyleSheet(f"font-size:10px;font-weight:600;padding:2px 8px;border-radius:5px;background:{lv[3]};color:{lv[2]};")

        # Sub-metrics
        for w in self.sub_metrics_w.findChildren(QWidget): self.sub_metrics_lo.removeWidget(w)
        tt = self.st.get("task",""); tw = tt.strip().split() if tt.strip() else []
        c_len = 100 if len(tw)>=15 else 75 if len(tw)>=10 else 40 if len(tw)>=5 else 15 if len(tw)>=2 else 0
        c_verb = 100 if any(v in tt.lower() for v in ACTION_VERBS) else 0
        c_vague = 20 if any(p in tt.lower() for p in VAGUE_PHRASES) else 100
        c_ctx = 100 if len(self.st.get("context","").strip())>50 else 60 if len(self.st.get("context","").strip())>20 else 25 if self.st.get("context","").strip() else 0
        s_fmt = 100 if self.st.get("format","").strip() else 0
        s_con = 100 if self.st.get("constraints","").strip() else 0
        s_ex = 100 if self.st.get("examples","").strip() else 0
        s_neg = 100 if self.st.get("negative","").strip() else 0
        nums = len(re.findall(r"\d+", " ".join(self.st.values())))
        s_num = 100 if nums>=5 else 70 if nums>=3 else 35 if nums>=1 else 0
        sr = 100 if self.st.get("role","").strip() else 0
        stk = 100 if self.st.get("task","").strip() else 0
        sf = 100 if self.st.get("format","").strip() else 0
        sb = 100 if self.st.get("constraints","").strip() and self.st.get("negative","").strip() else (50 if self.st.get("constraints","").strip() or self.st.get("negative","").strip() else 0)
        sc = 100 if self.st.get("task","").strip() and self.st.get("role","").strip() else (40 if self.st.get("task","").strip() or self.st.get("role","").strip() else 0)

        self.sub_metrics_lo.addWidget(SubMetricRow("Clarity", cl, color))
        for l,v,c in [("Task length",c_len,ACCENT),("Action verb",c_verb,OK),("No vague",c_vague,INFO if tw else BORDER),("Context",c_ctx,VAGUE_C)]:
            self.sub_metrics_lo.addWidget(SubMetricRow(l,v,c,True))
        self.sub_metrics_lo.addWidget(SubMetricRow("Specificity", sp, OK))
        for l,v,c in [("Format",s_fmt,ACCENT),("Constraints",s_con,OK),("Examples",s_ex,INFO),("Negative",s_neg,ERR),("Numbers",s_num,VAGUE_C)]:
            self.sub_metrics_lo.addWidget(SubMetricRow(l,v,c,True))
        self.sub_metrics_lo.addWidget(SubMetricRow("Completeness", co, INFO))
        self.sub_metrics_lo.addWidget(SubMetricRow("Structure", st2, VAGUE_C))
        for l,v,c in [("Role",sr,ACCENT),("Task",stk,OK),("Format",sf,INFO),("Guard rails",sb,ERR),("Critical path",sc,VAGUE_C)]:
            self.sub_metrics_lo.addWidget(SubMetricRow(l,v,c,True))

        # Checklist
        for w in self.checklist_grid.findChildren(QWidget): self.checklist_grid.removeWidget(w)
        checks = [("Role assigned",bool(self.st["role"].strip())),("Context given",bool(self.st["context"].strip())),
            ("Task defined",len(self.st["task"].strip())>10),("Format specified",bool(self.st["format"].strip())),
            ("Constraints set",bool(self.st["constraints"].strip())),("Negatives stated",bool(self.st["negative"].strip())),
            ("Examples included",bool(self.st["examples"].strip())),("Tone defined",bool(self.st["tone"].strip()))]
        for i,(l,ok) in enumerate(checks):
            self.checklist_grid.addWidget(CheckItem(l,ok), i//2, i%2)

        # Balance
        for w in self.balance_w.findChildren(QWidget): self.balance_lo.removeWidget(w)
        for w in self.balance_labels.findChildren(QWidget): self.balance_labels.removeWidget(w)
        lens = [len(self.st.get(i,"").strip()) for i in self.sec_ord]
        total = sum(lens)
        if total:
            for i,sid in enumerate(self.sec_ord):
                sec = next(s for s in SECS if s["id"]==sid)
                seg = QFrame()
                seg.setStyleSheet(f"background:{sec['ic2'] if lens[i] else BORDER};border-radius:2px;min-width:2px;")
                seg.setFixedHeight(8)
                seg.setToolTip(f"{sec['t']}: {lens[i]} chars")
                self.balance_lo.addWidget(seg)
            for i,sid in enumerate(self.sec_ord):
                if lens[i]:
                    sec = next(s for s in SECS if s["id"]==sid)
                    l = QLabel(sec["t"].split()[0])
                    l.setStyleSheet(f"font-size:8px;color:{sec['ic2']};")
                    self.balance_labels.addWidget(l)

        # Suggestions
        for w in self.suggs_lo.findChildren(QWidget): self.suggs_lo.removeWidget(w)
        self._update_suggestions(ov, cl, sp, co, st2)

    def _update_suggestions(self, ov, cl, sp, co, st2):
        suggs = []
        if not self.st["task"].strip(): suggs.append(("fa-bullseye", ERR, "Add a task — the most critical section."))
        elif len(self.st["task"].strip().split())<8: suggs.append(("fa-bullseye", WARN, "Task too brief. Add more detail."))
        if not self.st["context"].strip(): suggs.append(("fa-layer-group", WARN, "Context helps the model."))
        if not self.st["format"].strip(): suggs.append(("fa-table-cells", WARN, "Specify output format."))
        if not self.st["constraints"].strip() and sum(1 for v in self.st.values() if v.strip())>=3: suggs.append(("fa-shield-halved", INFO, "Constraints improve quality."))
        if not self.st["negative"].strip() and sum(1 for v in self.st.values() if v.strip())>=4: suggs.append(("fa-ban", INFO, "Negative prompts are effective."))
        if not self.st["examples"].strip() and sum(1 for v in self.st.values() if v.strip())>=4: suggs.append(("fa-lightbulb", INFO, "One example boosts consistency."))
        if not self.st["role"].strip() and sum(1 for v in self.st.values() if v.strip())>=2: suggs.append(("fa-user-gear", INFO, "Assign a role."))
        if cl<50 and self.st["task"].strip(): suggs.append(("fa-spell-check", WARN, "Use action verbs, avoid vague phrasing."))
        if st2<40 and sum(1 for v in self.st.values() if v.strip())>=2: suggs.append(("fa-sitemap", WARN, "Structure weak — add role, format, or guard rails."))
        if not suggs and any(v.strip() for v in self.st.values()): suggs.append(("fa-check-circle", OK, "Looking good! Run it and iterate."))

        for icon, color, text in suggs[:5]:
            row = QFrame()
            row.setStyleSheet(f"background:transparent;border-top:1px solid {BORDER};padding:4px 0;")
            rlo = QHBoxLayout(row)
            rlo.setContentsMargins(0,0,0,0)
            rlo.setSpacing(6)
            il = QLabel("●")
            il.setFixedSize(8,8)
            il.setStyleSheet(f"color:{color};font-size:8px;")
            rlo.addWidget(il)
            tl = QLabel(text)
            tl.setWordWrap(True)
            tl.setStyleSheet(f"font-size:11px;color:{MUTED};line-height:1.3;")
            rlo.addWidget(tl, 1)
            self.suggs_lo.addWidget(row)

    # ═══ STRUCTURE MAP ═══

    def update_struct_map(self):
        for w in self.struct_map.findChildren(QWidget): self.struct_map.layout().removeWidget(w)
        for sid in self.sec_ord:
            sec = next(s for s in SECS if s["id"]==sid)
            filled = bool(self.st.get(sid,"").strip())
            seg = QFrame()
            seg.setStyleSheet(f"background:{sec['ic2'] if filled else BORDER};border-radius:2px;min-width:2px;opacity:{1 if filled else .3};")
            self.struct_map.layout().addWidget(seg)

    # ═══ VAR BADGE ═══

    def update_var_badge(self):
        vs = det_vars(self.st.values())
        if vs:
            self.var_badge.setText(str(len(vs)))
            self.var_badge.show()
        else:
            self.var_badge.hide()

    # ═══ READABILITY ═══

    def update_readability(self, text):
        for w in self.read_grid.findChildren(QWidget): self.read_grid.removeWidget(w)
        rd = readability(text)
        if not rd:
            l = QLabel("No text")
            l.setStyleSheet(f"font-size:10px;color:{MUTED2};grid-column:1/-1;")
            self.read_grid.addWidget(l)
            return
        asl, awl, cxp, fk = rd["asl"], rd["awl"], rd["cxp"], rd["fk"]
        fc = OK if fk<=8 else ACCENT if fk<=12 else WARN if fk<=18 else ERR
        fl = "Easy" if fk<=8 else "Fair" if fk<=12 else "Moderate" if fk<=18 else "Hard"
        items = [("Sent length",f"{asl:.1f}w",""),("Word length",f"{awl:.1f}c",""),("Complex >6c",f"{cxp}%",""),("FK Grade",f"{fk:.1f} {fl}",fc)]
        for i,(l,v,c) in enumerate(items):
            ll = QLabel(l)
            ll.setStyleSheet(f"font-size:10px;color:{MUTED};")
            self.read_grid.addWidget(ll, i, 0)
            vl = QLabel(v)
            vl.setStyleSheet(f"font-family:{MF};font-size:10px;{f'color:{c};' if c else ''}")
            self.read_grid.addWidget(vl, i, 1)

    # ═══ MODEL METRICS ═══

    def update_models(self, text):
        if not text.strip():
            self.total_tok_label.setText("0 tokens")
            self.model_tip.setText("")
            for r in range(len(MODELS)):
                for c in range(5): self.model_table.setItem(r, c, QTableWidgetItem(""))
            return

        base_tok = tok_est(text, 3.5)
        out_mult = 2.5
        self.total_tok_label.setText(f"~{base_tok:,} in + ~{int(base_tok*out_mult):,} out est.")

        best_name, best_score = None, -1
        all_costs = []
        for m in MODELS:
            it = tok_est(text, m["cpT"])
            ot = int(it * out_mult)
            tt2 = it + ot
            pct = min(100, round(tt2/m["ctx"]*100))
            ic = (it/1e6)*m["inC"]
            oc = (ot/1e6)*m["outC"]
            tc = ic+oc
            all_costs.append(tc)

        min_c, max_c = min(all_costs), max(all_costs)
        tips = {
            "GPT-4.1":"Best for: analysis, coding, multi-step reasoning.",
            "GPT-4o":"Great for: general tasks, quick drafts, multimodal.",
            "Claude 4 Sonnet":"Best cost/quality. Excellent at: long-form, nuanced instructions.",
            "Claude 4 Opus":"Most capable for complex tasks. Best for: difficult reasoning, expert analysis.",
            "Gemini 2.5 Pro":"Massive context. Ideal for: very long documents, large codebases.",
            "Gemini 2.5 Flash":"Extremely cheap and fast. Perfect for: high-volume, simple queries.",
            "DeepSeek V3":"Great value. Good for: coding, general reasoning.",
            "Llama 4 Maverick":"Open-weight. Best for: privacy-sensitive, self-hosted deployment.",
        }

        for r, m in enumerate(MODELS):
            it = tok_est(text, m["cpT"])
            ot = int(it * out_mult)
            tt2 = it + ot
            pct = min(100, round(tt2/m["ctx"]*100))
            ic = (it/1e6)*m["inC"]
            oc = (ot/1e6)*m["outC"]
            tc = ic+oc

            fit = 100
            if pct>80: fit -= (pct-80)*2
            if pct>100: fit -= 50
            cn = (tc-min_c)/(max_c-min_c) if max_c>min_c else 0
            fit -= cn*30
            fit = max(0, min(100, round(fit)))
            if fit > best_score: best_score, best_name = fit, m["name"]

            # Name
            ni = QTableWidgetItem(m["name"])
            ni.setForeground(QColor(m["color"]))
            ni.setFont(QFont(FF, 11, QFont.Bold))
            self.model_table.setItem(r, 0, ni)

            # Bar
            bar_w = QWidget()
            blo = QHBoxLayout(bar_w)
            blo.setContentsMargins(4,2,4,2)
            bg = QFrame()
            bg.setStyleSheet(f"background:{BORDER};border-radius:3px;height:5px;")
            bgl = QHBoxLayout(bg)
            bgl.setContentsMargins(0,0,0,0)
            fill = QFrame()
            bc = ERR if pct>80 else WARN if pct>50 else OK
            fill.setFixedHeight(5)
            fill.setStyleSheet(f"background:{bc};border-radius:3px;")
            bgl.addWidget(fill)
            bgl.addStretch()
            blo.addWidget(bg)
            self.model_table.setCellWidget(r, 1, bar_w)
            # Set bar width after layout
            QTimer.singleShot(0, lambda bg2=bg, f2=fill, p=pct: f2.setFixedWidth(max(2, int(bg2.width()*min(p,100)/100))))

            # Tokens
            ti = QTableWidgetItem(f"{it:,}")
            ti.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
            ti.setFont(QFont(MF, 10))
            self.model_table.setItem(r, 2, ti)

            # Cost
            ci = QTableWidgetItem(f"<${tc:.4f}" if tc<0.01 else f"${tc:.2f}")
            ci.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
            ci.setForeground(QColor(OK))
            ci.setFont(QFont(MF, 10))
            self.model_table.setItem(r, 3, ci)

            # Fit
            if pct>100: fl,fc2,fbg2 = "OVER",ERR,f"rgba(212,95,95,.12)"
            elif pct>80: fl,fc2,fbg2 = "TIGHT",WARN,f"rgba(224,145,69,.12)"
            elif pct>50: fl,fc2,fbg2 = "GOOD",ACCENT,f"rgba(212,168,67,.12)"
            else: fl,fc2,fbg2 = "GREAT",OK,f"rgba(92,184,122,.12)"
            fi = QTableWidgetItem(fl)
            fi.setTextAlignment(Qt.AlignCenter)
            fi.setForeground(QColor(fc2))
            fi.setFont(QFont(FF, 9, QFont.Bold))
            self.model_table.setItem(r, 4, fi)

        self.model_table.setRowHeight(0, 24)
        for r in range(len(MODELS)): self.model_table.setRowHeight(r, 32)

        if best_name:
            self.model_tip.setText(f'<span style="color:{OK}">●</span> <b>{best_name}</b> — {tips.get(best_name,"")}')
        else:
            self.model_tip.setText("")

    # ═══ ACTIONS ═══

    def copy_prompt(self):
        if self._compressed:
            QApplication.clipboard().setText(self._compressed)
            self.show_toast("Compressed prompt copied")
            self._compressed = None
            self.copy_btn.setText("  Copy Prompt  ")
            self.copy_btn.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:600;border:none;border-radius:7px;font-size:12px;")
            self.update_preview()
            return
        text = assemble_prompt(self.st, self.sec_ord, self.pats, self.split_tab, True, self.var_vals)
        if not text: self.show_toast("Nothing to copy"); return
        QApplication.clipboard().setText(text)
        self.show_toast("Copied to clipboard")

    def download_prompt(self):
        text = assemble_prompt(self.st, self.sec_ord, self.pats, self.split_tab, True, self.var_vals)
        if not text: self.show_toast("Nothing to download"); return
        path, _ = QFileDialog.getSaveFileName(self, "Download", "prompt.txt", "Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(text)
            self.show_toast("Downloaded")

    def magic_enhance(self):
        removed = enhance_text(self.st, self.sec_ord)
        for sid in self.sec_ord:
            if sid in self.section_cards:
                self.section_cards[sid].editor.setPlainText(self.st[sid])
        self.refresh_all()
        vf = sum(1 for p,h in VAGUE if p.search(" ".join(self.st.values())))
        parts = []
        if removed: parts.append(f"removed {removed} filler{'s' if removed>1 else ''}")
        if vf: parts.append(f"{vf} vague flagged")
        if not parts: parts.append("clean")
        self.show_toast(f"Enhanced: {', '.join(parts)}")

    def compress_prompt(self):
        text = assemble_prompt(self.st, self.sec_ord, self.pats, "full", False)
        if not text.strip(): self.show_toast("Nothing to compress"); return
        compressed, cc = compress_text(text)
        bl, al = len(text), len(compressed)
        pct = round((bl-al)/bl*100) if bl else 0
        html = compressed.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        html = re.sub(r"^(## .+)$", lambda m: f'<span style="color:{ACCENT};font-weight:600">{m.group(1)}</span>', html, flags=re.M)
        html += f'<br><br><span style="color:{OK};font-family:{FF}">Compressed: {bl} → {al} chars ({pct}% smaller, {cc} changes)</span>'
        self.preview_box.setHtml(html)
        self._compressed = compressed
        self.copy_btn.setText("  Copy Compressed  ")
        self.copy_btn.setStyleSheet(f"background:{OK};color:#0e0e0e;font-weight:600;border:none;border-radius:7px;font-size:12px;")
        QTimer.singleShot(8000, self._reset_copy_btn)
        self.show_toast(f"Compressed: -{bl-al} chars ({pct}%)")

    def _reset_copy_btn(self):
        self._compressed = None
        self.copy_btn.setText("  Copy Prompt  ")
        self.copy_btn.setStyleSheet(f"background:{ACCENT};color:#0e0e0e;font-weight:600;border:none;border-radius:7px;font-size:12px;")
        self.update_preview()

    def toggle_pat(self, key):
        self.pats[key] = not self.pats[key]
        b = self.pat_btns[key]
        if self.pats[key]:
            b.setStyleSheet(f"background:{f'rgba(212,168,67,.12)'};color:{ACCENT};border:1px solid {f'rgba(212,168,67,.3)'};font-size:12px;padding:5px 10px;border-radius:6px;")
        else:
            b.setStyleSheet(f"border:1px solid {BORDER};font-size:12px;padding:5px 10px;border-radius:6px;color:{MUTED};")
        self.update_preview()
        self.update_score()

    def reset_all(self):
        self.push_undo()
        for k in self.st: self.st[k] = ""
        for sid, card in self.section_cards.items(): card.editor.clear()
        self.pats = {"cot":False,"se":False,"ss":False}
        for k,b in self.pat_btns.items(): b.setChecked(False); b.setStyleSheet(f"border:1px solid {BORDER};font-size:12px;padding:5px 10px;border-radius:6px;color:{MUTED};")
        self.refresh_all()
        self.show_toast("Cleared")

    # ═══ SNAPSHOTS ═══

    def save_snapshot(self):
        if not any(v.strip() for v in self.st.values()): self.show_toast("Nothing to save"); return
        self.h_id += 1
        self.history.insert(0, {"id":self.h_id,"ts":datetime.now(),"s":{...self.st},"o":[...self.sec_ord],"p":{...self.pats},"label":f"Snap {self.h_id}"})
        if len(self.history)>20: self.history.pop()
        self.show_toast(f"Snap {self.h_id} saved")

    # ═══ DIALOGS ═══

    def open_guide(self): GuideDialog(self).exec()

    def open_vars(self):
        vs = det_vars(self.st.values())
        d = VariablesDialog(vs, self.var_vals, self)
        d.finished.connect(lambda: (self.update_preview(), self.update_score()))
        d.exec()

    def open_hist(self):
        d = HistoryDialog(self.history, self)
        d.restore.connect(self._restore_snap)
        d.exec()

    def _restore_snap(self, hid):
        h = next((h for h in self.history if h["id"]==hid), None)
        if not h: return
        self.push_undo()
        self.st.update(h["s"])
        self.sec_ord = h["o"]
        self.pats.update(h["p"])
        self.refresh_all()
        self.show_toast(f'Restored "{h["label"]}"')

    def open_io(self):
        d = IODialog(self)
        d.imported.connect(self._apply_import)
        d._export({"v":4,"s":self.st,"o":self.sec_ord,"p":self.pats,"v2":self.var_vals,"c":self.custom_tpls})
        d.exec()

    def _apply_import(self, data):
        if "s" in data: self.st.update({k:v for k,v in data["s"].items() if k in self.st})
        if "o" in data: self.sec_ord = [i for i in data["o"] if i in self.st]
        if "p" in data: self.pats.update(data["p"])
        if "v" in data: self.var_vals.update(data["v"])
        if "v2" in data: self.var_vals.update(data["v2"])
        if "c" in data: self.custom_tpls = data["c"]
        self.refresh_all()
        self.show_toast("Imported")

    def open_qi(self):
        d = QuickInsertDialog(self)
        d.insert.connect(self._do_qi_insert)
        d.exec()

    def _do_qi_insert(self, target, text):
        self.push_undo()
        cur = self.st.get(target,"")
        self.st[target] = (cur.strip()+"\n"+text).strip() if cur.strip() else text
        if target in self.section_cards:
            self.section_cards[target].editor.setPlainText(self.st[target])
            if not self.section_cards[target]._open:
                self.section_cards[target].toggle()
        self.refresh_all()
        self.show_toast(f"Added to {next((s['t'] for s in SECS if s['id']==target),'?')}")

    def open_save_tpl(self):
        if not any(v.strip() for v in self.st.values()): self.show_toast("Fill sections first"); return
        d = SaveTemplateDialog(self)
        d.save.connect(self._do_save_tpl)
        d.exec()

    def _do_save_tpl(self, name, desc):
        self.custom_tpls.append({"name":name,"cat":"custom","d":desc or "Custom","data":{...self.st}})
        self.save_state()
        self.render_templates()
        self.show_toast(f'Template "{name}" saved')

    # ═══ TEMPLATES ═══

    def render_templates(self, cat="All"):
        for w in self.tpl_grid.findChildren(QWidget): self.tpl_grid.removeWidget(w)
        all_t = TEMPLATES + self.custom_tpls
        if cat != "All": all_t = [t for t in all_t if t["cat"].lower()==cat.lower()]
        for i, t in enumerate(all_t):
            card = QFrame()
            card.setStyleSheet(f"background:{CARD};border:1px solid {BORDER};border-radius:9px;padding:12px;cursor:pointer;")
            card.setCursor(Qt.PointingHandCursor)
            clo = QVBoxLayout(card)
            clo.setContentsMargins(12,10,12,10)
            clo.setSpacing(4)
            nl = QLabel(t["name"])
            nl.setStyleSheet(f"font-weight:600;font-size:13px;")
            clo.addWidget(nl)
            dl = QLabel(t["d"])
            dl.setWordWrap(True)
            dl.setStyleSheet(f"font-size:11px;color:{MUTED};")
            clo.addWidget(dl)
            cl = QLabel(t["cat"].upper())
            cl.setStyleSheet(f"font-size:9px;text-transform:uppercase;letter-spacing:.4px;color:{MUTED};background:{BG};padding:2px 6px;border-radius:3px;")
            clo.addWidget(cl)
            idx = i
            is_custom = t["cat"]=="custom"
            card.mousePressEvent = lambda e, tpl=t, ic=is_custom: self._apply_tpl(tpl, ic)
            card.enterEvent = lambda e, c=card: c.setStyleSheet(f"background:{CARD};border:1px solid {ACCENT};border-radius:9px;padding:12px;cursor:pointer;")
            card.leaveEvent = lambda e, c=card: c.setStyleSheet(f"background:{CARD};border:1px solid {BORDER};border-radius:9px;padding:12px;cursor:pointer;")
            self.tpl_grid.addWidget(card, i//3, i%3)

    def _apply_tpl(self, tpl, is_custom):
        self.push_undo()
        data = tpl["data"]
        for k,v in data.items():
            if k in self.st: self.st[k] = v
        self.refresh_all()
        self.show_toast(f'Applied "{tpl["name]}"'))

    # ═══ TOAST ═══

    def show_toast(self, msg):
        self.toast_label.setText(f"  {msg}  ")
        self.toast_label.adjustSize()
        self.toast_label.move((self.width()-self.toast_label.width())//2, self.height()-60)
        self.toast_label.show()
        self.toast_label.raise_()
        self._toast_timer.start(2500)

    # ═══ REFRESH ALL ═══

    def refresh_all(self):
        self._rebuild_sections()
        for sid, card in self.section_cards.items():
            if self.st[sid].strip(): card.set_open(True)
        for k,b in self.pat_btns.items():
            if self.pats[k]:
                b.setStyleSheet(f"background:{f'rgba(212,168,67,.12)'};color:{ACCENT};border:1px solid {f'rgba(212,168,67,.3)'};font-size:12px;padding:5px 10px;border-radius:6px;")
            else:
                b.setStyleSheet(f"border:1px solid {BORDER};font-size:12px;padding:5px 10px;border-radius:6px;color:{MUTED};")
        self.update_preview()
        self.update_score()
        self.update_struct_map()
        self.update_var_badge()
        self.render_templates(self.tpl_combo.currentText())
        self.save_state()

# ═══════════════════════ ENTRY ═══════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PromptForge()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()