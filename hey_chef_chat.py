import PyPDF2  # for PDF text extraction
from io import BytesIO
import streamlit as st
from groq import Groq
import re
from datetime import datetime, timedelta

import io
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import requests
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import base64
from openai import OpenAI
import random
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
st.set_page_config(
    page_title="KitchenMate – AI Cooking",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ═══════════════════════════════════════════════════════════════
# CUSTOM CSS - TRANSPARENT UI WITH PROPER STYLING
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ════════════════════════════════════════════════════════
   ANNAPURNĀ — MASTER CSS  (mobile-first, orange brand)
   ════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap');

/* ── CSS Variables ── */
:root {
    --orange:        #FF7518;
    --orange-light:  #FF8F3F;
    --orange-dim:    rgba(255,117,24,0.14);
    --orange-border: rgba(255,117,24,0.28);
    --orange-glow:   rgba(255,117,24,0.22);
    --bg:            #0C0E14;
    --surface:       #13161F;
    --surface2:      #1A1E2A;
    --surface3:      #222738;
    --text:          #EEF0F8;
    --text-dim:      rgba(238,240,248,0.52);
    --text-muted:    rgba(238,240,248,0.32);
    --green:         #3DD68C;
    --red:           #FF5757;
    --blue:          #4D9EFF;
    --radius:        14px;
    --radius-sm:     9px;
    --shadow:        0 4px 24px rgba(0,0,0,0.4);
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text) !important;
}
h1, h2, h3, h4, .stSubheader {
    font-family: 'Syne', sans-serif !important;
    letter-spacing: -0.025em !important;
    color: var(--text) !important;
}

/* ── App background ── */
.stApp {
    background: var(--bg) !important;
    background-image:
        radial-gradient(ellipse 70% 40% at 10% 0%, rgba(255,117,24,0.07) 0%, transparent 70%),
        radial-gradient(ellipse 50% 30% at 90% 100%, rgba(255,117,24,0.04) 0%, transparent 70%) !important;
}
.main, .block-container, section,
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
.element-container {
    background: transparent !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--orange-border) !important;
}
section[data-testid="stSidebar"] > div { background: var(--surface) !important; }
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: var(--orange) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-radius: 12px !important;
    padding: 4px 6px !important;
    gap: 2px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: var(--text-dim) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 7px 13px !important;
    white-space: nowrap !important;
    border-bottom: none !important;
    transition: all 0.18s ease !important;
}
.stTabs [aria-selected="true"] {
    background: var(--orange) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 12px var(--orange-glow) !important;
}
/* Kill Streamlit's default red/blue tab underline */
.stTabs [data-baseweb="tab-highlight"] {
    background: transparent !important;
    height: 0 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--surface2) !important;
    border: 1px solid var(--orange-border) !important;
    color: var(--orange) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 0.45rem 1.1rem !important;
    transition: all 0.18s ease !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    background: var(--orange-dim) !important;
    border-color: var(--orange) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px var(--orange-glow) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Primary buttons */
[data-testid="baseButton-primary"],
.stButton > button[kind="primary"] {
    background: var(--orange) !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 4px 18px var(--orange-glow) !important;
    font-weight: 600 !important;
}
[data-testid="baseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background: var(--orange-light) !important;
    box-shadow: 0 6px 24px rgba(255,117,24,0.4) !important;
    transform: translateY(-1px) !important;
}

/* ── Inputs ── */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stSelectbox > div > div {
    background: var(--surface2) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: border-color 0.18s !important;
}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--orange) !important;
    box-shadow: 0 0 0 3px rgba(255,117,24,0.12) !important;
    outline: none !important;
}
input::placeholder, textarea::placeholder { color: var(--text-muted) !important; }

/* Number input +/- buttons */
.stNumberInput button {
    background: var(--surface3) !important;
    border-color: rgba(255,255,255,0.08) !important;
    color: var(--orange) !important;
    border-radius: 6px !important;
}

/* ── Chat input — pinned bottom bar (ChatGPT-style) ── */
/*
   Streamlit renders the chat input inside [data-testid="stBottom"].
   We pin it fixed to the viewport bottom, spanning from the sidebar
   edge to the right edge. On mobile the sidebar collapses so we use
   left:0 instead.
*/
div[data-testid="stBottom"],
div[data-testid="stChatInputContainer"],
.stChatInputContainer {
    position: fixed !important;
    bottom: 0 !important;
    left: 21rem !important;   /* sidebar width — matches Streamlit default */
    right: 0 !important;
    z-index: 99999 !important;
    /* frosted-glass dark backdrop */
    background: rgba(12,14,20,0.97) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border-top: 1px solid var(--orange-border) !important;
    box-shadow: 0 -8px 40px rgba(0,0,0,0.55) !important;
    padding: 10px 32px 16px 32px !important;
    /* prevents content from going edge-to-edge on ultra-wide screens */
    box-sizing: border-box !important;
}

/* Ensure enough bottom clearance so the last message
   is never hidden behind the fixed input bar */
section.main > div.block-container {
    padding-bottom: 130px !important;
}

/* ── Chat input field ── */
[data-testid="stChatInput"] > div {
    background: var(--surface2) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 18px !important;
    backdrop-filter: blur(8px) !important;
    box-shadow: 0 2px 18px rgba(0,0,0,0.25) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    /* cap width for readability on very wide screens */
    max-width: 900px !important;
    margin: 0 auto !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--orange) !important;
    box-shadow: 0 0 0 3px rgba(255,117,24,0.14), 0 2px 18px rgba(0,0,0,0.25) !important;
}
[data-testid="stChatInput"] input,
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text) !important;
    border: none !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.95rem !important;
    line-height: 1.5 !important;
}
/* Send button inside the input */
[data-testid="stChatInput"] button {
    color: var(--orange) !important;
    transition: color 0.15s !important;
}
[data-testid="stChatInput"] button:hover { color: var(--orange-light) !important; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    margin-bottom: 6px !important;
}
[data-testid="stChatMessageContent"] {
    background: var(--surface) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 16px !important;
    padding: 12px 16px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.6 !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2) !important;
}
/* User messages get orange tint */
.stChatMessage:nth-child(odd) [data-testid="stChatMessageContent"] {
    background: rgba(255,117,24,0.1) !important;
    border-color: var(--orange-border) !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: background 0.15s !important;
}
.streamlit-expanderHeader:hover { background: var(--surface2) !important; }
.streamlit-expanderContent {
    background: var(--surface) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
}

/* ── Alerts ── */
.stSuccess { background: rgba(61,214,140,0.1) !important; border: 1px solid rgba(61,214,140,0.3) !important; border-radius: 10px !important; }
.stError   { background: rgba(255,87,87,0.1)  !important; border: 1px solid rgba(255,87,87,0.3)  !important; border-radius: 10px !important; }
.stWarning { background: rgba(255,193,7,0.1)  !important; border: 1px solid rgba(255,193,7,0.3)  !important; border-radius: 10px !important; }
.stInfo    { background: rgba(77,158,255,0.1) !important; border: 1px solid rgba(77,158,255,0.3) !important; border-radius: 10px !important; }

/* ── Toggles & checkboxes ── */
.stCheckbox label, .stToggle label {
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 1rem 0 !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
}

/* ── Mobile responsiveness ── */
@media (max-width: 768px) {
    /* On mobile Streamlit collapses the sidebar, so the input spans full width */
    div[data-testid="stBottom"],
    div[data-testid="stChatInputContainer"],
    .stChatInputContainer {
        left: 0 !important;
        padding: 8px 14px 14px 14px !important;
    }
    /* Restore full-width input field on small screens */
    [data-testid="stChatInput"] > div {
        max-width: 100% !important;
        border-radius: 14px !important;
    }
    /* More bottom padding so last message clears keyboard + input bar */
    section.main > div.block-container {
        padding-bottom: 150px !important;
    }
    .stTabs [data-baseweb="tab"] { font-size: 0.72rem !important; padding: 6px 9px !important; }
    .block-container { padding: 1rem 0.75rem !important; }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--orange-border); border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: var(--orange); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS - UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def display_message(role, content, msg_index=None):
    """
    Displays chat message with avatars and copy button.
    
    Args:
        role: "user" or "assistant"
        content: Message text (supports markdown)
        msg_index: Unique index to avoid duplicate widget keys
    """
    # Avatar URLs
    avatars = {
        "user": "https://api.dicebear.com/7.x/avataaars/svg?seed=user",
        "assistant": "https://api.dicebear.com/7.x/bottts/svg?seed=chef&backgroundColor=FF6B35"
    }
    
    with st.chat_message(role, avatar=avatars.get(role)):
        st.markdown(content)
        
        # Add copy button for assistant messages — use unique index to avoid key collisions
        if role == "assistant":
            key = f"copy_msg_{msg_index}" if msg_index is not None else f"copy_msg_{id(content)}"
            if st.button("📋 Copy", key=key, help="Copy to clipboard"):
                st.code(content, language=None)
                st.toast("Copied! 🎉", icon="✅")

def format_recipe(recipe_text, recipe_uid=None):
    """
    Formats recipe with expandable sections and copy buttons.
    recipe_uid: unique identifier to avoid key collisions when called multiple times.
    """
    uid = recipe_uid if recipe_uid is not None else int(time.time() * 1000)
    # Ingredients expander
    with st.expander("🥘 Ingredients", expanded=True):
        ingredients = [line for line in recipe_text.split("\n") if line.strip().startswith("-") or line.strip().startswith("•")]
        if ingredients:
            for ing in ingredients:
                st.markdown(ing)
            if st.button("📋 Copy Ingredients", key=f"copy_ing_{uid}"):
                st.code("\n".join(ingredients), language=None)
                st.toast("Ingredients copied!", icon="🥘")
        else:
            st.info("No ingredients detected in standard format")
    
    # Steps expander
    with st.expander("👨‍🍳 Cooking Steps", expanded=True):
        steps = [line for line in recipe_text.split("\n") if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("Step"))]
        if steps:
            for step in steps:
                st.markdown(step)
            if st.button("📋 Copy Steps", key=f"copy_steps_{uid}"):
                st.code("\n".join(steps), language=None)
                st.toast("Steps copied!", icon="👨‍🍳")
        else:
            st.info("No steps detected in standard format")
    
    # Full recipe copy
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📄 Copy Full Recipe", key=f"copy_full_{uid}", use_container_width=True, type="primary"):
            st.code(recipe_text, language=None)
            st.balloons()
            st.toast("Full recipe copied!", icon="📄")
def auto_extract_ingredients_from_recipe(recipe_text):
    """
    Automatically extracts ingredients list from last recipe.
    Returns: list of ingredient names (strings)
    """
    ingredients = extract_ingredients(recipe_text, jain_mode=st.session_state.jain_mode)
    if not ingredients:
        return []
    return [ing["name"] for ing in ingredients if ing and "name" in ing]
# ═══════════════════════════════════════════════════════════════
# FIREBASE INITIALIZATION (safe for Streamlit reruns)
# ═══════════════════════════════════════════════════════════════
# ================= FIREBASE INITIALIZATION (safe for Streamlit reruns) =================

APP_NAME = "annapurna-default"

if APP_NAME not in firebase_admin._apps:
    try:
        cred_dict = {
            "type": "service_account",
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, name=APP_NAME)
    except Exception as e:
        st.error(f"Firebase initialization failed: {str(e)}\nCheck secrets in Streamlit Cloud")
        st.stop()

# Always define db safely
db = firestore.client(app=firebase_admin.get_app(APP_NAME))

# ================= SESSION STATE INITIALIZATION =================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "show_onboarding" not in st.session_state:
    st.session_state.show_onboarding = False
if "user_preferences" not in st.session_state:
    st.session_state.user_preferences = {}

# ================= AUTHENTICATION FUNCTIONS ==============       
# ================= AUTHENTICATION FUNCTIONS =================

