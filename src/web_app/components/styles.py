"""
src/web_app/components/styles.py — Global CSS for Finnie's Streamlit UI.

Inject this exactly once, at app startup, via:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap');

:root {
  --bg-primary:    #0a0a0f;
  --bg-secondary:  #131419;
  --bg-tertiary:   #1c1d24;
  --border-subtle: #2a2b35;
  --border-active: #10b981;
  --text-primary:  #fafafa;
  --text-secondary:#a1a1aa;
  --text-muted:    #71717a;
  --accent-emerald:#10b981;
  --accent-cyan:   #06b6d4;
  --accent-violet: #8b5cf6;
  --accent-amber:  #f59e0b;
  --accent-coral:  #f87171;
  --gradient-hero: linear-gradient(135deg, #10b981 0%, #06b6d4 50%, #8b5cf6 100%);
  --gradient-warm: linear-gradient(135deg, #f59e0b 0%, #f87171 100%);
}

/* Hide Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] {
  visibility: hidden;
  height: 0;
}

/* Global font + background */
html, body, .stApp, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
  background-color: var(--bg-primary) !important;
  color: var(--text-primary) !important;
}

/* Headings */
h1, h2, h3, h4 {
  font-family: 'Outfit', sans-serif !important;
  letter-spacing: -0.02em !important;
}

h1 {
  font-size: 3.5rem !important;
  font-weight: 800 !important;
  line-height: 1.1 !important;
  background: var(--gradient-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0.5rem !important;
}

h2 { font-size: 1.75rem !important; font-weight: 700 !important; color: var(--text-primary) !important; }
h3 { font-size: 1.25rem !important; font-weight: 600 !important; color: var(--text-primary) !important; }
p, li, span { color: var(--text-secondary); }

/* Hero pill */
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: var(--accent-emerald);
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 1.25rem;
}

.hero-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-emerald);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 0 8px var(--accent-emerald);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.5; transform: scale(0.85); }
}

/* Tab strip */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg-secondary);
  border-radius: 14px;
  padding: 6px;
  gap: 4px;
  border: 1px solid var(--border-subtle);
}

.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 10px !important;
  padding: 10px 20px !important;
  font-weight: 500 !important;
  transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"],
.stTabs [data-baseweb="tab"] p {
  color: var(--text-secondary) !important;
}

.stTabs [data-baseweb="tab"]:hover {
  background: var(--bg-tertiary) !important;
}

.stTabs [data-baseweb="tab"]:hover,
.stTabs [data-baseweb="tab"]:hover p {
  color: var(--text-primary) !important;
}

/* Active tab — gradient background, force white text on ALL states incl. hover */
.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"]:hover {
  background: var(--gradient-hero) !important;
}

.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"]:hover,
.stTabs [aria-selected="true"]:hover p {
  color: white !important;
  font-weight: 600 !important;
}

.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* Buttons */
.stButton > button {
  background: var(--bg-tertiary) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  transition: all 0.2s ease;
}

.stButton > button:hover:not(:disabled) {
  background: var(--bg-secondary) !important;
  border-color: var(--accent-emerald) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.15);
}

.stButton > button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Input fields */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox > div > div {
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 10px !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', sans-serif !important;
}

/* Chat input outer container */
[data-testid="stChatInput"] {
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 14px !important;
  padding: 8px !important;
  box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.04) !important;
}

/* Chat input inner textarea/input */
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {
  background: var(--bg-tertiary) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 10px !important;
  font-family: 'Inter', sans-serif !important;
  caret-color: var(--accent-emerald) !important;
}

/* Chat input placeholder text */
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInput"] input::placeholder,
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
  color: #9ca3af !important;
  opacity: 1 !important;
}

/* Chat input focus state */
[data-testid="stChatInput"]:focus-within {
  border-color: var(--accent-emerald) !important;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.14) !important;
}

/* Remove unwanted white background from chat input internal wrappers */
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] div,
[data-testid="stChatInput"] form {
  background: transparent !important;
}

/* Send button */
[data-testid="stChatInput"] button {
  background: var(--bg-tertiary) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 10px !important;
}

[data-testid="stChatInput"] button:hover {
  background: rgba(16, 185, 129, 0.14) !important;
  border-color: var(--accent-emerald) !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 16px !important;
  padding: 18px 22px !important;
  margin-bottom: 12px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: var(--bg-secondary) !important;
  border-right: 1px solid var(--border-subtle) !important;
}

section[data-testid="stSidebar"] h3 {
  font-size: 0.7rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: var(--text-muted) !important;
}

/* Metrics */
[data-testid="stMetric"] {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 18px;
  transition: all 0.2s ease;
}

[data-testid="stMetric"]:hover {
  border-color: var(--accent-emerald);
}

[data-testid="stMetricLabel"] {
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
}

[data-testid="stMetricValue"] {
  font-family: 'Outfit', sans-serif !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
}

/* Reusable component classes */
.finnie-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 16px;
  transition: all 0.2s ease;
}

.finnie-card:hover {
  border-color: var(--accent-emerald);
  transform: translateY(-2px);
}

.feature-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge-coming-soon {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: var(--accent-amber);
}

.badge-live {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: var(--accent-emerald);
}

/* Section divider */
.section-eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

/* Hero subtitle */
.hero-subtitle {
  font-size: 1.15rem;
  color: var(--text-secondary);
  font-weight: 400;
  max-width: 780px;
  margin-bottom: 1.5rem;
}

/* Markdown links */
a {
  color: var(--accent-cyan) !important;
  text-decoration: none !important;
  transition: color 0.2s ease;
}
a:hover { color: var(--accent-emerald) !important; }

/* Expander */
.streamlit-expanderHeader {
  background: var(--bg-secondary) !important;
  border-radius: 10px !important;
}

/* Spinner color */
.stSpinner > div { border-top-color: var(--accent-emerald) !important; }
</style>
"""