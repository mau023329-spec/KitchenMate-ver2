# pages/google-login.py
# This is a separate page that handles Google login redirect
# It will appear as a new tab/page in your app: /google-login

import streamlit as st

st.set_page_config(
    page_title="Google Login - KitchenMate",
    page_icon="🔑",
    layout="centered"
)

st.title("Signing you in with Google...")

st.info("Please wait while we complete the login...")

# Small spinner for better UX
with st.spinner("Connecting to Google..."):
    # In this simple version, we just show a message
    # Later we can add real token handling here
    st.markdown("""
        <script>
            // This page is loaded after Google redirect
            // You can add JS here to get the token or user info
            // For now, just redirect back to main app after 3 seconds
            setTimeout(() => {
                window.location.href = "/";
            }, 3000);
        </script>
    """, unsafe_allow_html=True)

    st.success("Login in progress... Redirecting back to main app!")