def hash_password(password):
    """Simple password hashing using hashlib"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def create_account(name, email, password):
    """Create new user account in Firestore"""
    try:
        # Check if email already exists
        users_ref = db.collection("users")
        existing = users_ref.where("email", "==", email).limit(1).get()
        
        if len(list(existing)) > 0:
            return False, "Email already registered. Please login instead."
        
        user_id = f"user_{uuid.uuid4().hex}"
        doc_ref = db.collection("users").document(user_id)
        doc_ref.set({
            "user_id": user_id,
            "name": name,
            "email": email,
            "password_hash": hash_password(password),
            "created_at": datetime.now().isoformat()
        })
        return True, user_id
    except Exception as e:
        return False, str(e)

def login_user(email, password):
    """Verify credentials and return user data"""
    try:
        users_ref = db.collection("users")
        results = users_ref.where("email", "==", email).limit(1).get()
        
        users = list(results)
        if not users:
            return False, None, "No account found with this email."
        
        user_data = users[0].to_dict()
        
        if user_data.get("password_hash") != hash_password(password):
            return False, None, "Incorrect password."
        
        return True, user_data, "Login successful!"
    except Exception as e:
        return False, None, str(e)

def show_login():
    """Display login/signup page"""
    
    st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1>🍳 KitchenMate</h1>
            <p style='color: #888; font-size: 16px;'>Your AI-Powered Cooking Assistant</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Tab selector stored in session state
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "login"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Tab buttons
        tab_col1, tab_col2 = st.columns(2)
        with tab_col1:
            if st.button(
                "🔑 Login",
                use_container_width=True,
                type="primary" if st.session_state.auth_tab == "login" else "secondary"
            ):
                st.session_state.auth_tab = "login"
                st.rerun()
        with tab_col2:
            if st.button(
                "📝 Create Account",
                use_container_width=True,
                type="primary" if st.session_state.auth_tab == "signup" else "secondary"
            ):
                st.session_state.auth_tab = "signup"
                st.rerun()
        
        st.markdown("---")
        
        # ── LOGIN TAB ──────────────────────────────────────────────
        if st.session_state.auth_tab == "login":
            st.markdown("#### Welcome back 👋")
            
            with st.form("login_form"):
                email = st.text_input("📧 Email", placeholder="you@example.com")
                password = st.text_input("🔒 Password", type="password", placeholder="Your password")
                
                login_btn = st.form_submit_button("Login →", use_container_width=True, type="primary")
                
                if login_btn:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        with st.spinner("Logging in..."):
                            success, user_data, message = login_user(email, password)
                        
                        if success:
                            st.session_state.user_id = user_data["user_id"]
                            st.session_state.user_email = user_data["email"]
                            st.session_state.user_name = user_data["name"]
                            st.session_state.is_authenticated = True
                            st.session_state.show_onboarding = False
                            st.success(f"Welcome back, {user_data['name']}! 🎉")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            # Google login option below the form
            st.markdown("---")
            st.markdown("<p style='text-align:center; color:#888; font-size:13px;'>Or sign in with</p>", unsafe_allow_html=True)
            if st.button("🔵  Continue with Google", use_container_width=True):
                st.info("💡 Google Sign-In requires Firebase setup. Coming soon!", icon="ℹ️")
                # ← You can re-wire your existing Firebase Google flow here later
        
        # ── SIGNUP TAB ─────────────────────────────────────────────
        else:
            st.markdown("#### Create your account 🚀")
            
            with st.form("signup_form"):
                name = st.text_input("👤 Full Name", placeholder="John Doe")
                email = st.text_input("📧 Email", placeholder="you@example.com")
                password = st.text_input("🔒 Password", type="password", placeholder="Min. 8 characters")
                confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password")
                
                signup_btn = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
                
                if signup_btn:
                    # Validation
                    if not all([name, email, password, confirm_password]):
                        st.error("Please fill in all fields.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters.")
                    elif password != confirm_password:
                        st.error("Passwords don't match.")
                    elif "@" not in email:
                        st.error("Please enter a valid email address.")
                    else:
                        with st.spinner("Creating your account..."):
                            success, result = create_account(name, email, password)
                        
                        if success:
                            st.session_state.user_id = result
                            st.session_state.user_email = email
                            st.session_state.user_name = name
                            st.session_state.is_authenticated = True
                            st.session_state.show_onboarding = True
                            st.success("Account created! Let's set you up 🎉")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {result}")
            
            # Google signup option
            st.markdown("---")
            st.markdown("<p style='text-align:center; color:#888; font-size:13px;'>Or sign up with</p>", unsafe_allow_html=True)
            if st.button("🔵  Sign up with Google", use_container_width=True):
                st.info("💡 Google Sign-In coming soon!", icon="ℹ️")
        
        # ── GUEST ACCESS ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("<p style='text-align:center; color:#888; font-size:13px;'>Just browsing?</p>", unsafe_allow_html=True)
        if st.button("👤  Continue as Guest", use_container_width=True):
            st.session_state.user_id = f"guest_{uuid.uuid4().hex[:8]}"
            st.session_state.user_email = "guest@annapurna.app"
            st.session_state.user_name = "Guest"
            st.session_state.is_authenticated = True
            st.session_state.show_onboarding = True
            st.rerun()

def onboarding():
    """Show onboarding screen for new users"""
    st.title("⚙️ Quick Setup")
    st.markdown(f"### Welcome, {st.session_state.user_name}! 👋")
    
    with st.form("onboarding_form"):
        diet = st.radio(
            "🥗 Diet Preference",
            ["Pure Veg", "Vegetarian", "Non-Veg", "Vegan", "Jain"],
            help="This helps us customize recipe suggestions"
        )
        
        allergies = st.text_input(
            "🚫 Allergies (comma-separated)",
            placeholder="e.g., peanuts, dairy, shellfish"
        )
        
        submitted = st.form_submit_button("Save & Start Cooking! 🚀", use_container_width=True)
        
        if submitted:
            prefs = {
                "diet": diet,
                "allergies": allergies,
                "created_at": datetime.now().isoformat()
            }
            
            # Save to Firestore (only for non-guest users)
            if not st.session_state.user_email.startswith("guest"):
                try:
                    doc_ref = db.collection("users").document(st.session_state.user_id)
                    doc_ref.set({
                        "email": st.session_state.user_email,
                        "name": st.session_state.user_name,
                        "preferences": prefs
                    }, merge=True)
                    st.success("✅ Preferences saved!")
                except Exception as e:
                    st.warning(f"⚠️ Couldn't save to cloud: {str(e)}")
            
            # Apply preferences to session
            st.session_state.user_preferences = prefs
            st.session_state.allergies = allergies
            
            if diet == "Jain":
                st.session_state.jain_mode = True
            if diet in ["Pure Veg", "Vegan", "Jain"]:
                st.session_state.pure_veg_mode = True
            
            st.session_state.show_onboarding = False
            st.balloons()
            time.sleep(1)
            st.rerun()

def load_user_data():
    """Load user's saved data from Firestore — uses .get() with defaults to prevent KeyError"""
    if st.session_state.user_email.startswith("guest"):
        return  # Skip for guest users
    
    try:
        doc_ref = db.collection("users").document(st.session_state.user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            
            # Load preferences safely
            prefs = data.get("preferences", {})
            if prefs:
                st.session_state.user_preferences = prefs
                st.session_state.allergies = prefs.get("allergies", "")
                
                diet = prefs.get("diet", "")
                if diet == "Jain":
                    st.session_state.jain_mode = True
                if diet in ["Pure Veg", "Vegan", "Jain"]:
                    st.session_state.pure_veg_mode = True
            
            # Load inventory safely — use .get() with empty-dict/list defaults
            st.session_state.inventory = data.get("inventory", st.session_state.inventory)
            st.session_state.inventory_prices = data.get("inventory_prices", {})
            st.session_state.inventory_expiry = data.get("inventory_expiry", {})
            raw_grocery = data.get("grocery_list", [])
            st.session_state.grocery_list = set(raw_grocery) if isinstance(raw_grocery, list) else set()
            st.session_state.diet_charts = data.get("diet_charts", {})
            
    except Exception as e:
        st.warning(f"Couldn't load saved data: {str(e)}")

# ================= AUTH CHECK =================

# Initialize Firebase auth check
st.markdown("""
<script>
    // Check if Firebase auth data exists in localStorage (from previous session)
    window.firebaseAuthData = JSON.parse(localStorage.getItem('firebaseAuthData') || 'null');
    
    if (window.firebaseAuthData) {
        // User has cached auth data, pass to parent
        window.parent.postMessage({
            type: 'firebaseAuthRestored',
            data: window.firebaseAuthData
        }, '*');
    }
    
    // Listen for messages from child frames
    window.addEventListener('message', function(event) {
        if (event.data && event.data.type === 'google-login-success') {
            // Store auth data in localStorage
            localStorage.setItem('firebaseAuthData', JSON.stringify(event.data.data));
            // Trigger page reload to update Streamlit
            window.location.reload();
        }
    });
</script>
""", unsafe_allow_html=True)

# Check if user is authenticated
if not st.session_state.is_authenticated:
    # Check for query parameters with Google login info
    query_params = st.query_params
    
    # Check for user_id from Google login
    if "user_id" in query_params:
        try:
            st.session_state.user_id = query_params.get("user_id", [""])[0] if isinstance(query_params.get("user_id"), list) else query_params.get("user_id")
            st.session_state.user_email = query_params.get("email", [""])[0] if isinstance(query_params.get("email"), list) else query_params.get("email")
            st.session_state.user_name = query_params.get("name", ["Guest"])[0] if isinstance(query_params.get("name"), list) else query_params.get("name", "Guest")
            st.session_state.is_authenticated = True
            st.session_state.show_onboarding = True
            
            # Clear query params
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
    
    show_login()
    st.stop()

# Load user data on first login
if st.session_state.is_authenticated and "data_loaded" not in st.session_state:
    load_user_data()
    
    # Automatic expiration countdown
    today = datetime.now().date()
    
    # Initialize last_opened if missing
    if "last_opened_date" not in st.session_state:
        st.session_state.last_opened_date = today
    
    # Calculate days passed since last open
    days_passed = (today - st.session_state.last_opened_date).days
    
    if days_passed > 0:
        updated = False
        for item, days_left in list(st.session_state.inventory_expiry.items()):
            if isinstance(days_left, (int, float)):
                new_days = days_left - days_passed
                st.session_state.inventory_expiry[item] = max(-30, new_days)  # don't go below -30
                updated = True
        
        if updated:
            # Optional: save updated expiry to Firestore
            if not st.session_state.user_email.startswith("guest"):
                try:
                    db.collection("users").document(st.session_state.user_id).set({
                        "inventory_expiry": dict(st.session_state.inventory_expiry)
                    }, merge=True)
                except:
                    pass  # silent fail
        
        # Update last opened date
        st.session_state.last_opened_date = today
    
    st.session_state.data_loaded = True

# Show onboarding if needed
if st.session_state.show_onboarding:
    onboarding()
    st.stop()

# ================= API KEYS =================
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Initialize clients
client = Groq(api_key=GROQ_API_KEY)

openrouter_client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ================= REST OF YOUR CODE CONTINUES HERE =================
# ================= SESSION STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "grocery_list" not in st.session_state:
    st.session_state.grocery_list = set()
if "inventory" not in st.session_state:
    st.session_state.inventory = {
        "salt": 500, "chilli powder": 200, "turmeric": 150,
        "rice": 2000, "oil": 1000, "onion": 10, "tomato": 8,
        "paneer": 500, "potato": 2000, "milk": 1000, "garlic": 200, "ginger": 150
    }
if "inventory_prices" not in st.session_state:
    st.session_state.inventory_prices = {}
if "inventory_expiry" not in st.session_state:
    st.session_state.inventory_expiry = {}
if "meal_plan" not in st.session_state:
    st.session_state.meal_plan = {}
if "allergies" not in st.session_state:
    st.session_state.allergies = ""
if "custom_recipes" not in st.session_state:
    st.session_state.custom_recipes = {}
if "show_cooking_check" not in st.session_state:
    st.session_state.show_cooking_check = False
if "show_nutrition" not in st.session_state:
    st.session_state.show_nutrition = False
if "show_substitutes" not in st.session_state:
    st.session_state.show_substitutes = False
if "last_recipe" not in st.session_state:
    st.session_state.last_recipe = ""
if "pure_veg_mode" not in st.session_state:
    st.session_state.pure_veg_mode = False
if "health_mode" not in st.session_state:
    st.session_state.health_mode = False
if "language_mode" not in st.session_state:
    st.session_state.language_mode = "Hinglish"
if "tried_recipes" not in st.session_state:
    st.session_state.tried_recipes = []
if "favourite_recipes" not in st.session_state:
    st.session_state.favourite_recipes = {}
if "diet_charts" not in st.session_state:
    st.session_state.diet_charts = {}
if "unit_system" not in st.session_state:
    st.session_state.unit_system = "metric"
if "servings" not in st.session_state:
    st.session_state.servings = 1
if "cooking_mode" not in st.session_state:
    st.session_state.cooking_mode = False
if "current_step" not in st.session_state:
    st.session_state.current_step = 0
if "cooking_steps" not in st.session_state:
    st.session_state.cooking_steps = []
if "ingredients_shown" not in st.session_state:
    st.session_state.ingredients_shown = False
if "missing_ingredients" not in st.session_state:
    st.session_state.missing_ingredients = []
if "processing_video" not in st.session_state:
    st.session_state.processing_video = False
if "video_recipe" not in st.session_state:
    st.session_state.video_recipe = ""
if "jain_mode" not in st.session_state:
    st.session_state.jain_mode = False
# Initialize auth-related session state (prevents AttributeError)
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "show_onboarding" not in st.session_state:
    st.session_state.show_onboarding = False
if "user_preferences" not in st.session_state:
    st.session_state.user_preferences = {}
if "gym_diet_chart" not in st.session_state:
    st.session_state.gym_diet_chart = None  # stores analyzed/edited chart summary
if "detected_ingredients" not in st.session_state:
    st.session_state.detected_ingredients = []

# Listen for Firebase login from iframe
st.components.v1.html("""
    <script>
        window.addEventListener('message', function(event) {
            if (event.data.type === 'firebase_login') {
                const url = new URL(window.location);
                url.searchParams.set('auth', 'success');
                url.searchParams.set('uid', event.data.uid);
                url.searchParams.set('email', encodeURIComponent(event.data.email));
                window.location = url;
            }
        });
    </script>
""", height=0)

    # ================= NEW: IMAGE DETECTION HELPER =================
def detect_ingredients_from_image(image_bytes):
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = openrouter_client.chat.completions.create( 
            model="gpt-4o-mini",  # Vision-capable model available on OpenRouter
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "List all visible food ingredients in this image. One item per line. Use simple English names."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=200
        )
        text = response.choices[0].message.content.strip()
        items = [line.strip().lower() for line in text.split("\n") if line.strip()]
        return items
    except Exception as e:
        st.error(f"Detection error: {str(e)}")
        return []
def get_expiry_estimate(item_name):
    """Simple estimate for expiry in days"""
    item = item_name.lower()
    if any(x in item for x in ["tomato", "onion", "cucumber", "spinach", "coriander", "curry leaves"]):
        return random.randint(3, 7)   # fresh veggies
    elif any(x in item for x in ["potato", "carrot", "beetroot", "pumpkin"]):
        return random.randint(10, 20) # root veggies
    elif "milk" in item or "curd" in item:
        return random.randint(2, 5)
    elif "paneer" in item:
        return random.randint(3, 6)
    elif any(x in item for x in ["rice", "dal", "flour", "oil", "spices"]):
        return random.randint(180, 365) # long shelf
    else:
        return random.randint(7, 30)  # default
def detect_youtube_url(text):
    """Detect YouTube URLs in text and extract video ID"""
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def extract_youtube_transcript(video_id):
    """Extract transcript from YouTube video"""
    try:
        # Try to get transcript in English first, then Hindi
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except:
            try:
                transcript = transcript_list.find_transcript(['hi', 'hi-IN'])
            except:
                # Get any available transcript
                transcript = transcript_list.find_generated_transcript(['en', 'hi'])
        
        # Fetch and combine all text
        transcript_data = transcript.fetch()
        full_text = " ".join([entry['text'] for entry in transcript_data])
        return full_text
    
    except TranscriptsDisabled:
        return None
    except NoTranscriptFound:
        return None
    except Exception as e:
        return None

def get_video_title(video_id):
    """Get YouTube video title using oEmbed API"""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('title', 'Unknown Video')
    except:
        pass
    return 'Unknown Video'

def get_video_description(video_id):
    """Get YouTube video description using YouTube Data API v3"""
    if not YOUTUBE_API_KEY:
        return None, "⚠️ YouTube API key not configured. Please add your API key in the code."
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if response['items']:
            snippet = response['items'][0]['snippet']
            title = snippet.get('title', 'Unknown Video')
            description = snippet.get('description', '')
            return {
                'title': title,
                'description': description
            }, None
        else:
            return None, "Video not found"
            
    except HttpError as e:
        return None, f"API Error: {str(e)}"
    except Exception as e:
        return None, f"Error: {str(e)}"

def extract_recipe_links(description):
    """Extract URLs from video description"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, description)
    
    # Filter out common non-recipe URLs
    recipe_urls = []
    exclude_patterns = ['instagram.com', 'facebook.com', 'twitter.com', 'youtube.com', 'youtu.be']
    
    for url in urls:
        if not any(pattern in url.lower() for pattern in exclude_patterns):
            recipe_urls.append(url)
    
    return recipe_urls

def scrape_recipe_from_url(url):
    """Scrape recipe content from external URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Simple text extraction (you can enhance this with BeautifulSoup for better parsing)
            text = response.text
            # Remove HTML tags for basic parsing
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:5000]  # Limit to first 5000 chars
        return None
    except Exception as e:
        return None

