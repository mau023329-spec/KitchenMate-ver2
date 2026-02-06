# pages/google-login.py
# REAL Google OAuth callback handler - this page receives the code from Google

import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import time

st.set_page_config(page_title="Login - KitchenMate", layout="centered")
st.title("🔐 Finishing Google Login...")

with st.spinner("Verifying your Google account..."):
    # Get all query params Google sent us (NEW API)
    query_params = st.query_params
    auth_code = query_params.get("code", None)
    error = query_params.get("error", None)

    if error:
        st.error(f"Google login failed: {error}")
        if st.button("← Back to Login"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    if not auth_code:
        st.error("No authorization code received from Google. Please try again.")
        if st.button("← Try Login Again"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    # Set up the OAuth flow with your secrets
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
        # Exchange the code for access token + ID token
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials

        # Get basic user profile from Google
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()

        # Save everything we need to session state
        st.session_state.user_id = user_info["id"]
        st.session_state.user_email = user_info["email"]
        st.session_state.user_name = user_info.get("name", "User")
        st.session_state.user_picture = user_info.get("picture", None)  # optional profile pic
        st.session_state.is_authenticated = True
        st.session_state.show_onboarding = True  # go to onboarding if first time

        st.success(f"Welcome back, {st.session_state.user_name}! 🎉")
        st.balloons()

        # Wait 2 seconds so user sees success message
        time.sleep(2)

        # Clear URL params and go back to main app
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.error(f"Something went wrong during login: {str(e)}")
        st.write("Technical details (for debug):")
        st.code(str(e))
        if st.button("← Try Again"):
            st.query_params.clear()
            st.rerun()
