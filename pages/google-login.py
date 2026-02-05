# pages/google-login.py
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import time

st.set_page_config(page_title="Login - KitchenMate", layout="centered")

st.title("🔐 Completing Google Login...")

with st.spinner("Verifying with Google..."):
    # Get authorization code from URL
    query_params = st.query_params
    auth_code = query_params.get("code")
    
    if not auth_code:
        st.error("❌ No authorization code received.")
        st.info("Please click the Google Sign-In button again.")
        if st.button("← Back to Login"):
            st.switch_page("streamlit_app.py")
        st.stop()
    
    # Create OAuth flow
    try:
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
            scopes=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
        )
        
        # Exchange authorization code for token
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # Get user info from Google
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        # Save to session state
        st.session_state.user_id = user_info["id"]
        st.session_state.user_email = user_info["email"]
        st.session_state.user_name = user_info.get("name", "User")
        st.session_state.is_authenticated = True
        st.session_state.show_onboarding = True
        
        st.success(f"✅ Welcome, {st.session_state.user_name}!")
        st.balloons()
        
        # Redirect to main app
        time.sleep(1)
        st.switch_page("streamlit_app.py")
        
    except Exception as e:
        st.error(f"❌ Login failed")
        
        with st.expander("Error Details (for debugging)"):
            st.code(str(e))
        
        st.warning("**Possible reasons:**")
        st.write("1. OAuth redirect URI mismatch in Google Cloud Console")
        st.write("2. You're not added as a test user in OAuth consent screen")
        st.write("3. Client ID/Secret incorrect in secrets")
        
        if st.button("← Try Again"):
            st.switch_page("streamlit_app.py")