def parse_recipe_from_transcript(transcript_text, video_title=""):
    """Use AI to extract recipe from transcript"""
    prompt = f"""
You are a recipe extractor. Below is a transcript from a cooking video titled "{video_title}".

Extract the recipe in this format:

**Recipe: [Dish Name]**

**Ingredients:**
- ingredient 1 with quantity
- ingredient 2 with quantity
(list all mentioned)

**Steps:**
1. Step one
2. Step two
(numbered steps)

Transcript:
{transcript_text[:3000]}

Be concise and practical. If ingredients aren't clearly mentioned, make reasonable estimates based on the cooking steps described.
"""
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error parsing recipe: {str(e)}"

def parse_recipe_from_description(description_text, scraped_content="", video_title=""):
    """Use AI to extract recipe from description + scraped content"""
    combined_text = f"Video Title: {video_title}\n\nDescription:\n{description_text}\n\n"
    
    if scraped_content:
        combined_text += f"Recipe Page Content:\n{scraped_content}"
    
    prompt = f"""
You are a recipe extractor. Extract the complete recipe with exact measurements.

{combined_text[:4000]}

Format the recipe as:

**Recipe: [Dish Name]**

**Ingredients:**
- ingredient 1 with EXACT quantity (e.g., 2 cups, 500g)
- ingredient 2 with EXACT quantity
(list ALL ingredients with measurements)

**Steps:**
1. Detailed step one
2. Detailed step two
(numbered steps)

IMPORTANT: Extract EXACT quantities. Don't estimate - use the measurements provided.
"""
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error parsing recipe: {str(e)}"

# ================= HELPERS =================
def get_quantity_status(qty):
    if qty >= 500:
        return "High", "green"
    elif qty >= 200:
        return "Medium", "orange"
    else:
        return "Low", "red"

UNIT_CONVERSIONS = {
    "g": {"imperial": ("oz", 0.035274), "metric": ("g", 1.0)},
    "kg": {"imperial": ("lbs", 2.20462), "metric": ("kg", 1.0)},
    "gram": {"imperial": ("oz", 0.035274), "metric": ("g", 1.0)},
    "grams": {"imperial": ("oz", 0.035274), "metric": ("g", 1.0)},
    "ml": {"imperial": ("fl oz", 0.033814), "metric": ("ml", 1.0)},
    "l": {"imperial": ("cups", 4.22675), "metric": ("l", 1.0)},
    "pcs": {"imperial": ("pcs", 1.0), "metric": ("pcs", 1.0)},
    "piece": {"imperial": ("piece", 1.0), "metric": ("piece", 1.0)},
    "pieces": {"imperial": ("pieces", 1.0), "metric": ("pieces", 1.0)},
    "cup": {"imperial": ("cup", 1.0), "metric": ("cup", 1.0)},
    "cups": {"imperial": ("cups", 1.0), "metric": ("cups", 1.0)},
}

def convert_quantity(qty_str, target_system="metric"):
    if qty_str in ["as needed", "to taste", "a pinch"]:
        return qty_str
    try:
        parts = qty_str.split(maxsplit=1)
        num = float(parts[0])
        unit = parts[1].lower() if len(parts) > 1 else ""
        base_unit = unit.rstrip('s')
        if base_unit not in UNIT_CONVERSIONS:
            return qty_str
        conv = UNIT_CONVERSIONS[base_unit][target_system]
        new_unit, factor = conv
        new_num = round(num * factor, 2) if factor != 1.0 else num
        return f"{new_num} {new_unit}"
    except:
        return qty_str

def scale_quantity(qty_str, servings=1):
    if servings <= 1:
        return qty_str
    try:
        parts = qty_str.split(maxsplit=1)
        num = float(parts[0])
        rest = " " + parts[1] if len(parts) > 1 else ""
        return f"{round(num * servings, 1)}{rest}"
    except:
        return qty_str
def generate_weekly_plan_from_chart(chart_summary):
    with st.spinner("Creating your personalized 7-day plan..."):
        plan_prompt = f"""
        You are an expert Indian meal planner for fitness goals.
        
        User's gym diet chart summary:
        {chart_summary}
        
        User's preferences:
        - Allergies: {st.session_state.get('allergies', 'None')}
        - Diet mode: {'Jain' if st.session_state.get('jain_mode') else 'Normal'}
        - Pure Veg: {'Yes' if st.session_state.get('pure_veg_mode') else 'No'}
        
        Generate a realistic 7-day Indian meal plan:
        - Breakfast, Mid-morning snack, Lunch, Evening snack, Dinner
        - Match protein/calorie targets from chart
        - Use simple home ingredients
        - Suggest recipes or simple meals
        
        Format:
        Day 1:
        - Breakfast: [meal] (~X cal, Xg protein)
        - ...
        
        At the end, list missing ingredients not in inventory.
        """
        
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": plan_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.6,
                max_tokens=1500
            )
            plan_text = response.choices[0].message.content.strip()
            
            st.markdown("### Your 7-Day Gym Plan")
            st.markdown(plan_text)
            
            # Extract missing items (simple regex - improve later)
            missing_match = re.search(r"Missing ingredients:(.*)", plan_text, re.DOTALL | re.IGNORECASE)
            if missing_match:
                missing_items = [item.strip() for item in missing_match.group(1).split("\n") if item.strip()]
                for item in missing_items:
                    st.session_state.grocery_list.add(item.lower())
                st.success(f"Added {len(missing_items)} missing items to grocery list!")
            
            # Save plan to meal planner (simplified)
            today = datetime.now().date()
            for i in range(7):
                day_key = (today + timedelta(days=i)).strftime("%Y-%m-%d")
                if day_key not in st.session_state.meal_plan:
                    st.session_state.meal_plan[day_key] = {}
                st.session_state.meal_plan[day_key]["Gym Plan"] = "Generated from chart"
            
            st.success("Plan added to Meal Planner tab!")
            
        except Exception as e:
            st.error(f"Plan generation failed: {str(e)}")
def add_items_from_receipt(receipt_text):
    lines = [line.strip() for line in receipt_text.split("\n") if line.strip() and "|" in line]
    added_count = 0
    
    for line in lines:
        try:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            name = parts[0].lower()
            qty_str = parts[1]
            unit = parts[2].lower()
            price = float(parts[3].replace("₹", "").strip()) if len(parts) > 3 else 0
            
            # Convert to grams/ml/pcs
            qty_num = float(re.search(r'\d*\.?\d+', qty_str).group()) if re.search(r'\d', qty_str) else 500
            if "kg" in unit:
                qty_num *= 1000
            elif "l" in unit:
                qty_num *= 1000
            
            # Validate quantity before adding
            if qty_num <= 0:
                continue
            
            key = name
            st.session_state.inventory[key] = int(qty_num)
            if price > 0:
                st.session_state.inventory_prices[key] = price / (qty_num / 100)  # per 100g/ml
            added_count += 1
            
        except:
            continue
    
    if added_count > 0:
        st.success(f"Added {added_count} items to inventory!")
        st.rerun()
    else:
        st.warning("No valid items found.")

def add_missing_items_from_receipt(receipt_text):
    lines = [line.strip() for line in receipt_text.split("\n") if line.strip() and "|" in line]
    added_count = 0
    
    for line in lines:
        try:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue
            name = parts[0].lower()
            
            # Skip if already in inventory
            if name in st.session_state.inventory:
                continue
                
            qty_str = parts[1]
            qty_num = float(re.search(r'\d*\.?\d+', qty_str).group()) if re.search(r'\d', qty_str) else 500
            st.session_state.inventory[name] = int(qty_num)
            added_count += 1
            
        except:
            continue
    
    if added_count > 0:
        st.success(f"Added {added_count} missing items!")
        st.rerun()
    else:
        st.info("All items already in inventory!")

# ================= INGREDIENT ACCEPT PATTERNS =================

# Comprehensive food ingredient categories
VEGETABLES = [
    "onion", "tomato", "potato", "garlic", "ginger", "carrot", "beetroot",
    "capsicum", "bell pepper", "cabbage", "cauliflower", "broccoli",
    "spinach", "palak", "methi", "fenugreek", "coriander", "cilantro",
    "curry leaves", "mint", "pudina", "beans", "peas", "corn",
    "cucumber", "radish", "turnip", "pumpkin", "bottle gourd", "lauki",
    "bitter gourd", "karela", "ridge gourd", "turai", "eggplant", "brinjal",
    "okra", "bhindi", "mushroom", "zucchini", "lettuce", "celery",
    "spring onion", "leek", "sweet potato", "yam", "colocasia", "arbi"
]

SPICES = [
    "turmeric", "haldi", "cumin", "jeera", "coriander", "dhaniya",
    "chilli", "chili", "red chilli", "green chilli", "kashmiri chilli",
    "black pepper", "white pepper", "cardamom", "elaichi", "cinnamon",
    "dalchini", "clove", "laung", "bay leaf", "tej patta", "star anise",
    "fennel", "saunf", "fenugreek", "methi", "mustard", "sarson", "rai",
    "asafoetida", "hing", "nutmeg", "jaiphal", "mace", "javitri",
    "carom seeds", "ajwain", "nigella", "kalonji", "sesame", "til",
    "poppy seeds", "khus khus", "garam masala", "chaat masala",
    "pav bhaji masala", "chole masala", "biryani masala", "tandoori masala",
    "curry powder", "sambhar powder", "rasam powder", "chilli powder",
    "coriander powder", "cumin powder", "turmeric powder", "ginger powder",
    "garlic powder", "dried mango", "amchur", "dried pomegranate", "anardana",
    "saffron", "kesar", "vanilla", "oregano", "basil", "thyme", "rosemary",
    "paprika", "cayenne"
]

GRAINS_PULSES = [
    "rice", "basmati rice", "sona masoori", "brown rice", "jasmine rice",
    "wheat", "flour", "atta", "maida", "all purpose flour", "whole wheat",
    "semolina", "sooji", "rava", "besan", "gram flour", "chickpea flour",
    "corn flour", "cornstarch", "rice flour", "ragi", "finger millet",
    "jowar", "sorghum", "bajra", "pearl millet", "oats", "quinoa",
    "dal", "lentil", "moong dal", "mung dal", "toor dal", "arhar dal",
    "chana dal", "masoor dal", "urad dal", "chickpea", "kabuli chana",
    "black chickpea", "kala chana", "rajma", "kidney beans", "black beans",
    "white beans", "pinto beans", "soybean", "peanut", "groundnut",
    "almond", "badam", "cashew", "kaju", "walnut", "akhrot", "pistachio",
    "pista", "raisin", "kishmish", "dates", "khajoor", "coconut", "nariyal"
]

