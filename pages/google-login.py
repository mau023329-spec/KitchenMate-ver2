# pages/google-login.py
# Google OAuth callback handler
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

st.set_page_config(page_title="Login - KitchenMate", layout="centered")

st.title("🔐 Completing Google Login...")

with st.spinner("Verifying with Google..."):
    # Get authorization code from URL
    query_params = st.query_params  # Updated syntax (not experimental)
    auth_code = query_params.get("code", None)
    
    if not auth_code:
        st.error("❌ No authorization code received. Please try logging in again.")
        if st.button("← Back to Login"):
            st.switch_page("streamlit_app.py")  # Go back to main page
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
        st.info("Redirecting to app...")
        st.switch_page("streamlit_app.py")
        
    except Exception as e:
        st.error(f"❌ Login failed: {str(e)}")
        st.code(str(e), language="text")
        
        if st.button("← Try Again"):
            st.switch_page("streamlit_app.py")
