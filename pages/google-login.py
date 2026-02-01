# pages/google-login.py
# Real Google OAuth callback handler

import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import urllib.parse

st.set_page_config(page_title="Login - KitchenMate", layout="centered")
st.title("🔐 Completing Google Login...")

with st.spinner("Verifying with Google..."):
    # Get the full URL (including query params) that Google redirected to
    query_params = st.experimental_get_query_params()
    auth_code = query_params.get("code", [None])[0]

    if not auth_code:
        st.error("No authorization code received. Please try logging in again.")
        if st.button("← Back to Login"):
            st.experimental_set_query_params()
            st.rerun()
        st.stop()

    # Google OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["google_oauth"]["client_id"],
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]]
            }
        },
        scopes=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
    )

    try:
        # Exchange code for token
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials

        # Get user info from Google
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()

        # SUCCESS! Save to session
        st.session_state.user_id = user_info["id"]
        st.session_state.user_email = user_info["email"]
        st.session_state.user_name = user_info.get("name", "User")
        st.session_state.is_authenticated = True
        st.session_state.show_onboarding = True

        st.success(f"Welcome {st.session_state.user_name}!")
        st.balloons()
        
        # Clear query params and go back to main app
        st.experimental_set_query_params()
        st.rerun()

    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        if st.button("← Try Again"):
            st.experimental_set_query_params()
            st.rerun()
