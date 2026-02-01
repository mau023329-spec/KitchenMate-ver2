# pages/callback.py
# This page handles the Google login redirect callback

import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import urllib.parse

# Google OAuth config from secrets
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]],
        }
    },
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
    redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
)

st.set_page_config(page_title="Login Callback", layout="centered")
st.title("Completing Google Login...")

with st.spinner("Verifying..."):
    authorization_response = st.experimental_get_query_params()["code"][0] if "code" in st.experimental_get_query_params() else None
    
    if authorization_response:
        # Exchange code for token
        flow.fetch_token(code=authorization_response)
        credentials = flow.credentials
        
        # Get user info
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        # Save to session
        st.session_state.user_id = user_info["id"]
        st.session_state.user_email = user_info["email"]
        st.session_state.is_authenticated = True
        st.session_state.show_onboarding = True
        
        st.success("Login successful! Redirecting to main app...")
        time.sleep(2)
        st.experimental_rerun()  # Redirect back to main page
    else:
        st.error("No authorization code found. Please try logging in again.")