DAIRY_PRODUCTS = [
    "milk", "doodh", "cream", "heavy cream", "fresh cream", "whipping cream",
    "butter", "makhan", "ghee", "clarified butter", "paneer", "cottage cheese",
    "cheese", "cheddar", "mozzarella", "parmesan", "cream cheese",
    "curd", "yogurt", "dahi", "buttermilk", "chaas", "khoya", "mawa",
    "condensed milk", "evaporated milk", "milk powder", "malai"
]

PROTEINS = [
    "chicken", "mutton", "lamb", "goat", "beef", "pork", "fish", "machli",
    "prawn", "shrimp", "crab", "salmon", "tuna", "pomfret", "rohu",
    "egg", "anda", "tofu", "soya chunks", "soy", "tempeh"
]

OILS_FATS = [
    "oil", "tel", "mustard oil", "coconut oil", "olive oil", "sunflower oil",
    "vegetable oil", "sesame oil", "groundnut oil", "peanut oil",
    "ghee", "butter", "margarine", "lard"
]

SWEETENERS = [
    "sugar", "chini", "jaggery", "gur", "brown sugar", "honey", "shahad",
    "maple syrup", "corn syrup", "stevia", "artificial sweetener",
    "palm sugar", "coconut sugar", "date syrup"
]

SAUCES_CONDIMENTS = [
    "tomato sauce", "ketchup", "soy sauce", "vinegar", "sirka",
    "tamarind", "imli", "lemon", "nimbu", "lime", "orange", "pomegranate",
    "tomato paste", "tomato puree", "chilli sauce", "hot sauce",
    "worcestershire sauce", "fish sauce", "oyster sauce", "hoisin sauce",
    "mayonnaise", "mustard sauce", "pickle", "achar", "chutney"
]

BREADS_PASTA = [
    "bread", "pav", "bun", "roti", "chapati", "naan", "paratha",
    "puri", "bhatura", "kulcha", "pasta", "macaroni", "spaghetti",
    "noodles", "vermicelli", "seviyan", "couscous"
]

BEVERAGES = [
    "water", "pani", "tea", "chai", "coffee", "juice", "coconut water",
    "stock", "broth", "vegetable stock", "chicken stock", "bone broth"
]

OTHERS = [
    "salt", "namak", "baking soda", "baking powder", "yeast", "gelatin",
    "agar agar", "corn", "cornmeal", "breadcrumbs", "panko",
    "chocolate", "cocoa", "coffee powder", "tea leaves"
]

# Combine all categories
ALL_FOOD_INGREDIENTS = (
    VEGETABLES + SPICES + GRAINS_PULSES + DAIRY_PRODUCTS + 
    PROTEINS + OILS_FATS + SWEETENERS + SAUCES_CONDIMENTS + 
    BREADS_PASTA + BEVERAGES + OTHERS
)

# Create a set for faster lookup
FOOD_INGREDIENTS_SET = set([item.lower() for item in ALL_FOOD_INGREDIENTS])
# ================= JAIN DIET RESTRICTIONS =================
# Ingredients NOT allowed in Jain diet (grown underground)
JAIN_RESTRICTED_INGREDIENTS = [
    # Root vegetables
    "potato", "potatoes", "aloo", "sweet potato", "shakarkandi",
    "onion", "onions", "pyaz", "spring onion", "scallion", "leek",
    "garlic", "lahsun", "lehsun",
    "ginger", "adrak",
    "radish", "mooli", "daikon",
    "carrot", "carrots", "gajar",
    "beetroot", "beet", "chukandar",
    "turnip", "shalgam",
    "yam", "suran", "jimikand",
    "colocasia", "arbi", "taro root",
    "elephant yam", "suran",
    "turmeric", "haldi",  # Fresh turmeric root
    "ginger garlic paste",
    "peanut", "groundnut", "moongfali",  # Grows underground
]

# Create set for faster lookup
JAIN_RESTRICTED_SET = set([item.lower() for item in JAIN_RESTRICTED_INGREDIENTS])

def is_jain_compatible(ingredient_name):
    """Check if ingredient is compatible with Jain diet"""
    ingredient_name = ingredient_name.lower().strip()
    
    # Check if it contains any restricted ingredient
    for restricted in JAIN_RESTRICTED_SET:
        if restricted in ingredient_name:
            # Exception: turmeric powder is allowed
            if "turmeric" in ingredient_name and "powder" in ingredient_name:
                continue
            return False
    
    return True

def get_jain_substitute(ingredient_name):
    """Get Jain-friendly substitute for restricted ingredient"""
    ingredient_name = ingredient_name.lower()
    
    substitutes = {
        "potato": "raw banana (kachha kela), arrowroot (ararot), or sweet corn",
        "onion": "asafoetida (hing) for flavor, or finely chopped cabbage",
        "garlic": "asafoetida (hing) for flavor",
        "ginger": "dry ginger powder (sonth) or green chilli for heat",
        "radish": "cucumber or white pumpkin (petha)",
        "carrot": "bottle gourd (lauki), red pumpkin, or tomatoes",
        "beetroot": "red pumpkin or tomatoes for color",
        "turnip": "white pumpkin (petha) or bottle gourd",
        "peanut": "cashew, almond, or melon seeds",
        "turmeric": "turmeric powder (powder form is allowed)",
        "ginger garlic paste": "green chilli paste with asafoetida (hing)",
    }
    
    for key, substitute in substitutes.items():
        if key in ingredient_name:
            return substitute
    
    return "Please check Jain diet guidelines for substitute"
# Cooking verbs to reject
COOKING_VERBS = [
    "cook", "stir", "add", "mix", "serve", "fry", "boil", "bake", "heat",
    "preheat", "chop", "slice", "dice", "grate", "grind", "pour", "simmer",
    "use", "put", "take", "keep", "let", "bring", "reduce", "thicken",
    "turn", "flip", "cover", "uncover", "sauté", "roast", "steam",
    "blend", "whisk", "knead", "marinate", "garnish", "season", "taste"
]

def is_valid_food_ingredient(name):
    """Check if the name is a valid food ingredient"""
    name = name.lower().strip()
    
    # Too short
    if len(name) < 3:
        return False
    
    # Check if it's a cooking verb
    if any(name.startswith(verb) for verb in COOKING_VERBS):
        return False
    
    # Check if any known ingredient is in the name
    for ingredient in FOOD_INGREDIENTS_SET:
        if ingredient in name or name in ingredient:
            return True
    
    return False
def extract_ingredients(text, jain_mode=False):
    """Extract ingredients line by line from recipe text"""
    jain_excluded = ['onion', 'garlic', 'potato', 'carrot', 'beetroot',
                     'radish', 'turnip', 'leek', 'shallot', 'scallion', 'spring onion']

    # Try to isolate the ingredients section
    text_lower = text.lower()
    ing_markers = ['ingredients:', 'ingredients', 'सामग्री:', 'what you need:', 'required:']
    step_markers = ['instructions:', 'steps:', 'method:', 'directions:', 'how to make:', 'विधि:']

    ing_start = -1
    for marker in ing_markers:
        idx = text_lower.find(marker)
        if idx != -1:
            ing_start = idx + len(marker)
            break

    step_start = len(text)
    for marker in step_markers:
        idx = text_lower.find(marker)
        if idx != -1 and idx > ing_start:
            step_start = idx
            break

    if ing_start != -1:
        section = text[ing_start:step_start]
    else:
        section = text

    ingredients = []
    seen = set()

    for line in section.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Remove bullet/numbering
        line = re.sub(r'^[-•*✓✔►▶\d]+[.)\s]*', '', line).strip()
        if not line or len(line) < 3:
            continue

        # Skip lines that look like headers or steps
        if any(m in line.lower() for m in ['step', 'instruction', 'method', 'note:', 'tip:']):
            continue

        # Try to split qty from name
        # Pattern: optional number + optional unit + ingredient name
        match = re.match(
            r'^([\d½¼¾⅓⅔\./\-\s]+)?\s*'
            r'(cups?|tbsp|tsp|tablespoons?|teaspoons?|kg|g|grams?|ml|l|liters?|litres?|'
            r'pieces?|pcs?|medium|large|small|handful|pinch|bunch|cloves?|slices?|packets?|cans?)?\s*'
            r'(?:of\s+)?(.+)',
            line, re.IGNORECASE
        )

        if match:
            qty_num = (match.group(1) or '').strip()
            unit    = (match.group(2) or '').strip()
            name    = (match.group(3) or '').strip()
        else:
            name    = line
            qty_num = ''
            unit    = ''

        # Clean up name
        name = re.sub(r'\(.*?\)', '', name).strip()   # remove parentheses
        name = re.sub(r',.*$', '', name).strip()         # remove after comma
        name = name.lower().strip(' -–')

        if not name or len(name) < 2:
            continue

        if jain_mode and any(j in name for j in jain_excluded):
            continue

        if name in seen:
            continue
        seen.add(name)

        qty_str = f"{qty_num} {unit}".strip() if (qty_num or unit) else "as needed"
        ingredients.append({'name': name, 'qty': qty_str})

    return ingredients

def extract_steps(text):
    """Extract cooking steps from recipe"""
    text_lower = text.lower()
    
    step_markers = r'(steps?:?|instructions?:?|method:?|विधि:?|how to make:?|procedure:?)'
    step_start = re.search(step_markers, text_lower)
    
    if not step_start:
        return []
    
    steps_text = text[step_start.end():].strip()
    
    step_patterns = [
        r'^\d+[\.\)]\s+(.+?)(?=\n\d+[\.\)]|\Z)',
        r'^[-•]\s+(.+?)(?=\n[-•]|\Z)',
        r'^[a-z]\)\s+(.+?)(?=\n[a-z]\)|\Z)',
    ]
    
    steps = []
    for pattern in step_patterns:
        matches = re.findall(pattern, steps_text, re.MULTILINE | re.IGNORECASE)
        if matches:
            steps = [m.strip() for m in matches if m.strip()]
            break
    
    if not steps:
        
        steps = [s.strip() for s in steps_text.split('\n\n') if s.strip()]
    
    return steps[:15]

def get_system_prompt():
    base = """You are KitchenMate - a chill, friendly Indian cooking assistant.
Be casual and helpful. Use simple language.

CRITICAL RULE: You are a RECIPE GENERATOR, not an echo bot!
- If someone asks for a dish (like "butter chicken", "pasta", "biryani"), ALWAYS give the FULL RECIPE with ingredients and steps
- NEVER just repeat the dish name back
- NEVER say "what would you like to know about [dish]?" - just give the recipe!
- If they say "Give me the recipe for pasta" → Give the full pasta recipe immediately

When giving recipes:
- List ingredients with quantities
- Give clear, numbered steps
- End with something friendly

Remember: Your job is to provide recipes, not ask clarifying questions!"""

    if st.session_state.language_mode == "English":
        base += "\nSpeak ONLY in pure English. No Hindi words at all."
    else:
        base += "\nUse casual Hindi."

    if st.session_state.allergies:
        base += f"\nUser allergies: {st.session_state.allergies}. Avoid these completely!"

    low_items = [k for k, v in st.session_state.inventory.items() if v < 200]
    if low_items:
        base += f"\nUser has LOW stock of: {', '.join(low_items)}. Prefer recipes using little of these or suggest substitutes."

    if st.session_state.jain_mode:
        base += "\nUser follows JAIN diet. NEVER suggest: onion, garlic, ginger, potato, carrot, radish, beetroot, or any root vegetables. Use hing (asafoetida) for flavor instead."

    # ───── NEW: Prioritize expiring items ─────
    expiring_soon = []
    for item, days in st.session_state.inventory_expiry.items():
        if isinstance(days, (int, float)) and 0 < days <= 3:
            expiring_soon.append(f"{item} ({days} days left)")
    
    if expiring_soon:
        base += f"\nUser has items expiring very soon: {', '.join(expiring_soon)}. ALWAYS prioritize using these items first in recipes! Suggest them prominently and use substitutes only if absolutely necessary."

    return base

def get_nutrition_prompt(servings):
    return f"""You are a nutrition calculator. For the given recipe, estimate nutritional values **strictly PER {servings} SERVING(S)**.
Return format:
Calories: X kcal
Protein: X g
Carbs: X g
Fat: X g
Fiber: X g

Be realistic using standard Indian/home-cooked food values. Do NOT give total for whole recipe — only per serving."""

# ================= MAIN APP =================

# ================= MAIN APP CSS =================


# ────── EXPIRATION WARNING BANNER ──────
expiring_items = []
expired_items = []

for item, days in st.session_state.inventory_expiry.items():
    if isinstance(days, (int, float)):
        if days <= 0:
            expired_items.append(f"{item} (expired {abs(days)} days ago)")
        elif days <= 3:
            expiring_items.append(f"{item} ({days} days left)")

if expired_items or expiring_items:
    if expired_items:
        banner_text = f"⚠️ Expired items: {', '.join(expired_items)}"
        banner_color = "#ffcccc"  # light red
    else:
        banner_text = f"⏰ Expiring soon: {', '.join(expiring_items)}"
        banner_color = "#fff3cd"  # light orange-yellow
    
    st.markdown(f"""
        <div style="
            background-color: {banner_color};
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            text-align: center;
            font-weight: bold;
            color: #333;
        ">
            {banner_text} — Use them soon or remove from inventory!
        </div>
    """, unsafe_allow_html=True)
# Force custom PWA manifest to override Streamlit's default
st.markdown("""
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#FF6B6B">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="KitchenMate">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
""", unsafe_allow_html=True)

# ═══ ADD HEADER FUNCTION HERE ═══
def render_header():
    """Renders the app header with branding"""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #FF7518 0%, #FF9A3C 60%, #FFB870 100%);
        padding: 20px 28px 22px 28px;
        border-radius: 0 0 22px 22px;
        box-shadow: 0 6px 32px rgba(255,117,24,0.28);
        margin: -1rem -1rem 1.5rem -1rem;
        position: relative;
        overflow: hidden;
    ">
        <!-- decorative grain -->
        <div style="position:absolute;inset:0;background:url('data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/></filter><rect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\' opacity=\'0.04\'/></svg>');opacity:0.4;pointer-events:none;"></div>
        <div style="position:relative;text-align:center;">
            <div style="font-size:2.2rem;margin-bottom:2px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.15));">🍳</div>
            <h1 style="
                color: white;
                font-family: 'Syne', sans-serif;
                font-size: clamp(1.6rem, 5vw, 2.2rem);
                font-weight: 800;
                margin: 0;
                letter-spacing: -0.03em;
                text-shadow: 0 2px 8px rgba(0,0,0,0.15);
            ">KitchenMate</h1>
            <p style="
                color: rgba(255,255,255,0.88);
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 0.9rem;
                font-weight: 400;
                margin: 5px 0 0 0;
                letter-spacing: 0.02em;
            ">Your AI-powered cooking companion</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
# ================= COMPLETE SIDEBAR SECTION =================

# ── Theme toggle removed: CSS is fixed dark-orange theme; no dynamic theming needed ──

with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 12px 0;border-bottom:1px solid rgba(255,117,24,0.2);margin-bottom:12px;">
        <span style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;color:#FF7518;">🍳 KitchenMate</span>
        <span style="font-size:0.75rem;color:rgba(255,255,255,0.4);margin-left:6px;">Settings</span>
    </div>
    """, unsafe_allow_html=True)

    # ──── USER INFO ────
    if st.session_state.get("user_email") and not str(st.session_state.user_email).startswith("guest"):
        st.write("👤 Logged in as:")
        st.caption(st.session_state.user_email)
    else:
        st.info("🚶 Guest Mode")

    st.markdown("---")

    # ──── FIREBASE STATUS ────
    with st.expander("🔧 Firebase Status", expanded=False):
        try:
            db.collection("_health_check").document("test").get()
            st.success("✅ Connected")
        except Exception as e:
            st.error("❌ Not Connected")
            st.write(str(e))

    st.markdown("---")

    # ──── SECTION: DIETARY ────
    with st.expander("🥗 Dietary Preferences", expanded=False):
        new_jain_mode = st.toggle("🌿 Jain Mode (No root vegetables)", value=st.session_state.jain_mode)
        if new_jain_mode != st.session_state.jain_mode:
            st.session_state.jain_mode = new_jain_mode
            st.rerun()

        pure_veg = st.toggle("🌱 Pure Veg Mode", value=st.session_state.pure_veg_mode)
        if pure_veg != st.session_state.pure_veg_mode:
            st.session_state.pure_veg_mode = pure_veg
            st.rerun()

        health = st.toggle("💪 Health Mode (Low oil, sugar)", value=st.session_state.health_mode)
        if health != st.session_state.health_mode:
            st.session_state.health_mode = health
            st.rerun()

        st.session_state.allergies = st.text_input(
            "🚫 Allergies",
            value=st.session_state.allergies,
            placeholder="e.g., peanuts, dairy, shellfish",
            help="I'll avoid these in all recipe suggestions!"
        )

    # ──── SECTION: UNITS & SERVINGS ────
    with st.expander("📏 Units & Servings", expanded=False):
        st.session_state.servings = st.number_input(
            "🍽️ Number of servings",
            min_value=1, max_value=20,
            value=st.session_state.servings,
            step=1,
        )
        unit_choice = st.radio(
            "Preferred unit system",
            ["Metric (kg, g, ml)", "American (lbs, oz, cups)"],
            index=0 if st.session_state.unit_system == "metric" else 1
        )
        new_system = "metric" if "Metric" in unit_choice else "imperial"
        if new_system != st.session_state.unit_system:
            st.session_state.unit_system = new_system
            st.rerun()

    # ──── SECTION: LANGUAGE ────
    with st.expander("🗣️ Language", expanded=False):
        st.session_state.language_mode = st.radio(
            "Response Language",
            ["Hinglish", "English"],
            help="Choose how I should talk to you"
        )

    # ──── SECTION: INVENTORY ────
    with st.expander("📦 Inventory Management", expanded=False):
        with st.form("add_ingredient_form"):
            new_item = st.text_input("Ingredient Name", placeholder="e.g., basmati rice")
            col1, col2 = st.columns(2)
            with col1:
                new_qty = st.number_input("Quantity", min_value=0, step=50, value=500)
            with col2:
                unit_type = st.selectbox("Unit", ["g", "ml", "pcs"])
            new_price = st.number_input("Price per 100g/piece (₹)", min_value=0.0, step=1.0, value=0.0)
            submitted = st.form_submit_button("Add to Inventory", use_container_width=True)
            if submitted and new_item:
                key = new_item.lower().strip()
                st.session_state.inventory[key] = new_qty
                if new_price > 0:
                    st.session_state.inventory_prices[key] = new_price
                st.success(f"✅ Added {new_item} ({new_qty}{unit_type})")
                st.rerun()

        if st.session_state.inventory:
            st.markdown("<hr style='border-color:rgba(255,117,24,0.15);margin:12px 0 8px 0;'>", unsafe_allow_html=True)
            st.markdown("<p style='color:rgba(238,240,248,0.5);font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;'>🗑️ Remove Ingredient</p>", unsafe_allow_html=True)
            remove_item = st.selectbox(
                "Select item to remove",
                [""] + sorted(list(st.session_state.inventory.keys())),
                label_visibility="collapsed",
                key="sidebar_remove_item"
            )
            if remove_item and st.button("Remove", use_container_width=True, key="sidebar_remove_btn"):
                del st.session_state.inventory[remove_item]
                st.session_state.inventory_prices.pop(remove_item, None)
                st.session_state.inventory_expiry.pop(remove_item, None)
                st.success(f"🗑️ Removed {remove_item}")
                st.rerun()

    # ──── SECTION: ROUTINE GROCERY ────
    with st.expander("🛍️ Routine Weekly Grocery", expanded=False):
        if "routine_grocery_items" not in st.session_state:
            st.session_state.routine_grocery_items = [
                "rice", "flour", "oil", "milk", "eggs",
                "vegetables", "spices", "fruits", "dal", "sugar"
            ]

        st.write("**Current routine items:**")
        items_to_remove = []
        for item in st.session_state.routine_grocery_items:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {item.capitalize()}")
            with col2:
                if st.button("❌", key=f"remove_routine_{item}"):
                    items_to_remove.append(item)
        for item in items_to_remove:
            st.session_state.routine_grocery_items.remove(item)
            st.rerun()

        new_routine = st.text_input("Add new routine item", placeholder="e.g., bread")
        if st.button("Add") and new_routine:
            if new_routine.lower() not in st.session_state.routine_grocery_items:
                st.session_state.routine_grocery_items.append(new_routine.lower())
                st.success(f"Added {new_routine}")
                st.rerun()

        if st.button("🛒 Add Routine to Grocery List", use_container_width=True):
            st.session_state.grocery_list.update(st.session_state.routine_grocery_items)
            st.success(f"✅ Added {len(st.session_state.routine_grocery_items)} items!")
            st.rerun()

    st.markdown("---")

    # ──── SIGN OUT ────
    if st.button("🚪 Sign Out", use_container_width=True, type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("👋 Signed out successfully!")
        time.sleep(1)
        st.rerun()

    st.markdown("---")
    st.caption("Made by Manas")

# Call header
render_header()
# ═══ END HEADER ═══

# ── Top action bar ──
col_fresh, col_count = st.columns([3, 1])
with col_fresh:
    if st.button("✦ Start Fresh Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()
with col_count:
    msg_count = len(st.session_state.get("messages", []))
    if msg_count > 0:
        st.markdown(f"<div style='text-align:right;padding-top:8px;color:rgba(255,117,24,0.7);font-size:0.82rem;font-weight:600;'>{msg_count} msgs</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab_scanner, tab_diet = st.tabs([
    "💬 Chat", "📅 Meal Planner", "🛒 Grocery & Inventory",
    "🍲 Custom Recipes", "🔥 Tried Recipes", "❤️ Favourite Recipes",
    "📸 Scanner", "🥗 Diet Charts"
])

# ────────────── CHAT TAB ──────────────
with tab1:

    # Show chat history
    for msg_idx, msg in enumerate(st.session_state.messages):
        display_message(msg["role"], msg["content"], msg_index=msg_idx)

    # ── Chat input (fixed at bottom via master CSS) ──
    chat_input_prompt = st.chat_input(
        placeholder="✨ Ask me anything — recipes, tips, substitutes...",
        key="main_chat_input"
    )

    prompt = chat_input_prompt if chat_input_prompt else None

    # File uploader (separate, above chat)
    uploaded_file = st.sidebar.file_uploader(
        label="📎 Attach a file",
        type=["jpg", "jpeg", "png", "pdf", "txt"],
        accept_multiple_files=False,
        key="pinned_file_uploader",
    )

    # ═══════════════════════════════════════════════════════════════
    # FILE UPLOAD HANDLING
    # ═══════════════════════════════════════════════════════════════

    if uploaded_file is not None:
        st.session_state.messages.append({
            "role": "user",
            "content": f"Uploaded: **{uploaded_file.name}**"
        })

        with st.chat_message("user"):
            st.markdown(f"Uploaded: **{uploaded_file.name}**")
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, use_container_width=True)
            else:
                st.write("PDF uploaded")

        with st.chat_message("assistant"):
            with st.spinner("Analyzing file... 📊"):
                chart_text = ""

                # Extract text from file
                if uploaded_file.type == "application/pdf":
                    try:
                        pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
                        for page in pdf_reader.pages:
                            chart_text += page.extract_text() + "\n"
                    except Exception as e:
                        chart_text = f"Error reading PDF: {str(e)}"
                else:
                    chart_text = "Image uploaded - text extraction pending OCR implementation"

                # Decide if it's a diet chart or receipt based on filename
                is_receipt = any(word in uploaded_file.name.lower() for word in ["receipt", "bill", "grocery", "kiranastore"])

                if is_receipt:
                    analysis_prompt = f"""
                    You are a smart grocery receipt scanner.
                    Extract ALL food items, quantities and prices from this receipt text:
                    {chart_text[:4000]}

                    Output format (only this, no extra text):
                    Item name | Quantity | Unit | Price (₹)
                    Paneer | 500 | g | 180
                    Tomatoes | 2 | kg | 80
                    ...

                    Skip non-food items (soap, bags, etc.).
                    Use standard units (g, kg, ml, L, pcs).
                    """
                else:
                    analysis_prompt = f"""
                    You are a nutrition & fitness expert. Analyze this gym diet chart text:
                    {chart_text[:4000]}

                    Extract and summarize in this structured format:
                    Daily Calories: X kcal
                    Protein target: X g
                    Carbs: X g / Low/Medium/High
                    Fats: X g
                    Meals per day: X
                    Key rules / foods to avoid: ...
                    Special notes / restrictions: ...

                    Return ONLY the structured summary - no extra text.
                    """

                try:
                    response = client.chat.completions.create(
                        messages=[{"role": "user", "content": analysis_prompt}],
                        model="llama-3.3-70b-versatile",
                        temperature=0.4,
                        max_tokens=500
                    )
                    summary = response.choices[0].message.content.strip()

                    # Editable summary
                    st.markdown("**AI Analysis (edit if needed):**")
                    edited_summary = st.text_area(
                        label="",
                        value=summary,
                        height=180,
                        key=f"edit_{uploaded_file.name}_{int(time.time())}"  # unique key
                    )

                    col1, col2 = st.columns(2)

                    if col1.button("💾 Save / Add to Inventory"):
                        if is_receipt:
                            add_items_from_receipt(edited_summary)
                        else:
                            st.session_state.gym_diet_chart = edited_summary
                            if not st.session_state.user_email.startswith("guest"):
                                db.collection("users").document(st.session_state.user_id).set({
                                    "gym_diet_chart": edited_summary,
                                    "chart_updated": datetime.now().isoformat()
                                }, merge=True)
                            st.success("Saved!")

                    if col2.button("📅 Generate Weekly Plan" if not is_receipt else "➕ Add Missing Items"):
                        if is_receipt:
                            add_missing_items_from_receipt(edited_summary)
                        else:
                            generate_weekly_plan_from_chart(edited_summary)

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.info("Try uploading again or paste text manually.")

        # ────────────── YOUTUBE VIDEO PROCESSING ──────────────
    video_id = detect_youtube_url(prompt) if prompt else None

    if video_id:
            st.session_state.processing_video = True

            with st.chat_message("user"):
                st.markdown(f"🎥 YouTube Video Link")

            with st.chat_message("assistant"):
                with st.spinner("📹 Analyzing video..."):

                    # Step 1: Get video description using YouTube API
                    video_data, error = get_video_description(video_id)

                    if error:
                        st.error(f"❌ {error}")
                        if "API key" in error:
                            st.info("""
                            **How to add YouTube API key:**
                            1. Get key from: https://console.cloud.google.com
                            2. Find this line in code: `YOUTUBE_API_KEY = ""`
                            3. Replace with: `YOUTUBE_API_KEY = "YOUR_KEY_HERE"`
                            """)
                        st.session_state.processing_video = False
                        st.stop()

                    video_title = video_data['title']
                    description = video_data['description']

                    st.markdown(f"**Video:** {video_title}")

                    # Step 2: Check if description has ingredients
                    if len(description) > 100:
                        st.info("📝 Found detailed description!")

                        # Step 3: Extract recipe links from description
                        recipe_links = extract_recipe_links(description)

                        scraped_content = ""
                        if recipe_links:
                            st.info(f"🔗 Found recipe link: {recipe_links[0][:50]}...")
                            with st.spinner("🌐 Fetching recipe from link..."):
                                scraped_content = scrape_recipe_from_url(recipe_links[0])
                                if scraped_content:
                                    st.success("✅ Recipe page loaded!")

                        # Step 4: Parse recipe from description + scraped content
                        with st.spinner("🤖 Extracting exact ingredients..."):
                            recipe = parse_recipe_from_description(description, scraped_content, video_title)
                            st.markdown(recipe)

                            st.session_state.last_recipe = recipe
                            st.session_state.video_recipe = recipe
                            st.session_state.messages.append({"role": "user", "content": f"YouTube: {video_title}"})
                            st.session_state.messages.append({"role": "assistant", "content": recipe})



                    else:
                        # Fallback to transcript if description is too short
                        st.info("📝 Description is short, trying transcript...")
                        transcript = extract_youtube_transcript(video_id)

                        if transcript:
                            st.success("✅ Transcript extracted!")
                            with st.spinner("🤖 Converting transcript to recipe..."):
                                recipe = parse_recipe_from_transcript(transcript, video_title)
                                st.markdown(recipe)

                                st.session_state.last_recipe = recipe
                                st.session_state.video_recipe = recipe
                                st.session_state.messages.append({"role": "user", "content": f"YouTube: {video_title}"})
                                st.session_state.messages.append({"role": "assistant", "content": recipe})


                        else:
                            st.warning("⚠️ No transcript or description available.")
                            st.info("💡 Try asking me to suggest a similar recipe instead!")

            st.session_state.processing_video = False
            st.rerun()

    if prompt:
            st.session_state.show_cooking_check = False
            st.session_state.show_nutrition = False
            st.session_state.show_substitutes = False
            st.session_state.ingredients_shown = False

            # Smart prompt enhancement for short commands
            # If user just says a dish name (1-3 words, no question words), make it a recipe request
            prompt_lower = prompt.lower().strip()
            question_words = ['how', 'what', 'why', 'when', 'where', 'can', 'should', 'make', 'cook', 'prepare', 'recipe', 'give', 'tell', 'show']
            word_count = len(prompt_lower.split())

            # If it's a short phrase (1-3 words) without question words, assume they want a recipe
            if word_count <= 3 and not any(qword in prompt_lower for qword in question_words):
                enhanced_prompt = f"Give me the complete recipe for {prompt} with all ingredients and step-by-step instructions."
                st.info(f"💡 Understood: You want a recipe for **{prompt}**")
            else:
                enhanced_prompt = prompt

            allergy_note = f"User allergies: {st.session_state.allergies}. Avoid these!" if st.session_state.allergies else ""
            full_prompt = enhanced_prompt + " " + allergy_note
            if st.session_state.servings > 1:
                full_prompt += f" (for {st.session_state.servings} people)"

            st.session_state.messages.append({"role": "user", "content": full_prompt})
            with st.chat_message("user"):
                st.markdown(enhanced_prompt)  # Show enhanced version, not original
            with st.chat_message("assistant"):
                with st.spinner(random.choice([
        "Simmering your recipe… 🍲",
        "Chopping ingredients… 🔪",
        "Mixing flavors… 🥄",
        "Heating the pan… 🍳",
        "Tasting for perfection… 👨‍🍳"
    ])):
        # your streaming code here
                    try:
                        stream = client.chat.completions.create(
                            messages=[{"role": "system", "content": get_system_prompt()}, *st.session_state.messages],
                            model="llama-3.3-70b-versatile",
                            temperature=0.75,
                            max_tokens=700,
                            stream=True
                        )
                        response = ""
                        placeholder = st.empty()
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                response += chunk.choices[0].delta.content
                                placeholder.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.session_state.last_recipe = response


                    except Exception as e:
                        st.error(f"Error: {str(e)}")


    if st.button("😴  Feeling Lazy? Suggest from Inventory", type="primary", use_container_width=True):
        inventory_str = ", ".join(st.session_state.inventory.keys())
        lazy_prompt = f"Suggest a simple recipe using only these ingredients: {inventory_str}. Keep it easy and quick."

        st.session_state.messages.append({"role": "user", "content": lazy_prompt})

        with st.chat_message("user"):
            st.markdown(lazy_prompt)

        with st.chat_message("assistant"):
            with st.spinner(random.choice([
                "Simmering your recipe… 🍲",
                "Chopping ingredients… 🔪",
                "Mixing flavors… 🥄",
                "Heating the pan… 🍳",
                "Tasting for perfection… 👨‍🍳"
            ])):
                try:
                    stream = client.chat.completions.create(
                        messages=[{"role": "system", "content": get_system_prompt()}, *st.session_state.messages],
                        model="llama-3.3-70b-versatile",
                        temperature=0.75,
                        max_tokens=700,
                        stream=True
                    )

                    response = ""
                    placeholder = st.empty()

                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            response += chunk.choices[0].delta.content
                            placeholder.markdown(response)

                    # Save the final response
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.last_recipe = response



                except Exception as e:
                    st.error(f"Error: {str(e)}")

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        col1, col2, col3, col4 = st.columns([2,2,2,2])
        with col1:
            if st.button("🍳 Start Cooking"):
                # Auto-extract ingredients from recipe
                auto_ingredients = auto_extract_ingredients_from_recipe(st.session_state.last_recipe)

                if not auto_ingredients:
                    st.error("❌ Could not detect ingredients. Try rephrasing the recipe.")
                else:
                    # Check which are missing from inventory
                    missing_items = []
                    for item in auto_ingredients:
                        found = False
                        for inv_key in st.session_state.inventory:
                            if inv_key in item or item in inv_key:
                                found = True
                                break
                        if not found:
                            missing_items.append(item)

                    # Store for later use
                    st.session_state.detected_ingredients = auto_ingredients
                    st.session_state.missing_ingredients = missing_items
                    st.session_state.show_cooking_check = True
                    st.session_state.show_nutrition = False
                    st.session_state.show_substitutes = False
                    st.rerun()

        with col2:
            if st.button("🥗 Calculate Nutrition"):
                st.session_state.show_nutrition = True
                st.session_state.show_cooking_check = False
                st.session_state.show_substitutes = False
                st.rerun()

        with col3:
            if st.button("❤️ Favourite"):
                recipe_name = f"Recipe {len(st.session_state.favourite_recipes) + 1}"
                st.session_state.favourite_recipes[recipe_name] = st.session_state.last_recipe
                st.success(f"Added to Favourites: {recipe_name}")

        with col4:
            if st.button("🔄 Substitutes"):
                st.session_state.show_substitutes = True
                st.session_state.show_cooking_check = False
                st.session_state.show_nutrition = False
                st.rerun()

        # ═══ RECIPE FORMATTER (keep this as-is) ═══
        if st.session_state.last_recipe:
            st.markdown("---")
            format_recipe(st.session_state.last_recipe)

    if st.session_state.show_cooking_check and not st.session_state.cooking_mode:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(255,107,53,0.12) 0%, rgba(255,140,66,0.06) 100%);
            border: 1px solid rgba(255,107,53,0.3);
            border-radius: 16px;
            padding: 20px 24px;
            margin: 16px 0;
        ">
            <h3 style="color:#FF6B35; margin:0 0 4px 0; font-size:1.2rem;">🧾 Ingredient Check</h3>
            <p style="color:rgba(255,255,255,0.5); margin:0; font-size:0.85rem;">Review what you have and what you need</p>
        </div>
        """, unsafe_allow_html=True)

        detected_ingredients = st.session_state.get('detected_ingredients', [])
        missing = st.session_state.get('missing_ingredients', [])

        if not detected_ingredients:
            st.error("❌ No ingredients detected. Please try again.")
            if st.button("Close"):
                st.session_state.show_cooking_check = False
                st.rerun()
        else:
            # Jain mode warning
            if st.session_state.jain_mode:
                non_jain = [item for item in detected_ingredients if not is_jain_compatible(item)]
                if non_jain:
                    st.warning(f"⚠️ **Jain Alert:** This recipe contains: {', '.join(non_jain)}")
                    for item in non_jain:
                        substitute = get_jain_substitute(item)
                        st.write(f"• {item.capitalize()} → {substitute}")

            # Two columns: have / missing
            have = [i for i in detected_ingredients if i not in missing]

            col_have, col_miss = st.columns(2)

            with col_have:
                st.markdown(f"<p style='color:#4CAF50; font-weight:600; margin-bottom:8px;'>✅ You Have ({len(have)})</p>", unsafe_allow_html=True)
                for item in have:
                    for inv_key in st.session_state.inventory:
                        if inv_key in item or item in inv_key:
                            qty = st.session_state.inventory[inv_key]
                            status, color = get_quantity_status(qty)
                            st.markdown(f"<div style='background:rgba(76,175,80,0.08); border:1px solid rgba(76,175,80,0.2); border-radius:8px; padding:6px 12px; margin:4px 0; font-size:0.9rem;'>🟢 <b>{item.capitalize()}</b> <span style='color:{color}; font-size:0.8rem;'>[{status}]</span></div>", unsafe_allow_html=True)
                            break

            with col_miss:
                st.markdown(f"<p style='color:#FF6B35; font-weight:600; margin-bottom:8px;'>❌ Missing ({len(missing)})</p>", unsafe_allow_html=True)
                
                # Checkboxes to select which missing items to add to inventory
                items_to_add = []
                for item in missing:
                    st.markdown(f"<div style='background:rgba(255,107,53,0.08); border:1px solid rgba(255,107,53,0.2); border-radius:8px; padding:6px 12px; margin:4px 0; font-size:0.9rem;'>🔴 <b>{item.capitalize()}</b></div>", unsafe_allow_html=True)

            st.markdown("---")

            # Missing ingredient actions
            if missing:
                st.markdown("<p style='color:rgba(255,255,255,0.7); font-size:0.9rem; margin-bottom:12px;'>What do you want to do with the missing ingredients?</p>", unsafe_allow_html=True)
                
                # Let user pick quantities and add to inventory
                with st.expander("➕ Add missing items to Inventory", expanded=True):
                    st.markdown("<p style='color:rgba(255,255,255,0.6); font-size:0.85rem;'>Set quantities and add directly to your inventory:</p>", unsafe_allow_html=True)
                    quantities = {}
                    cols = st.columns(2)
                    for i, item in enumerate(missing):
                        with cols[i % 2]:
                            qty = st.number_input(
                                f"{item.capitalize()}",
                                min_value=0,
                                max_value=5000,
                                value=100,
                                step=50,
                                key=f"add_inv_qty_{item}"
                            )
                            quantities[item] = qty

                    if st.button("💾 Add All to Inventory", type="primary", use_container_width=True):
                        added = 0
                        for item, qty in quantities.items():
                            if qty > 0:
                                st.session_state.inventory[item.lower()] = qty
                                added += 1
                        if added:
                            # Save to Firebase
                            if not st.session_state.user_email.startswith("guest"):
                                try:
                                    db.collection("users").document(st.session_state.user_id).set(
                                        {"inventory": st.session_state.inventory}, merge=True
                                    )
                                except:
                                    pass
                            st.success(f"✅ Added {added} items to inventory!")
                            # Recheck missing
                            st.session_state.missing_ingredients = [
                                i for i in missing if i not in st.session_state.inventory
                            ]
                            st.rerun()

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.show_cooking_check = False
                        st.rerun()
                with col2:
                    if st.button("🛒 Add to Grocery List", use_container_width=True):
                        for item in missing:
                            st.session_state.grocery_list.add(item.lower())
                        st.success(f"✅ Added {len(missing)} items to grocery list!")
                        st.session_state.show_cooking_check = False
                        st.rerun()
                with col3:
                    if st.button("🍳 Cook Anyway", use_container_width=True):
                        st.session_state.cooking_steps = extract_steps(st.session_state.last_recipe)
                        if st.session_state.cooking_steps:
                            st.session_state.cooking_mode = True
                            st.session_state.current_step = 0
                            st.session_state.show_cooking_check = False
                            st.rerun()
                        else:
                            st.error("Could not extract cooking steps from recipe")
            else:
                st.success("✅ All ingredients available! Ready to cook?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.show_cooking_check = False
                        st.rerun()
                with col2:
                    if st.button("👨‍🍳 Start Cooking", type="primary", use_container_width=True):
                        st.session_state.cooking_steps = extract_steps(st.session_state.last_recipe)
                        if st.session_state.cooking_steps:
                            st.session_state.cooking_mode = True
                            st.session_state.current_step = 0
                            st.session_state.show_cooking_check = False
                            st.rerun()
                        else:
                            st.error("Could not extract steps from recipe")

    if st.session_state.show_nutrition and not st.session_state.cooking_mode:
            st.markdown("---")
            st.subheader(f"🥗 Nutrition per {st.session_state.servings} serving(s)")
            with st.spinner("Calculating nutrition..."):
                try:
                    stream = client.chat.completions.create(
                        messages=[{"role": "system", "content": get_nutrition_prompt(st.session_state.servings)},
                                  {"role": "user", "content": st.session_state.last_recipe}],
                        model="llama-3.3-70b-versatile",
                        temperature=0.5,
                        max_tokens=500,
                        stream=True
                    )
                    response = ""
                    placeholder = st.empty()
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            response += chunk.choices[0].delta.content
                            placeholder.markdown(response)


                except Exception as e:
                    st.error(f"Error: {str(e)}")
            if st.button("Close Nutrition"):
                st.session_state.show_nutrition = False
                st.rerun()

    if st.session_state.show_substitutes and not st.session_state.cooking_mode:
            st.markdown("---")
            st.subheader("🔄 Ingredient Substitutes")
            ingredients = extract_ingredients(st.session_state.last_recipe)
            missing = [ing['name'] for ing in ingredients if not any(k in ing['name'] or ing['name'] in k for k in st.session_state.inventory)]
            if missing:
                st.markdown(f"**Finding alternatives for:** {', '.join(missing)}")
                with st.spinner("Looking for Indian alternatives..."):
                    try:
                        sub_prompt = f"Practical Indian substitutes for: {', '.join(missing)}. One or two options each."
                        stream = client.chat.completions.create(
                            messages=[{"role": "user", "content": sub_prompt}],
                            model="llama-3.3-70b-versatile",
                            temperature=0.6,
                            max_tokens=400,
                            stream=True
                        )
                        resp = ""
                        placeholder = st.empty()
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                resp += chunk.choices[0].delta.content
                                placeholder.markdown(resp)


                    except Exception as e:
                        st.error(str(e))
            else:
                st.info("No missing ingredients!")
            if st.button("Close Substitutes"):
                st.session_state.show_substitutes = False
                st.rerun()

        # ────────────── COOKING MODE ──────────────
    if st.session_state.cooking_mode:
            st.markdown("---")
            st.subheader("👨‍🍳 Step-by-Step Cooking Guide")

            if st.session_state.cooking_steps:
                total_steps = len(st.session_state.cooking_steps)
                current = st.session_state.current_step

                st.markdown(f"### Step {current + 1} of {total_steps}")
                step_text = st.session_state.cooking_steps[current]
                st.markdown(f"**{step_text}**")



                # ───── TIMER FEATURE (client-side JS, no rerun loop) ─────
                time_pattern = r'(?:for|about|around|approximately)?\s*(\d+(?:\.\d+)?)\s*(minute|minutes|min|hour|hours|hr|second|seconds|sec|overnight)'
                match = re.search(time_pattern, step_text.lower())
                timer_key = f"timer_{current}"

                if match:
                    amount = float(match.group(1))
                    unit = match.group(2).lower()
                    if unit in ["minute", "minutes", "min"]:
                        seconds = int(amount * 60)
                    elif unit in ["hour", "hours", "hr"]:
                        seconds = int(amount * 3600)
                    elif unit in ["second", "seconds", "sec"]:
                        seconds = int(amount)
                    elif unit == "overnight":
                        seconds = 8 * 3600
                    else:
                        seconds = 0

                    if seconds > 0:
                        st.markdown(f"**⏱️ Suggested timer:** {amount} {unit}")
                        timer_html = f"""
                        <div id="timer_box_{current}" style="
                            background: rgba(255,117,24,0.1);
                            border: 1px solid rgba(255,117,24,0.35);
                            border-radius: 12px;
                            padding: 16px 20px;
                            text-align: center;
                            margin: 8px 0;
                        ">
                            <div id="timer_display_{current}" style="
                                font-family: monospace;
                                font-size: 2rem;
                                font-weight: 700;
                                color: #FF7518;
                                letter-spacing: 0.05em;
                            ">{int(seconds)//60:02d}:{int(seconds)%60:02d}</div>
                            <div style="margin-top:10px; display:flex; gap:8px; justify-content:center;">
                                <button onclick="startTimer_{current}()" style="background:#FF7518;color:white;border:none;border-radius:8px;padding:8px 18px;font-weight:600;cursor:pointer;font-size:0.9rem;">⏱️ Start</button>
                                <button onclick="pauseTimer_{current}()" style="background:rgba(255,255,255,0.1);color:#EEF0F8;border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:8px 18px;font-weight:600;cursor:pointer;font-size:0.9rem;">⏸️ Pause</button>
                                <button onclick="resetTimer_{current}()" style="background:rgba(255,255,255,0.1);color:#EEF0F8;border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:8px 18px;font-weight:600;cursor:pointer;font-size:0.9rem;">🔄 Reset</button>
                            </div>
                            <div id="timer_done_{current}" style="display:none;margin-top:10px;color:#3DD68C;font-weight:700;font-size:1.1rem;">🎉 Time's up!</div>
                        </div>
                        <script>
                        (function() {{
                            var total_{current} = {int(seconds)};
                            var remaining_{current} = total_{current};
                            var interval_{current} = null;
                            var running_{current} = false;
                            function pad(n) {{ return n < 10 ? '0' + n : n; }}
                            function updateDisplay_{current}() {{
                                var m = Math.floor(remaining_{current} / 60);
                                var s = remaining_{current} % 60;
                                var el = document.getElementById('timer_display_{current}');
                                if (el) el.innerText = pad(m) + ':' + pad(s);
                            }}
                            window.startTimer_{current} = function() {{
                                if (running_{current}) return;
                                running_{current} = true;
                                interval_{current} = setInterval(function() {{
                                    if (remaining_{current} > 0) {{
                                        remaining_{current}--;
                                        updateDisplay_{current}();
                                    }} else {{
                                        clearInterval(interval_{current});
                                        running_{current} = false;
                                        var done = document.getElementById('timer_done_{current}');
                                        if (done) done.style.display = 'block';
                                    }}
                                }}, 1000);
                            }};
                            window.pauseTimer_{current} = function() {{
                                if (!running_{current}) return;
                                clearInterval(interval_{current});
                                running_{current} = false;
                            }};
                            window.resetTimer_{current} = function() {{
                                clearInterval(interval_{current});
                                running_{current} = false;
                                remaining_{current} = total_{current};
                                updateDisplay_{current}();
                                var done = document.getElementById('timer_done_{current}');
                                if (done) done.style.display = 'none';
                            }};
                        }})();
                        </script>
                        """
                        import streamlit.components.v1 as components
                        components.html(timer_html, height=160)
                # ───── END TIMER ─────

                # ── Step navigation buttons — ALWAYS rendered, outside all timer conditionals ──
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("⬅️ Previous" if current > 0 else "⬅️ First", key=f"prev_{current}"):
                        if current > 0:
                            st.session_state.current_step -= 1
                            st.rerun()
                with col2:
                    if st.button("🔄 Repeat", key=f"repeat_{current}"):
                        st.info(f"🔄 Repeating: {step_text}")
                with col3:
                    if st.button("➡️ Next" if current < total_steps - 1 else "✅ Done!", key=f"next_{current}"):
                        if current < total_steps - 1:
                            st.session_state.current_step += 1
                            st.rerun()
                        else:
                            st.session_state.cooking_mode = False
                            st.session_state.current_step = 0
                            st.session_state.cooking_steps = []
                            st.rerun()
                with col4:
                    if st.button("⛔ Exit Cooking", key=f"exit_{current}"):
                        st.session_state.cooking_mode = False
                        st.session_state.current_step = 0
                        st.session_state.cooking_steps = []
                        st.session_state.show_cooking_check = False
                        st.rerun()

# ────────────── MEAL PLANNER ──────────────
with tab2:
    st.subheader("📅 Meal Planner")
    tomorrow = datetime.now() + timedelta(days=1)
    selected_date = st.date_input("Plan for:", value=tomorrow)
    date_key = selected_date.strftime("%Y-%m-%d")
    meals = ["Breakfast", "Morning Snack", "Lunch", "Evening Snack", "Dinner"]
    planned = st.session_state.meal_plan.get(date_key, {})
    for meal in meals:
        with st.expander(f"🍽️ {meal}"):
            dish = st.text_input(f"What for {meal}?", value=planned.get(meal, ""), key=f"meal_{date_key}_{meal}")
            if dish and st.button(f"Save {meal}", key=f"save_{date_key}_{meal}"):
                if date_key not in st.session_state.meal_plan:
                    st.session_state.meal_plan[date_key] = {}
                st.session_state.meal_plan[date_key][meal] = dish
                st.success(f"{meal} saved: {dish}")
    if date_key in st.session_state.meal_plan:
        st.markdown("### Planned Meals")
        for m, d in st.session_state.meal_plan[date_key].items():
            st.write(f"**{m}**: {d}")

# ────────────── GROCERY & INVENTORY ──────────────
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🥫 Your Inventory")

        # Search / filter
        inv_search = st.text_input("🔍 Search inventory", placeholder="e.g., rice, milk", key="inv_search")

        filtered_inventory = {
            k: v for k, v in sorted(st.session_state.inventory.items())
            if inv_search.lower() in k.lower()
        } if inv_search else dict(sorted(st.session_state.inventory.items()))

        for item, qty in filtered_inventory.items():
            status, color = get_quantity_status(qty)
            price = st.session_state.inventory_prices.get(item, None)
            price_str = f"₹{price}/100g" if price else ""
            expiry_days = st.session_state.inventory_expiry.get(item, None)

            # Expiry color coding
            if expiry_days is not None:
                if expiry_days <= 0:
                    expiry_color = "#FF5757"
                    expiry_label = f"Expired ({abs(int(expiry_days))}d ago)"
                elif expiry_days <= 3:
                    expiry_color = "#FFB020"
                    expiry_label = f"⚠️ {int(expiry_days)}d left"
                else:
                    expiry_color = "#3DD68C"
                    expiry_label = f"✅ {int(expiry_days)}d left"
                expiry_badge = f"<span style='color:{expiry_color};font-size:0.78rem;margin-left:6px;'>{expiry_label}</span>"
            else:
                expiry_badge = ""

            st.markdown(f"""
            <div style="background:rgba(26,30,42,0.7);border:1px solid rgba(255,255,255,0.07);
                border-left:3px solid {color};border-radius:9px;padding:8px 12px;margin:4px 0;
                display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:500;font-size:0.9rem;">{item.capitalize()}</span>
                <span style="font-size:0.8rem;color:rgba(238,240,248,0.55);">
                    {qty}g &nbsp;
                    <span style="color:{color};">[{status}]</span>
                    &nbsp;{price_str}
                    {expiry_badge}
                </span>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.subheader("🛒 Grocery List")

        # Search grocery list
        grocery_search = st.text_input("🔍 Search grocery list", placeholder="e.g., onion", key="grocery_search")
        sorted_grocery = sorted(st.session_state.grocery_list)
        filtered_grocery = [i for i in sorted_grocery if grocery_search.lower() in i.lower()] if grocery_search else sorted_grocery

        if not st.session_state.grocery_list:
            st.info("List khali hai! 🛒")
        else:
            to_add = []
            for item in filtered_grocery:
                if st.checkbox(f"{item.capitalize()}", key=f"grocery_check_{item}"):
                    to_add.append(item)
            if to_add:
                for item in to_add:
                    st.session_state.inventory[item.lower()] = 500
                    st.session_state.grocery_list.remove(item)
                st.success(f"Added {len(to_add)} items to inventory!")
                st.rerun()

        # Confirmation dialog before clearing grocery list
        if st.session_state.grocery_list:
            if "confirm_clear_grocery" not in st.session_state:
                st.session_state.confirm_clear_grocery = False

            if not st.session_state.confirm_clear_grocery:
                if st.button("🗑️ Clear Grocery List", use_container_width=True):
                    st.session_state.confirm_clear_grocery = True
                    st.rerun()
            else:
                st.warning("⚠️ Are you sure you want to clear the entire grocery list?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Yes, clear it", type="primary", use_container_width=True):
                        st.session_state.grocery_list.clear()
                        st.session_state.confirm_clear_grocery = False
                        st.rerun()
                with c2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.confirm_clear_grocery = False
                        st.rerun()

    # ── Add item with expiry ──
    st.markdown("---")
    st.markdown("### ➕ Add Item to Inventory")
    with st.form("tab3_add_item_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            t3_item = st.text_input("Ingredient Name", placeholder="e.g., basmati rice")
        with col_b:
            t3_qty  = st.number_input("Quantity (g/ml)", min_value=0, step=50, value=500)
        t3_price        = st.number_input("Price per 100g (₹, optional)", min_value=0.0, step=1.0, value=0.0)
        t3_expiry_opt   = st.radio("Expiry", ["Estimate for me", "Set manually"], horizontal=True)
        t3_manual_days  = st.number_input("Days until expiry (used if 'Set manually')", min_value=1, step=1, value=7)
        t3_submit       = st.form_submit_button("💾 Add to Inventory", use_container_width=True)

    if t3_submit and t3_item:
        key = t3_item.lower().strip()
        st.session_state.inventory[key] = t3_qty
        if t3_price > 0:
            st.session_state.inventory_prices[key] = t3_price
        if t3_expiry_opt == "Estimate for me":
            days = get_expiry_estimate(key)
        else:
            days = t3_manual_days
        st.session_state.inventory_expiry[key] = days
        if not st.session_state.user_email.startswith("guest"):
            try:
                db.collection("users").document(st.session_state.user_id).set(
                    {"inventory": st.session_state.inventory,
                     "inventory_expiry": st.session_state.inventory_expiry}, merge=True)
            except Exception:
                pass
        st.success(f"✅ Added **{t3_item}** ({t3_qty}g) — expires in ~{days} days")
        st.rerun()
# ────────────── CUSTOM RECIPES ──────────────
with tab4:
    st.subheader("🍲 Custom Recipes")
    with st.expander("➕ Create New Custom Recipe"):
        name = st.text_input("Recipe Name")
        ingredients = st.text_area("Ingredients")
        steps = st.text_area("Steps")
       
        if st.button("Save Custom Recipe") and name and ingredients and steps:
            st.session_state.custom_recipes[name] = {"ingredients": ingredients, "steps": steps}
            st.success(f"Saved: {name}")
    if st.session_state.custom_recipes:
        st.markdown("### Your Custom Recipes")
        for name, data in st.session_state.custom_recipes.items():
            with st.expander(name):
                st.write("**Ingredients:**", data["ingredients"])
                st.write("**Steps:**", data["steps"])

# ────────────── TRIED RECIPES ──────────────
with tab5:
    st.subheader("🔥 Tried Recipes")
    if not st.session_state.tried_recipes:
        st.info("No recipes tried yet! Cook something to see here.")
    else:
        for idx, entry in enumerate(reversed(st.session_state.tried_recipes), 1):
            stars = "★" * entry["rating"] + "☆" * (5 - entry["rating"])
            with st.expander(f"Recipe {idx} – {entry['date']} – {stars}"):
                st.markdown(entry["recipe"])

# ────────────── FAVOURITE RECIPES ──────────────
with tab6:
    st.subheader("❤️ Favourite Recipes")
    if not st.session_state.favourite_recipes:
        st.info("No favourites yet! Heart a recipe to add.")
    else:
        for name, recipe in st.session_state.favourite_recipes.items():
            with st.expander(name):
                st.markdown(recipe)

# ────────────── RECEIPT SCANNER TAB ──────────────
with tab_scanner:
    # ── Mode switcher ──
    scan_mode = st.radio(
        "Scanner Mode",
        ["🧾 Receipt Scanner", "📸 Ingredient Scanner"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Shared session state keys
    if "detected_scanner_items" not in st.session_state:
        st.session_state.detected_scanner_items = []
    if "scanner_selected_items" not in st.session_state:
        st.session_state.scanner_selected_items = {}
    if "scanner_mode_last" not in st.session_state:
        st.session_state.scanner_mode_last = ""

    # Reset selections when switching mode
    if scan_mode != st.session_state.scanner_mode_last:
        st.session_state.detected_scanner_items = []
        st.session_state.scanner_selected_items = {}
        st.session_state.scanner_mode_last = scan_mode

    if scan_mode == "🧾 Receipt Scanner":
        st.subheader("🧾 Receipt Scanner")
        st.info("Upload receipt photo → AI extracts food items → Review & add to inventory")
        mode_key = "receipt"
        scan_btn_label = "🔍 Scan Receipt with AI"
    else:
        st.subheader("📸 Ingredient Scanner")
        st.info("Take photo of ingredients → AI identifies them → Review & add to inventory")
        mode_key = "ingredients"
        scan_btn_label = "🔍 Detect Ingredients with AI"

    col_cam, col_upload = st.columns(2)
    with col_cam:
        scan_camera = st.camera_input(f"Take photo", key=f"scanner_camera_{mode_key}")
    with col_upload:
        file_types = ["jpg", "jpeg", "png", "pdf"] if mode_key == "receipt" else ["jpg", "jpeg", "png"]
        scan_upload = st.file_uploader("Or upload photo", type=file_types, key=f"scanner_upload_{mode_key}")

    scan_img = scan_camera or scan_upload

    if scan_img is not None:
        st.image(scan_img, caption="Your photo", use_container_width=True)

        if st.button(scan_btn_label, key=f"scan_btn_{mode_key}"):
            with st.spinner("Analyzing image with AI..."):
                image_bytes = scan_img.getvalue()
                detected_items = detect_ingredients_from_image(image_bytes)
                if detected_items:
                    st.session_state.detected_scanner_items = detected_items
                    st.session_state.scanner_selected_items = {}
                    st.success(f"✅ Detected {len(detected_items)} items!")
                else:
                    st.session_state.detected_scanner_items = []
                    st.warning("⚠️ No items detected. Try a clearer photo.")

    # ── Review UI (persists across reruns via session state) ──
    if st.session_state.detected_scanner_items:
        st.markdown("### 📝 Review Detected Items")
        st.caption("Check items to add, uncheck to skip. Edit quantities as needed.")

        cols = st.columns(3)
        for i, item in enumerate(st.session_state.detected_scanner_items):
            with cols[i % 3]:
                item_name = item.lower().strip()
                selected = st.checkbox(
                    f"**{item.capitalize()}**",
                    value=(item_name in st.session_state.scanner_selected_items),
                    key=f"scan_check_{mode_key}_{item_name}"
                )
                qty = st.number_input(
                    "g / ml",
                    min_value=1,
                    value=st.session_state.scanner_selected_items.get(item_name, 500),
                    step=50,
                    key=f"scan_qty_{mode_key}_{item_name}",
                    label_visibility="collapsed"
                )
                if selected:
                    st.session_state.scanner_selected_items[item_name] = qty
                elif item_name in st.session_state.scanner_selected_items:
                    del st.session_state.scanner_selected_items[item_name]

        st.markdown("---")
        selected_count = len(st.session_state.scanner_selected_items)
        if selected_count > 0:
            st.caption(f"{selected_count} item(s) selected")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Add to Inventory", type="primary", use_container_width=True, key=f"add_{mode_key}_inv"):
                    for item, qty in st.session_state.scanner_selected_items.items():
                        st.session_state.inventory[item] = qty
                    if not st.session_state.user_email.startswith("guest"):
                        try:
                            db.collection("users").document(st.session_state.user_id).set(
                                {"inventory": st.session_state.inventory}, merge=True)
                        except Exception:
                            pass
                    added = len(st.session_state.scanner_selected_items)
                    st.session_state.scanner_selected_items = {}
                    st.session_state.detected_scanner_items = []
                    st.success(f"✨ Added {added} items to inventory!")
                    st.rerun()
            with col2:
                if st.button("🛒 Add to Grocery List", use_container_width=True, key=f"add_{mode_key}_grocery"):
                    for item in list(st.session_state.scanner_selected_items.keys()):
                        st.session_state.grocery_list.add(item)
                    added = len(st.session_state.scanner_selected_items)
                    st.session_state.scanner_selected_items = {}
                    st.session_state.detected_scanner_items = []
                    st.success(f"✨ Added {added} items to grocery list!")
                    st.rerun()
        else:
            st.info("☝️ Select at least one item above to add.")

# ────────────── DIET CHARTS TAB ──────────────
with tab_diet:
    st.subheader("🥗 Diet Charts")
    st.info("Create personalized diet plans and meal schedules")
    
    # Create new diet chart
    with st.expander("➕ Create New Diet Chart", expanded=False):
        chart_name = st.text_input("Diet Chart Name", placeholder="e.g., Weight Loss Plan, Muscle Gain, Keto Diet")
        
        col1, col2 = st.columns(2)
        with col1:
            diet_type = st.selectbox(
                "Diet Type",
                ["Custom", "Weight Loss", "Weight Gain", "Maintenance", "Keto", "Vegan", "High Protein", "Low Carb"]
            )
        with col2:
            duration = st.selectbox("Duration", ["1 Week", "2 Weeks", "1 Month", "3 Months", "Ongoing"])
        
        st.markdown("#### 🍽️ Meal Schedule")
        
        # Days of week
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        meals = ["Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack", "Dinner"]
        
        diet_schedule = {}
        
        day_tabs = st.tabs(days)
        for day_idx, day in enumerate(days):
            with day_tabs[day_idx]:
                diet_schedule[day] = {}
                for meal in meals:
                    diet_schedule[day][meal] = st.text_area(
                        f"{meal}",
                        placeholder=f"Enter {meal.lower()} items...",
                        height=80,
                        key=f"diet_{day}_{meal}"
                    )
        
        notes = st.text_area("Additional Notes", placeholder="Special instructions, supplements, etc.")
        
        if st.button("💾 Save Diet Chart", type="primary", use_container_width=True):
            if chart_name:
                st.session_state.diet_charts[chart_name] = {
                    "type": diet_type,
                    "duration": duration,
                    "schedule": diet_schedule,
                    "notes": notes,
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.success(f"✅ Saved: {chart_name}")
                st.rerun()
            else:
                st.error("Please enter a diet chart name!")
    
    # Display existing diet charts
    if st.session_state.diet_charts:
        st.markdown("---")
        st.markdown("### 📋 Your Diet Charts")
        
        for chart_name, chart_data in st.session_state.diet_charts.items():
            with st.expander(f"📊 {chart_name} ({chart_data['type']} - {chart_data['duration']})", expanded=False):
                st.caption(f"Created: {chart_data['created']}")
                
                # Edit mode toggle
                edit_mode = st.checkbox(f"✏️ Edit this chart", key=f"edit_{chart_name}")
                
                if edit_mode:
                    st.markdown("#### Edit Meal Schedule")
                    
                    updated_schedule = {}
                    day_tabs_edit = st.tabs(days)
                    
                    for day_idx, day in enumerate(days):
                        with day_tabs_edit[day_idx]:
                            updated_schedule[day] = {}
                            for meal in meals:
                                current_value = chart_data['schedule'].get(day, {}).get(meal, "")
                                updated_schedule[day][meal] = st.text_area(
                                    f"{meal}",
                                    value=current_value,
                                    height=80,
                                    key=f"edit_{chart_name}_{day}_{meal}"
                                )
                    
                    updated_notes = st.text_area(
                        "Notes",
                        value=chart_data.get('notes', ''),
                        key=f"edit_notes_{chart_name}"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Save Changes", key=f"save_{chart_name}", use_container_width=True):
                            st.session_state.diet_charts[chart_name]['schedule'] = updated_schedule
                            st.session_state.diet_charts[chart_name]['notes'] = updated_notes
                            st.success("✅ Changes saved!")
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️ Delete Chart", key=f"delete_{chart_name}", use_container_width=True):
                            del st.session_state.diet_charts[chart_name]
                            st.success("✅ Chart deleted!")
                            st.rerun()
                
                else:
                    # View mode
                    st.markdown("#### 📅 Weekly Schedule")
                    
                    view_day_tabs = st.tabs(days)
                    for day_idx, day in enumerate(days):
                        with view_day_tabs[day_idx]:
                            for meal in meals:
                                meal_content = chart_data['schedule'].get(day, {}).get(meal, "")
                                if meal_content:
                                    st.markdown(f"**{meal}:**")
                                    st.write(meal_content)
                                    st.markdown("---")
                    
                    if chart_data.get('notes'):
                        st.markdown("#### 📝 Notes")
                        st.info(chart_data['notes'])
    else:
        st.info("📝 No diet charts yet. Create your first one above!")

# ────────────────────────────────────────────────
#  AUTO-SAVE INVENTORY & RELATED DATA TO FIRESTORE
#  Debounced: only saves if ≥10 seconds since last save; skips guest users entirely.
# ────────────────────────────────────────────────

_is_authenticated = st.session_state.get("is_authenticated", False)
_user_id = st.session_state.get("user_id", "")
_user_email = st.session_state.get("user_email", "") or ""
_is_guest = _user_email.startswith("guest")

if _is_authenticated and _user_id and not _is_guest:
    _now = time.time()
    _last_save = st.session_state.get("_last_autosave", 0)
    # Only write to Firestore if at least 10 seconds have passed since the last save
    if (_now - _last_save) >= 10:
        try:
            user_data = {
                "inventory":         dict(st.session_state.inventory),
                "inventory_prices":  dict(st.session_state.inventory_prices),
                "inventory_expiry":  dict(st.session_state.inventory_expiry),
                "grocery_list":      list(st.session_state.grocery_list),
                "diet_charts":       dict(st.session_state.diet_charts),
                "last_updated":      datetime.now().isoformat()
            }
            db.collection("users").document(_user_id).set(user_data, merge=True)
            st.session_state._last_autosave = _now
        except Exception as e:
            print(f"Auto-save failed: {str(e)}")
# ── Floating PWA install button (small, bottom-right, appears only when eligible) ──
st.markdown("""
    <script>
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        // Small floating button — matches orange brand
        const btn = document.createElement('button');
        btn.innerHTML = '📲';
        btn.title = 'Install KitchenMate';
        btn.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 18px;
            z-index: 99999;
            width: 46px;
            height: 46px;
            background: #FF7518;
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 1.25rem;
            box-shadow: 0 4px 16px rgba(255,117,24,0.45);
            cursor: pointer;
            transition: transform 0.18s;
        `;
        btn.onmouseover = () => btn.style.transform = 'scale(1.12)';
        btn.onmouseout  = () => btn.style.transform = 'scale(1)';
        btn.onclick = () => {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choice) => {
                deferredPrompt = null;
                btn.remove();
            });
        };
        document.body.appendChild(btn);
    });
    </script>
""", unsafe_allow_html=True)

# ── Footer ──
st.markdown("""
<div style="text-align:center;padding:24px 0 8px 0;">
    <span style="color:rgba(255,117,24,0.5);font-size:0.78rem;font-weight:600;letter-spacing:0.06em;">KITCHENMATE BY INDIAN INSTINCT STUDIOS</span>
</div>
""", unsafe_allow_html=True)
