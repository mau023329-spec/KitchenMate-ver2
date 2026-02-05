import PyPDF2  # for PDF text extraction
from io import BytesIO
import streamlit as st
from groq import Groq
import re
from datetime import datetime, timedelta
import speech_recognition as sr
from gtts import gTTS
import io
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import requests
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import threading
import time
import queue
import base64
from openai import OpenAI
import random
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from google_auth_oauthlib.flow import Flow

# ================= FIREBASE INITIALIZATION (safe for Streamlit reruns) =================

APP_NAME = "kitchenmate-default"

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

# ================= AUTHENTICATION FUNCTIONS =================

def show_login():
    """Display login page with Google OAuth and Guest mode"""
    st.title("🍳 Welcome to KitchenMate")
    st.markdown("### Your AI-Powered Cooking Assistant")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sign in with Google")
        
        # Create Google OAuth URL
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
            scopes=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email"
            ],
            redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
        )
        
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true"
        )
        
        # Google Sign-In Button
        st.markdown(f"""
            <a href="{authorization_url}" target="_self" style="text-decoration:none;">
                <button style="
                    background: #4285F4; 
                    color: white; 
                    padding: 12px 24px; 
                    border: none; 
                    border-radius: 4px; 
                    font-size: 16px; 
                    cursor: pointer; 
                    width: 100%; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    gap: 8px;
                    font-weight: 500;
                ">
                    <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="18">
                    Sign in with Google
                </button>
            </a>
        """, unsafe_allow_html=True)
        
        st.caption("Secure login via Google")
    
    with col2:
        st.subheader("Or continue as Guest")
        st.info("Quick access without login\n(Data won't be saved)")
        
        if st.button("🚀 Continue as Guest", use_container_width=True):
            st.session_state.user_id = f"guest_{uuid.uuid4().hex[:8]}"
            st.session_state.user_email = "guest@kitchenmate.app"
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
    """Load user's saved data from Firestore"""
    if st.session_state.user_email.startswith("guest"):
        return  # Skip for guest users
    
    try:
        doc_ref = db.collection("users").document(st.session_state.user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            
            # Load preferences
            if "preferences" in data:
                prefs = data["preferences"]
                st.session_state.user_preferences = prefs
                st.session_state.allergies = prefs.get("allergies", "")
                
                diet = prefs.get("diet", "")
                if diet == "Jain":
                    st.session_state.jain_mode = True
                if diet in ["Pure Veg", "Vegan", "Jain"]:
                    st.session_state.pure_veg_mode = True
            
            # Load inventory
            if "inventory" in data:
                st.session_state.inventory = data["inventory"]
            if "inventory_prices" in data:
                st.session_state.inventory_prices = data["inventory_prices"]
            if "inventory_expiry" in data:
                st.session_state.inventory_expiry = data["inventory_expiry"]
            if "grocery_list" in data:
                st.session_state.grocery_list = set(data["grocery_list"])
            
    except Exception as e:
        st.warning(f"Couldn't load saved data: {str(e)}")

# ================= AUTH CHECK =================

# Check if user is authenticated
if not st.session_state.is_authenticated:
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
if "unit_system" not in st.session_state:
    st.session_state.unit_system = "metric"
if "servings" not in st.session_state:
    st.session_state.servings = 1
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False
if "voice_language" not in st.session_state:
    st.session_state.voice_language = "English"
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
if "listening_active" not in st.session_state:
    st.session_state.listening_active = False
if "listening_status" not in st.session_state:
    st.session_state.listening_status = "idle"  # idle, listening, recording, processing
if "wake_word_detected" not in st.session_state:
    st.session_state.wake_word_detected = False
if "voice_command_queue" not in st.session_state:
    st.session_state.voice_command_queue = queue.Queue()
if "listening_thread" not in st.session_state:
    st.session_state.listening_thread = None
if "jain_mode" not in st.session_state:
    st.session_state.jain_mode = False
if "new_command_available" not in st.session_state:
    st.session_state.new_command_available = False
if "listening_error" not in st.session_state:
    st.session_state.listening_error = None
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
# ================= VOICE HELPERS =================
def listen_for_wake_word_chunk():
    """Listen for a short audio chunk and check for wake word"""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 4000  # Adjust for sensitivity
    recognizer.dynamic_energy_threshold = True
    
    try:
        with sr.Microphone() as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            # Listen for 3 seconds
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
            
            # Transcribe
            text = recognizer.recognize_google(audio).lower()
            
            # Check for wake word variants
            wake_words = ["hey chef", "hey chief", "a chef", "hey chefs"]
            if any(wake_word in text for wake_word in wake_words):
                return True, text
            return False, text
            
    except sr.WaitTimeoutError:
        return False, ""
    except sr.UnknownValueError:
        return False, ""
    except sr.RequestError:
        return False, ""
    except Exception as e:
        return False, ""

def record_voice_command():
    """Record full voice command after wake word detected"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            # Listen for command (up to 8 seconds)
            audio = recognizer.listen(source, timeout=2, phrase_time_limit=8)
            text = recognizer.recognize_google(audio)
            return text
    except Exception as e:
        return None

def continuous_listening_loop():
    """Background thread for continuous listening"""
    while st.session_state.get('listening_active', False):
        try:
            if st.session_state.listening_status == "listening":
                # Listen for wake word
                wake_detected, heard_text = listen_for_wake_word_chunk()
                
                if wake_detected:
                    st.session_state.listening_status = "recording"
                    st.session_state.wake_word_detected = True
                    
                    # Small pause
                    time.sleep(0.5)
                    
                    # Record command
                    command = record_voice_command()
                    
                    if command:
                        st.session_state.voice_command_queue.put(command)
                        st.session_state.listening_status = "processing"
                        # Set flag to trigger rerun
                        st.session_state.new_command_available = True
                    else:
                        # No command received, go back to listening
                        st.session_state.listening_status = "listening"
                        st.session_state.wake_word_detected = False
            
            time.sleep(0.2)  # Increased delay to reduce CPU usage
            
        except Exception as e:
            st.session_state.listening_status = "error"
            st.session_state.listening_error = str(e)
            break
    
    # Cleanup when stopped
    st.session_state.listening_status = "idle"

def start_continuous_listening():
    """Start the continuous listening mode"""
    if not st.session_state.listening_active:
        st.session_state.listening_active = True
        st.session_state.listening_status = "listening"
        
        # Start listening thread
        thread = threading.Thread(target=continuous_listening_loop, daemon=True)
        thread.start()
        st.session_state.listening_thread = thread

def stop_continuous_listening():
    """Stop the continuous listening mode"""
    st.session_state.listening_active = False
    st.session_state.listening_status = "idle"
    st.session_state.wake_word_detected = False
    st.session_state.new_command_available = False
    
    # Wait for thread to finish
    if st.session_state.listening_thread and st.session_state.listening_thread.is_alive():
        st.session_state.listening_thread.join(timeout=2)
    
    st.session_state.listening_thread = None

    # ================= NEW: IMAGE DETECTION HELPER =================
def detect_ingredients_from_image(image_bytes):
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = openrouter_client.chat.completions.create( 
            model="google/gemini-flash-1.5",
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

def transcribe_audio(audio_bytes):
    """Convert speech to text using Google Speech Recognition"""
    try:
        recognizer = sr.Recognizer()
        audio = sr.AudioData(audio_bytes, 16000, 2)
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        return None

def text_to_speech(text, lang_code=None):
    """Convert text to speech. If lang_code not provided, uses session state."""
    if lang_code is None:
        lang_code = "mr" if st.session_state.voice_language == "Marathi" else \
                   "hi" if st.session_state.voice_language == "Hindi" else "en"
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception as e:
        st.error(f"TTS error: {str(e)}")
        return None

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
    """Enhanced ingredient extraction with stricter cleaning and Jain check"""
    text = text.lower().strip()
    
    # Isolate ingredients section if possible
    ing_markers = r'(ingredients?:?|सामग्री:?|required items:?|what you need:?)'
    step_markers = r'(steps?:?|instructions?:?|method:?|विधि:?|how to make:?)'
    
    ing_start = re.search(ing_markers, text)
    step_start = re.search(step_markers, text)
    
    if ing_start and step_start and ing_start.start() < step_start.start():
        ing_text = text[ing_start.end():step_start.start()].strip()
    elif ing_start:
        ing_text = text[ing_start.end():].strip()
    else:
        ing_text = text
    
    ingredients = []
    
    # Main patterns (improved to split qty/unit/name cleaner)
    patterns = [
        r'(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)?\s*(g|kg|gram|grams|ml|l|liter|litre|pcs?|piece|pieces|tsp|teaspoon|tbsp|tablespoon|cup|cups|pack|packet|medium|large|small)?\s+([a-z][\w\s\-]{3,})(?=\s*(?:,|\.|;|\n|$|\(|\[|to taste|as needed))',
        r'(half|quarter|a|one|two|three|four|five|six|seven|eight|nine|ten|handful|pinch|some)?\s+([a-z][\w\s\-]{3,})(?=\s*(?:,|\.|;|\n|$|\(|\[|to taste|as needed))',
        r'([a-z][\w\s\-]{3,})\s*(to taste|as needed|as required|a pinch of?|to garnish)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, ing_text, re.IGNORECASE):
            qty_str = "as needed"
            name = ""
            groups = match.groups()
            
            # Extract qty and name, strip extra words
            if len(groups) >= 3 and groups[2]:
                qty_num = groups[0] or ""
                unit = groups[1] or ""
                name = groups[2].strip()
                qty_str = f"{qty_num} {unit}".strip() if qty_num or unit else "as needed"
            elif len(groups) >= 2 and groups[1]:
                qty_str = groups[0].strip() if groups[0] else "as needed"
                name = groups[1].strip()
            elif groups[0]:
                name = groups[0].strip()
                qty_str = groups[1].strip() if len(groups) > 1 and groups[1] else "as needed"
            
            # Clean name: remove "of", "a", "an", "some" if at start
            name = re.sub(r'^(of|a|an|some)\s+', '', name).strip()
            
            # Skip invalid or short names
            if not name or len(name) < 3:
                continue
            
def extract_ingredients(text, jain_mode=False):
    """Enhanced ingredient extraction with stricter cleaning and Jain check"""
    text = text.lower().strip()
    
    # Isolate ingredients section if possible
    ing_markers = r'(ingredients?:?|सामग्री:?|required items:?|what you need:?)'
    step_markers = r'(steps?:?|instructions?:?|method:?|विधि:?|how to make:?)'
    
    ing_start = re.search(ing_markers, text)
    step_start = re.search(step_markers, text)
    
    if ing_start and step_start and ing_start.start() < step_start.start():
        ing_text = text[ing_start.end():step_start.start()].strip()
    elif ing_start:
        ing_text = text[ing_start.end():].strip()
    else:
        ing_text = text
    
    ingredients = []
    
    # Main patterns (improved to split qty/unit/name cleaner)
    patterns = [
        r'(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)?\s*(g|kg|gram|grams|ml|l|liter|litre|pcs?|piece|pieces|tsp|teaspoon|tbsp|tablespoon|cup|cups|pack|packet|medium|large|small)?\s+([a-z][\w\s\-]{3,})(?=\s*(?:,|\.|;|\n|$|\(|\[|to taste|as needed))',
        r'(half|quarter|a|one|two|three|four|five|six|seven|eight|nine|ten|handful|pinch|some)?\s+([a-z][\w\s\-]{3,})(?=\s*(?:,|\.|;|\n|$|\(|\[|to taste|as needed))',
        r'([a-z][\w\s\-]{3,})\s*(to taste|as needed|as required|a pinch of?|to garnish)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, ing_text, re.IGNORECASE):
            qty_str = "as needed"
            name = ""
            groups = match.groups()
            
            # Extract qty and name, strip extra words
            if len(groups) >= 3 and groups[2]:
                qty_num = groups[0] or ""
                unit = groups[1] or ""
                name = groups[2].strip()
                qty_str = f"{qty_num} {unit}".strip() if qty_num or unit else "as needed"
            elif len(groups) >= 2 and groups[1]:
                qty_str = groups[0].strip() if groups[0] else "as needed"
                name = groups[1].strip()
            elif groups[0]:
                name = groups[0].strip()
                qty_str = groups[1].strip() if len(groups) > 1 and groups[1] else "as needed"
            
            # Clean name: remove "of", "a", "an", "some" if at start
            name = re.sub(r'^(of|a|an|some)\s+', '', name).strip()
            
            # Skip invalid or short names
            if not name or len(name) < 3:
                continue
            
            # Reject patterns - comprehensive list
            reject_patterns = [
                r'\b(less|more|extra|enough|plenty|sufficient|adequate)\b',
                r'\b(amount|quantity|portion|serving|measure|measurement)\b',
                r'\b(handful|pinch|dash|splash|sprinkle|drizzle)\b',
                r'\b(little|some|few|several|many|much|lot)\b',
                r'\b(half|quarter|third|double|triple)\b',
                r'\b(piece|pieces|slice|slices|chunk|chunks)\b',
                r'\b(level|heaping|rounded|packed)\b',
                r'\b(taste|tasting|adjust|according|required|needed)\b',
                r'\b(prefer|preference|optional|choice|variation)\b',
                r'\b(mild|medium|spicy|hot|cold|warm|cool)\b',
                r'\b(salty|sweet|sour|bitter|tangy|savory)\b',
                r'\b(strong|weak|light|heavy|thick|thin)\b',
                r'\b(cook|cooking|cooks|stir|stirring|stirs)\b',
                r'\b(add|adding|adds|mix|mixing|mixes)\b',
                r'\b(serve|serving|serves|fry|frying|fries)\b',
                r'\b(boil|boiling|boils|bake|baking|bakes)\b',
                r'\b(heat|heating|heats|preheat|preheating|preheats)\b',
                r'\b(simmer|simmering|simmers|saute|sauteing|sautes)\b',
                r'\b(roast|roasting|roasts|grill|grilling|grills)\b',
                r'\b(steam|steaming|steams|blanch|blanching|blanches)\b',
                r'\b(broil|broiling|broils|toast|toasting|toasts)\b',
                r'\b(poach|poaching|poaches)\b',
                r'\b(cooked|stirred|added|mixed|served|fried|boiled)\b',
                r'\b(baked|heated|preheated|simmered|sauteed|roasted)\b',
                r'\b(grilled|steamed|blanched|broiled|toasted|poached)\b',
                r'\b(prepared|finished|combined|blended|whisked)\b',
                r'\b(melted|dissolved|reduced|thickened)\b',
                r'\b(chop|chopping|chops|slice|slicing|slices)\b',
                r'\b(dice|dicing|dices|mince|mincing|minces)\b',
                r'\b(grate|grating|grates|grind|grinding|grinds)\b',
                r'\b(crush|crushing|crushes|peel|peeling|peels)\b',
                r'\b(wash|washing|washes|rinse|rinsing|rinses)\b',
                r'\b(drain|draining|drains|soak|soaking|soaks)\b',
                r'\b(marinate|marinating|marinates|season|seasoning|seasons)\b',
                r'\b(garnish|garnishing|garnishes|squeeze|squeezing|squeezes)\b',
                r'\b(strain|straining|strains|filter|filtering|filters)\b',
                r'\b(chopped|sliced|diced|minced|grated|ground)\b',
                r'\b(crushed|peeled|washed|rinsed|drained|soaked)\b',
                r'\b(marinated|seasoned|garnished|squeezed|strained)\b',
                r'\b(filtered|cleaned|trimmed|cut|shredded)\b',
                r'\b(pour|pouring|pours|poured|use|using|uses|used)\b',
                r'\b(put|putting|puts|take|taking|takes|took|taken)\b',
                r'\b(keep|keeping|keeps|kept|let|letting|lets)\b',
                r'\b(bring|bringing|brings|brought|reduce|reducing|reduces|reduced)\b',
                r'\b(turn|turning|turns|turned|flip|flipping|flips|flipped)\b',
                r'\b(cover|covering|covers|covered|uncover|uncovering|uncovers|uncovered)\b',
                r'\b(remove|removing|removes|removed|transfer|transferring|transfers|transferred)\b',
                r'\b(place|placing|places|placed|set|setting|sets)\b',
                r'\b(arrange|arranging|arranges|arranged)\b',
                r'\b(blend|blending|blends|blended|whisk|whisking|whisks|whisked)\b',
                r'\b(beat|beating|beats|beaten|whip|whipping|whips|whipped)\b',
                r'\b(fold|folding|folds|folded|knead|kneading|kneads|kneaded)\b',
                r'\b(combine|combining|combines|combined)\b',
                r'\b(incorporate|incorporating|incorporates|incorporated)\b',
                r'\b(toss|tossing|tosses|tossed)\b',
                r'\b(then|now|next|after|before|during|while|until)\b',
                r'\b(when|once|first|second|third|finally|lastly)\b',
                r'\b(meanwhile|simultaneously|immediately|gradually)\b',
                r'\b(already|still|yet|just|soon|later)\b',
                r'\b(minute|minutes|hour|hours|second|seconds)\b',
                r'\b(overnight|day|days|week|weeks|month|months)\b',
                r'\b(of|in|on|at|to|for|with|from|by|about)\b',
                r'\b(into|onto|over|under|above|below|between|among)\b',
                r'\b(through|across|along|around|behind|beside)\b',
                r'\b(near|against|without|within|towards|upon)\b',
                r'\b(and|or|but|nor|yet|so|if|though|although)\b',
                r'\b(because|since|unless|while|whereas|whether)\b',
                r'\b(a|an|the|this|that|these|those)\b',
                r'\b(my|your|his|her|its|our|their)\b',
                r'\b(each|every|all|both|some|any|no|none)\b',
                r'\b(it|they|them|we|us|you|he|she|him|her)\b',
                r'\b(what|which|who|whom|whose|where|when|why|how)\b',
                r'\b(be|is|are|am|was|were|been|being)\b',
                r'\b(have|has|had|having|do|does|did|doing|done)\b',
                r'\b(will|would|shall|should|can|could|may|might|must)\b',
                r'\b(well|very|too|quite|rather|really|truly)\b',
                r'\b(simply|just|only|merely|exactly|precisely)\b',
                r'\b(still|yet|already|always|never|often|rarely)\b',
                r'\b(quickly|slowly|gently|carefully|thoroughly)\b',
                r'\b(evenly|uniformly|constantly|continuously)\b',
                r'\b(make|makes|made|making|give|gives|gave|given|giving)\b',
                r'\b(get|gets|got|gotten|getting|become|becomes|became|becoming)\b',
                r'\b(see|sees|saw|seen|seeing|look|looks|looked|looking)\b',
                r'\b(find|finds|found|finding|want|wants|wanted|wanting)\b',
                r'\b(need|needs|needed|needing|try|tries|tried|trying)\b',
                r'\b(help|helps|helped|helping|start|starts|started|starting)\b',
                r'\b(stop|stops|stopped|stopping|continue|continues|continued|continuing)\b',
                r'\b(not|no|none|never|neither|nor|yes|ok|okay|sure|certainly|definitely)\b',
                r'\b(method|procedure|instructions|steps|directions)\b',
                r'\b(recipe|preparation|prep|total|ready)\b',
                r'\b(ingredients|ingredient|items|things)\b',
                r'\b(note|tip|tips|important|remember)\b',
                r'\b(optional|required|necessary|essential)\b',
                r'\b(serve|serving|serves|served|enjoy|enjoying|enjoys|enjoyed)\b',
                r'\b(garnish|garnished|garnishing|plate|plated|plating|presentation)\b',
                r'\b(dish|bowl|pan|pot|container)\b',
                r'\b(hot|cold|warm|cool|room temperature|chilled)\b',
                r'\b(frozen|thawed|fresh|stale|ripe|unripe)\b',
                r'\b(crispy|crunchy|soft|tender|firm|hard)\b',
                r'\b(smooth|creamy|chunky|lumpy|grainy)\b',
                r'\b(like|as|than|same|similar|different)\b',
                r'\b(such|kind|type|sort|variety)\b',
                r'\b(better|worse|best|worst|more|most|less|least)\b',
                r'\b(bowl|pan|pot|wok|kadhai|tawa|griddle)\b',
                r'\b(plate|dish|container|jar|bottle|bag)\b',
                r'\b(spoon|fork|knife|spatula|ladle|whisk)\b',
                r'\b(blender|mixer|grinder|processor|oven|stove)\b',
                r'\b(top|bottom|side|center|middle|edge)\b',
                r'\b(left|right|front|back|inside|outside)\b',
                r'\b(up|down|high|low|deep|shallow)\b',
                r'\b(to taste|as needed|as required|if needed)\b',
                r'\b(for serving|for garnish|for decoration)\b',
                r'\b(according to taste|based on preference)\b',
                r'\b(such as|like this|for example)\b',
                r'\b(in order|so that|make sure)\b',
                r'\b(you can|you may|you should|you need)\b',
                r'\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b',
                r'\b(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b',
                r'\b(thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b',
                r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b',
                r'\b(raw|undercooked|overcooked|done|ready|finished)\b',
                r'\b(golden|brown|browned|caramelized|charred)\b',
                r'\b(translucent|opaque|clear|cloudy)\b',
                r'\b(thing|things|stuff|item|items)\b',
                r'\b(way|ways|means|manner|method)\b',
                r'\b(here|there|where|anywhere|somewhere|everywhere)\b',
                r'\b(something|anything|nothing|everything)\b',
                r'\b(video|recipe|cooking|kitchen|food|eat|eating)\b',
                r'\b(delicious|yummy|tasty|flavorful|aromatic)\b',
                r'\b(homemade|traditional|authentic|classic|modern)\b',
                r'\b(easy|simple|quick|fast|slow|difficult|hard)\b',
                r'\b(healthy|nutritious|diet|low fat|low calorie)\b',
                r'\b(vegan|vegetarian|non veg|gluten free|dairy free)\b',
                r'\b[a-z]\b',  # Single letters
                r'\b\w{1,2}\b',  # 1-2 character words
            ]
            
            # Check against reject patterns
            if any(re.search(p, name) for p in reject_patterns):
                continue
            
            # Check if starts with cooking verb
            if re.match(r'^(cook|stir|add|mix|serve|fry|boil|bake|heat|preheat|chop|slice|dice|grate|grind|pour|simmer|use|put|take|keep|let|bring|reduce|thicken|turn|flip|cover|uncover)', name):
                continue
            
            # Skip if Jain mode and not compatible
            if jain_mode and not is_jain_compatible(name):
                continue
            
            ingredients.append({
                'name': name,
                'qty_str': qty_str
            })
    
    # Remove duplicates
    seen = set()
    unique = [ing for ing in ingredients if ing['name'] not in seen and not seen.add(ing['name'])]
    
    return unique


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
When giving recipes:
- List ingredients with quantities
- Give clear, simple steps
- End with something friendly"""

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
st.set_page_config(
    page_title="KitchenMate - AI Cooking Assistant",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)
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

st.title("KitchenMate - Smart AI Assistant")

tab1, tab2, tab3, tab4, tab5, tab6, tab_scan = st.tabs([
    "💬 Chat", "📅 Meal Planner", "🛒 Grocery & Inventory",
    "🍲 Custom Recipes", "🔥 Tried Recipes", "❤️ Favourite Recipes",
    "📸 Scan Ingredients"
])

# Sidebar Settings
# ================= COMPLETE SIDEBAR SECTION =================
# Replace your entire sidebar section with this

with st.sidebar:
    st.header("⚙️ Settings")
    
    # User Info
    if st.session_state.get("user_email") and st.session_state.user_email != "guest@kitchenmate.app":
        st.write(f"👤 Logged in as:")
        st.caption(st.session_state.user_email)
    elif st.session_state.get("user_email") == "guest@kitchenmate.app":
        st.info("🚶 Guest Mode")
    
    st.markdown("---")
    
    # ────────── FIREBASE STATUS ──────────
    st.caption("🔧 Firebase Status")
    try:
        # Test the connection
        db.collection("_health_check").document("test").get()
        st.success("✅ Connected")
    except Exception as e:
        st.error("❌ Not Connected")
        with st.expander("See Details"):
            st.write(str(e))
    
    st.markdown("---")
    
    # ────────── VOICE ASSISTANT ──────────
    st.subheader("🎤 Voice Assistant")
    voice_enabled = st.toggle("Enable Voice Input/Output", value=st.session_state.voice_enabled)
    st.session_state.voice_enabled = voice_enabled
    
    if st.session_state.voice_enabled:
        voice_lang = st.radio("Voice Language", ["English", "Hindi", "Marathi"], key="voice_lang_select")
        st.session_state.voice_language = voice_lang
    
    st.markdown("---")
    
    # ────────── YOUR ALLERGIES ──────────
    st.session_state.allergies = st.text_input(
        "🚫 Your Allergies",
        value=st.session_state.allergies,
        placeholder="e.g., peanuts, dairy, shellfish",
        help="I'll avoid these in all recipe suggestions!"
    )
    
    st.markdown("---")
    
    # ────────── DIET PREFERENCES ──────────
    st.subheader("🎛️ Diet Preferences")
    
    # Jain Mode
    new_jain_mode = st.toggle(" Jain Mode (No root vegetables)", value=st.session_state.jain_mode)
    if new_jain_mode != st.session_state.jain_mode:
        st.session_state.jain_mode = new_jain_mode
        st.rerun()
    
    # Pure Veg Mode
    pure_veg = st.toggle("🌱 Pure Veg Mode", value=st.session_state.pure_veg_mode)
    if pure_veg != st.session_state.pure_veg_mode:
        st.session_state.pure_veg_mode = pure_veg
        st.rerun()
    
    # Health Mode
    health = st.toggle("💪 Health Mode (Low oil, sugar)", value=st.session_state.health_mode)
    if health != st.session_state.health_mode:
        st.session_state.health_mode = health
        st.rerun()
    
    st.markdown("---")
    
    # ────────── LANGUAGE MODE ──────────
    st.subheader("🗣️ Language")
    st.session_state.language_mode = st.radio(
        "Response Language",
        ["Hinglish", "English"],
        help="Choose how I should talk to you"
    )
    
    st.markdown("---")
    
    # ────────── UNITS ──────────
    st.subheader("📏 Units")
    unit_choice = st.radio(
        "Preferred unit system",
        ["Metric (kg, g, ml)", "American (lbs, oz, cups)"],
        index=0 if st.session_state.unit_system == "metric" else 1
    )
    new_system = "metric" if "Metric" in unit_choice else "imperial"
    if new_system != st.session_state.unit_system:
        st.session_state.unit_system = new_system
        st.rerun()
    
    st.markdown("---")
    
    # ────────── CUSTOM INGREDIENT ──────────
    st.subheader("➕ Custom Ingredient")
    
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
    
    # Remove ingredient
    if st.session_state.inventory:
        with st.expander("🗑️ Remove Ingredient"):
            remove_item = st.selectbox("Select item to remove", [""] + sorted(list(st.session_state.inventory.keys())))
            if remove_item and st.button("Remove", use_container_width=True):
                del st.session_state.inventory[remove_item]
                st.session_state.inventory_prices.pop(remove_item, None)
                st.session_state.inventory_expiry.pop(remove_item, None)
                st.success(f"🗑️ Removed {remove_item}")
                st.rerun()
    
    st.markdown("---")
    
    # ────────── ROUTINE WEEKLY GROCERY ──────────
    st.subheader("🛍️ Routine Weekly Grocery")
    
    # Default routine items (user can customize)
    if "routine_grocery_items" not in st.session_state:
        st.session_state.routine_grocery_items = [
            "rice", "flour", "oil", "milk", "eggs", 
            "vegetables", "spices", "fruits", "dal", "sugar"
        ]
    
    with st.expander("📝 Customize Routine Items"):
        st.write("**Current routine items:**")
        
        # Show current items with remove option
        items_to_remove = []
        for item in st.session_state.routine_grocery_items:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {item.capitalize()}")
            with col2:
                if st.button("❌", key=f"remove_routine_{item}"):
                    items_to_remove.append(item)
        
        # Remove items
        for item in items_to_remove:
            st.session_state.routine_grocery_items.remove(item)
            st.rerun()
        
        # Add new routine item
        new_routine = st.text_input("Add new routine item", placeholder="e.g., bread")
        if st.button("Add") and new_routine:
            if new_routine.lower() not in st.session_state.routine_grocery_items:
                st.session_state.routine_grocery_items.append(new_routine.lower())
                st.success(f"Added {new_routine}")
                st.rerun()
    
    # Quick add routine to grocery list
    if st.button("🛒 Add Routine to Grocery List", use_container_width=True):
        st.session_state.grocery_list.update(st.session_state.routine_grocery_items)
        st.success(f"✅ Added {len(st.session_state.routine_grocery_items)} items!")
        st.rerun()
    
    st.markdown("---")
    
    # ────────── SIGN OUT ──────────
    if st.button("🚪 Sign Out", use_container_width=True, type="primary"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("👋 Signed out successfully!")
        time.sleep(1)
        st.rerun()
    
    st.markdown("---")
    st.caption("Made by Manas")
# ────────────── CHAT TAB ──────────────
with tab1:
    st.subheader("💬 Chat with KitchenMate")
   
    st.session_state.servings = st.number_input("Number of servings", min_value=1, max_value=10, value=st.session_state.servings, step=1)
   
    # ────────────── CONTINUOUS LISTENING MODE ──────────────
    if st.session_state.voice_enabled:
        st.markdown("---")
        st.subheader("🎤 Voice Assistant Mode")
        
        col_listen1, col_listen2 = st.columns([3, 1])
        
        with col_listen1:
            if st.session_state.listening_status == "idle":
                status_text = "🟢 Ready - Click to start listening"
                status_color = "green"
            elif st.session_state.listening_status == "listening":
                status_text = "🔴 Listening for 'Hey Chef'..."
                status_color = "red"
            elif st.session_state.listening_status == "recording":
                status_text = "🎙️ Recording your command..."
                status_color = "orange"
            elif st.session_state.listening_status == "processing":
                status_text = "⚙️ Processing..."
                status_color = "blue"
            else:
                status_text = "⚠️ Error"
                status_color = "gray"
            
            st.markdown(f"**Status:** <span style='color:{status_color}; font-size: 18px;'>{status_text}</span>", unsafe_allow_html=True)
        
        with col_listen2:
            if not st.session_state.listening_active:
                if st.button("🎤 Start Listening", type="primary"):
                    start_continuous_listening()
                    st.rerun()
            else:
                if st.button("⏹️ Stop Listening", type="secondary"):
                    stop_continuous_listening()
                    st.rerun()
        

        # Check for voice commands in queue
# Check for voice commands in queue
if st.session_state.new_command_available and not st.session_state.voice_command_queue.empty():
    prompt = st.session_state.voice_command_queue.get()
    st.success(f"👂 Heard: **{prompt}**")
    
    # Reset flags
    st.session_state.new_command_available = False
    st.session_state.listening_status = "listening"
    
    # Process the command immediately
    # (will be handled in the normal prompt flow below)
else:
    prompt = None

# Auto-refresh while listening (less frequent to reduce load)
if st.session_state.listening_active and st.session_state.listening_status in ["listening", "recording"]:
    time.sleep(1)  # Increased from 0.5 to 1 second
    st.rerun()

# Show error if any
if st.session_state.listening_error:
    st.error(f"❌ Listening error: {st.session_state.listening_error}")
    if st.button("Clear Error"):
        st.session_state.listening_error = None
        st.rerun()

st.markdown("---")
st.info("💡 **How to use:** Click 'Start Listening', then say 'Hey Chef' followed by your question!")

    # Show chat history
for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
   
    # Voice Input Section
video_id = None

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
           
# Chat input with attachment button
col_input, col_attach = st.columns([9, 1])

with col_input:
    prompt = st.chat_input("Ask anything... (or upload gym diet chart)")

with col_attach:
    uploaded_file = st.file_uploader(
        label="",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key="chat_file_uploader"
    )

# Handle uploaded file (gym diet chart or receipt)
if uploaded_file is not None:
    # Add user message with file name
    st.session_state.messages.append({
        "role": "user",
        "content": f"Uploaded: **{uploaded_file.name}**"
    })
    
    with st.chat_message("user"):
        st.markdown(f"Uploaded: **{uploaded_file.name}**")
        if uploaded_file.type.startswith("image/"):
            st.image(uploaded_file)
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
                # For images - placeholder (add OCR later if needed)
                chart_text = "Image uploaded - text extraction pending OCR implementation"
            
            # Decide if it's a diet chart or receipt based on filename
            is_receipt = any(word in uploaded_file.name.lower() for word in ["receipt", "bill", "grocery", "kiranastore"])
            
            if is_receipt:
                # Receipt analysis
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
                # Diet chart analysis (default)
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
    # Manual voice recording (if not using continuous mode)

if st.session_state.voice_enabled and not st.session_state.listening_active and not video_id and not prompt:
        st.markdown("#### Or Record Manually:")
        col_v1, col_v2 = st.columns([4, 1])
        with col_v1:
            audio_input = st.audio_input("🎤 Record your question...")
        with col_v2:
            st.write("")  # spacing
            process_voice = st.button("🎙️ Send Voice")
        
        if process_voice and audio_input:
            with st.spinner("🎧 Listening..."):
                audio_bytes = audio_input.getvalue()
                prompt = transcribe_audio(audio_bytes)
                
                if prompt:
                    st.success(f"👂 You said: **{prompt}**")
                else:
                    st.error("❌ Could not understand. Please speak clearly.")
    
    # ────────────── YOUTUBE VIDEO PROCESSING ──────────────
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
                        
                        # Voice output
                        if st.session_state.voice_enabled:
                            lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                            audio_fp = text_to_speech(recipe, lang_code)
                            if audio_fp:
                                st.audio(audio_fp, format="audio/mp3", autoplay=False)
                
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
                            
                            if st.session_state.voice_enabled:
                                lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                                audio_fp = text_to_speech(recipe, lang_code)
                                if audio_fp:
                                    st.audio(audio_fp, format="audio/mp3", autoplay=False)
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
       
        allergy_note = f"User allergies: {st.session_state.allergies}. Avoid these!" if st.session_state.allergies else ""
        full_prompt = prompt + " " + allergy_note
        if st.session_state.servings > 1:
            full_prompt += f" (for {st.session_state.servings} people)"
       
        st.session_state.messages.append({"role": "user", "content": full_prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Soch raha hoon..."):
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
                   
                    if st.session_state.voice_enabled and response:
                        lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                        audio_fp = text_to_speech(response, lang_code)
                        if audio_fp:
                            st.audio(audio_fp, format="audio/mp3", autoplay=False)
                    # Resume listening if in continuous mode
                    if st.session_state.listening_active:
                        time.sleep(2)
                        st.session_state.listening_status = "listening"
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if st.session_state.listening_active:
                        st.session_state.listening_status = "listening"
    
if st.button("😴 Feeling Lazy? Suggest from Inventory"):
        inventory_str = ", ".join(st.session_state.inventory.keys())
        lazy_prompt = f"Suggest a simple recipe using only these ingredients: {inventory_str}. Keep it easy and quick."
        st.session_state.messages.append({"role": "user", "content": lazy_prompt})
        with st.chat_message("user"):
            st.markdown(lazy_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Soch raha hoon..."):
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
                    
                    if st.session_state.voice_enabled and response:
                        lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                        audio_fp = text_to_speech(response, lang_code)
                        if audio_fp:
                            st.audio(audio_fp, format="audio/mp3", autoplay=False)
                    
                    # Resume listening if in continuous mode
                    if st.session_state.listening_active:
                        time.sleep(2)
                        st.session_state.listening_status = "listening"
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if st.session_state.listening_active:
                        st.session_state.listening_status = "listening"
                   
   
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        col1, col2, col3, col4 = st.columns([2,2,2,2])
        with col1:
            if st.button("🍳 Start Cooking"):
                st.session_state.show_cooking_check = True
                st.session_state.show_nutrition = False
                st.session_state.show_substitutes = False
                st.session_state.ingredients_shown = False
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
   
if st.session_state.show_cooking_check and not st.session_state.cooking_mode:
        st.markdown("---")
        st.subheader("🍳 Ingredient Check")
        ingredients = extract_ingredients(st.session_state.last_recipe, jain_mode=st.session_state.jain_mode)
       
        if not ingredients:
            st.info("No ingredients could be detected in the last recipe.")
            st.session_state.show_cooking_check = False
            st.rerun()
        
        # ⭐ ADD THIS JAIN MODE WARNING HERE ⭐
        if st.session_state.jain_mode:
            non_jain = [ing['name'] for ing in ingredients if not is_jain_compatible(ing['name'])]
            if non_jain:
                st.warning(f"⚠️ **Jain Alert:** This recipe contains: {', '.join(non_jain)}")
                st.info("**Suggested substitutes:**")
                for item in non_jain:
                    substitute = get_jain_substitute(item)
                    st.write(f"• {item.capitalize()} → {substitute}")
                st.markdown("---")
        # ⭐ END OF JAIN WARNING ⭐
       
        if not st.session_state.ingredients_shown:
            st.session_state.ingredients_shown = True
            missing = []
            # ... rest of the code continues ...
            for ing in ingredients:
                name = ing['name'].lower()
                found_key = None
                for inv_item in st.session_state.inventory:
                    if inv_item in name or name in inv_item:
                        found_key = inv_item
                        break
                if not found_key:
                    missing.append(name)
            st.session_state.missing_ingredients = missing
       
        missing = st.session_state.missing_ingredients
        status_lines = []
        total_cost = 0.0
       
        for ing in ingredients:
            name = ing['name'].lower()
            qty_str = ing['qty_str']
           
            scaled_qty = scale_quantity(qty_str, st.session_state.servings)
            display_qty = convert_quantity(scaled_qty, st.session_state.unit_system)
           
            found_key = None
            for inv_item in st.session_state.inventory:
                if inv_item in name or name in inv_item:
                    found_key = inv_item
                    break
           
            if found_key:
                current_qty = st.session_state.inventory[found_key]
                status, color = get_quantity_status(current_qty)
                display_name = found_key.capitalize()
               
                price_per_100 = st.session_state.inventory_prices.get(found_key, 0)
                est_cost = 0.0
                if price_per_100 > 0:
                    match = re.search(r'\d*\.?\d+', qty_str)
                    if match:
                        num = float(match.group())
                        portion_factor = num / 100
                        est_cost = round(price_per_100 * portion_factor * st.session_state.servings, 1)
                        total_cost += est_cost
               
                line = f"✅ **{display_name}**: {display_qty}   <span style='color:{color};'>[{status}]</span>"
                status_lines.append(line)
            else:
                status_lines.append(f"❌ **{name.capitalize()}**: {display_qty}")
       
        st.write("### Ingredients List:")
        for line in status_lines:
            st.markdown(line, unsafe_allow_html=True)
       
        if total_cost > 0:
            st.caption(f"💰 Estimated cost ≈ ₹{total_cost:.1f}")
       
        if missing:
            st.error(f"**Missing:** {', '.join(m.capitalize() for m in missing)}")
            col1, col2 = st.columns(2)
            if col1.button("❌ Abort"):
                st.session_state.show_cooking_check = False
                st.session_state.ingredients_shown = False
                st.rerun()
            if col2.button("➕ Add Missing to Grocery"):
                for n in missing:
                    st.session_state.grocery_list.add(n)
                st.success(f"Added {len(missing)} items to grocery list!")
                st.session_state.show_cooking_check = False
                st.session_state.ingredients_shown = False
                st.rerun()
        else:
            st.success("✅ All ingredients available! Ready to cook?")
            if st.button("👨‍🍳 Start Step-by-Step Cooking"):
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
                
                if st.session_state.voice_enabled and response:
                    lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                    audio_fp = text_to_speech(response, lang_code)
                    if audio_fp:
                        st.audio(audio_fp, format="audio/mp3", autoplay=False)
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
                    
                    if st.session_state.voice_enabled and resp:
                        lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                        audio_fp = text_to_speech(resp, lang_code)
                        if audio_fp:
                            st.audio(audio_fp, format="audio/mp3", autoplay=False)
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
            
        
        # Voice output for step (already there, but ensure autoplay)
        if st.session_state.voice_enabled:
            lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
            audio_fp = text_to_speech(step_text, lang_code)
            if audio_fp:
                st.audio(audio_fp, format="audio/mp3", autoplay=True)  # ← autoplay=True
            # ───── NEW: TIMER FEATURE ─────
        # Parse time from step text
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
                seconds = 8 * 3600  # rough 8 hours
            else:
                seconds = 0
            
            if seconds > 0:
                st.markdown(f"**Suggested timer:** {amount} {unit}")
                
                if f"timer_running_{current}" not in st.session_state:
                    st.session_state[f"timer_running_{current}"] = False
                    st.session_state[f"timer_remaining_{current}"] = seconds
                
                col_timer1, col_timer2 = st.columns([3, 1])
                with col_timer1:
                    if not st.session_state[f"timer_running_{current}"]:
                        if st.button("⏱️ Start Timer"):
                            st.session_state[f"timer_running_{current}"] = True
                            st.session_state[f"timer_start_{current}"] = time.time()
                            st.rerun()
                    else:
                        elapsed = time.time() - st.session_state[f"timer_start_{current}"]
                        remaining = max(0, st.session_state[f"timer_remaining_{current}"] - elapsed)
                        
                        if remaining > 0:
                            progress = 1 - (remaining / st.session_state[f"timer_remaining_{current}"])
                            st.progress(progress)
                            mins, secs = divmod(int(remaining), 60)
                            st.markdown(f"**Time left:** {mins:02d}:{secs:02d}")
                            st.rerun()  # auto-refresh every second
                        else:
                            st.success("🎉 Time's up!")
                            st.balloons()
                            st.session_state[f"timer_running_{current}"] = False
                            # Play beep sound (browser alert sound)
                            st.markdown(
                                '<audio autoplay><source src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=" type="audio/wav"></audio>',
                                unsafe_allow_html=True
                            )
                
                with col_timer2:
                    if st.session_state[f"timer_running_{current}"]:
                        if st.button("Pause"):
                            st.session_state[f"timer_remaining_{current}"] -= (time.time() - st.session_state[f"timer_start_{current}"])
                            st.session_state[f"timer_running_{current}"] = False
                            st.rerun()
                        if st.button("Reset"):
                            st.session_state[f"timer_running_{current}"] = False
                            st.rerun()
        
        # ───── END OF TIMER FEATURE ─────
            # Step controls
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("⬅️ Previous" if current > 0 else "⬅️ First"):
                    if current > 0:
                        st.session_state.current_step -= 1
                        st.rerun()
            
            with col2:
                if st.button("🔄 Repeat"):
                    if st.session_state.voice_enabled:
                        lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                        audio_fp = text_to_speech(step_text, lang_code)
                        if audio_fp:
                            st.audio(audio_fp, format="audio/mp3", autoplay=True)
                    st.info(f"🔄 Repeating: {step_text}")
            
            with col3:
                if st.button("➡️ Next" if current < total_steps - 1 else "✅ Done!"):
                    if current < total_steps - 1:
                        st.session_state.current_step += 1
                        st.rerun()
                    else:
                        st.session_state.cooking_mode = False
                        st.session_state.current_step = 0
                        st.session_state.cooking_steps = []
                        st.rerun()
            
            with col4:
                if st.button("⛔ Exit Cooking"):
                    st.session_state.cooking_mode = False
                    st.session_state.current_step = 0
                    st.session_state.cooking_steps = []
                    st.session_state.show_cooking_check = False
                    st.rerun()
            
            # Voice commands if enabled
            if st.session_state.voice_enabled:
                st.markdown("---")
st.info("🎤 Say: next, previous, repeat, start timer, pause timer, resume timer, reset timer, done")

if st.button("🎤 Voice Command", type="primary"):
        with st.spinner("Listening..."):
            audio_input = st.audio_input("Speak now (next / repeat / timer commands)...")
            if audio_input:
                audio_bytes = audio_input.getvalue()
                command = transcribe_audio(audio_bytes)
                
                if command:
                    command = command.lower().strip()
                    st.success(f"Heard: **{command}**")
                            
                            # Process voice command
                    if any(word in command for word in ["next", "next step", "continue", "ahead"]):
                        if current < total_steps - 1:
                            st.session_state.current_step += 1
                            st.rerun()
                        else:
                            st.balloons()
                            st.success("All steps completed!")
                            st.session_state.cooking_mode = False
                            st.rerun()
                    
                    elif any(word in command for word in ["previous", "back", "last"]):
                        if current > 0:
                            st.session_state.current_step -= 1
                            st.rerun()
                        else:
                            st.info("Already at first step")
                    
                    elif any(word in command for word in ["repeat", "again", "repeat step"]):
                        if st.session_state.voice_enabled:
                            lang_code = "hi" if st.session_state.voice_language == "Hindi" else "en"
                            audio_fp = text_to_speech(step_text, lang_code)
                            if audio_fp:
                                st.audio(audio_fp, format="audio/mp3", autoplay=True)
                        st.info("Repeating current step")
                    
                    elif any(word in command for word in ["start timer", "timer on", "begin timer"]):
                        # Start timer logic (if timer exists for this step)
                        if f"timer_remaining_{current}" in st.session_state and st.session_state[f"timer_remaining_{current}"] > 0:
                            st.session_state[f"timer_running_{current}"] = True
                            st.session_state[f"timer_start_{current}"] = time.time()
                            st.success("Timer started!")
                            st.rerun()
                        else:
                            st.warning("No timer set for this step")
                    
                    elif any(word in command for word in ["pause timer", "stop timer"]):
                        if st.session_state.get(f"timer_running_{current}", False):
                            elapsed = time.time() - st.session_state[f"timer_start_{current}"]
                            st.session_state[f"timer_remaining_{current}"] -= elapsed
                            st.session_state[f"timer_running_{current}"] = False
                            st.success("Timer paused")
                            st.rerun()
                    
                    elif "resume" in command:
                        if f"timer_remaining_{current}" in st.session_state and st.session_state[f"timer_remaining_{current}"] > 0:
                            st.session_state[f"timer_running_{current}"] = True
                            st.session_state[f"timer_start_{current}"] = time.time()
                            st.success("Timer resumed!")
                            st.rerun()
                    
                    elif "reset" in command:
                        if f"timer_remaining_{current}" in st.session_state:
                            st.session_state[f"timer_running_{current}"] = False
                            st.rerun()
                            st.info("Timer reset")
                    
                    elif any(word in command for word in ["done", "finish", "complete"]):
                        st.balloons()
                        st.success("Cooking completed!")
                        st.session_state.cooking_mode = False
                        st.rerun()
                    
                    else:
                        st.warning(f"Didn't understand: '{command}'\nTry: next, previous, repeat, start timer, pause timer, done")
                else:
                     st.error("Couldn't hear clearly. Try again.")
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
        for item, qty in sorted(st.session_state.inventory.items()):
            status, color = get_quantity_status(qty)
            price = st.session_state.inventory_prices.get(item, None)
            price_str = f" (₹{price}/100g)" if price else ""
            st.markdown(f"- {item.capitalize()}: {qty} <span style='color:{color};'>[{status}]{price_str}</span>", unsafe_allow_html=True)
    with col2:
        st.subheader("🛒 Grocery List")
        if not st.session_state.grocery_list:
            st.info("List khali hai!")
        else:
            to_add = []
            for item in sorted(st.session_state.grocery_list):
                if st.checkbox(f"{item.capitalize()}", key=f"grocery_check_{item}"):
                    to_add.append(item)
            if to_add:
                for item in to_add:
                    st.session_state.inventory[item.lower()] = 500
                    st.session_state.grocery_list.remove(item)
                st.success(f"Added {len(to_add)} items to inventory!")
                st.rerun()
        if st.button("Clear Grocery"):
            st.session_state.grocery_list.clear()
            st.rerun()
    with st.sidebar:
         st.markdown("---")
    st.subheader("➕ Add to Inventory")
    new_item = st.text_input("Item Name")
    new_qty = st.number_input("Quantity (g/ml/pcs)", min_value=0, step=50)
    new_price = st.number_input("Price per 100g/piece (₹)", min_value=0.0, step=1.0)

    expiry_option = st.radio("Expiry Date", ["Estimate for me", "Manual input"])

    if st.button("Add Item") and new_item:
        key = new_item.lower().strip()
        st.session_state.inventory[key] = new_qty
        if new_price > 0:
            st.session_state.inventory_prices[key] = new_price

        if expiry_option == "Estimate for me":
            days = get_expiry_estimate(key)
            st.session_state.inventory_expiry[key] = days
            st.success(f"Added {new_item} ({new_qty}) — estimated expiry in ~{days} days")
        else:
            days = st.number_input("Days until expiry", min_value=1, step=1, key="manual_days")
            st.session_state.inventory_expiry[key] = days
            st.success(f"Added {new_item} ({new_qty}) — expires in {days} days")

        st.rerun()

    # Show current inventory with expiry
    if st.session_state.inventory:
        st.markdown("### Current Inventory")
        for item, qty in sorted(st.session_state.inventory.items()):
            expiry_days = st.session_state.inventory_expiry.get(item, None)
            if expiry_days is not None:
                if expiry_days < 0:
                    status = f"Expired ({expiry_days} days ago)"
                    color = "red"
                elif expiry_days <= 3:
                    status = f"Urgent ({expiry_days} days left)"
                    color = "orange"
                else:
                    status = f"OK ({expiry_days} days left)"
                    color = "green"
                st.markdown(f"- **{item.capitalize()}**: {qty}g/ml  <span style='color:{color}'>{status}</span>", unsafe_allow_html=True)
            else:
                st.write(f"- {item.capitalize()}: {qty}g/ml")
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

# ────────────── NEW TAB: SCAN INGREDIENTS (OpenRouter) ──────────────
with tab_scan:
    st.subheader("📸 Scan Ingredients")
    st.info("Take or upload photo → AI detects items → add to grocery/inventory")

    col_cam, col_upload = st.columns(2)
    with col_cam:
        camera_img = st.camera_input("Take photo of ingredients")
    with col_upload:
        uploaded_img = st.file_uploader("Or upload photo", type=["jpg", "jpeg", "png"])

    img_file = camera_img or uploaded_img

    if img_file is not None:
        st.image(img_file, caption="Your photo", use_column_width=True)

        if st.button("Detect Ingredients with AI"):
            with st.spinner("Analyzing photo..."):
                image_bytes = img_file.getvalue()
                detected_items = detect_ingredients_from_image(image_bytes)
                if detected_items:
                    st.success("Detected items:")
                    selected = []
                    for item in detected_items:
                        if st.checkbox(item.capitalize()):
                            selected.append(item)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Add Selected to Grocery"):
                            st.session_state.grocery_list.update(selected)
                            st.success(f"Added {len(selected)} items to grocery!")
                    with col2:
                        if st.button("Add Selected to Inventory"):
                            for item in selected:
                                st.session_state.inventory[item.lower()] = 500
                            st.success(f"Added {len(selected)} items to inventory!")
                else:
                    st.warning("No ingredients detected. Try a clearer photo.")
# ────────────────────────────────────────────────
#  AUTO-SAVE INVENTORY & RELATED DATA TO FIRESTORE
# ────────────────────────────────────────────────

if st.session_state.get("is_authenticated", False) and st.session_state.get("user_id"):
    try:
        user_data = {
            "inventory": dict(st.session_state.inventory),  # convert to plain dict for JSON
            "inventory_prices": dict(st.session_state.inventory_prices),
            "inventory_expiry": dict(st.session_state.inventory_expiry),
            "grocery_list": list(st.session_state.grocery_list),
            "last_updated": datetime.now().isoformat()
        }
        
        # Save (merge = True means update only these fields, don't overwrite others)
        db.collection("users").document(st.session_state.user_id).set(
            user_data,
            merge=True
        )
        
        # Optional: show tiny success message (remove if annoying)
        # st.caption("Inventory auto-saved ✓")
        
    except Exception as e:
        # Silent fail (don't break app), but log for you
        print(f"Auto-save failed: {str(e)}")
# Improved floating PWA install button
st.markdown("""
    <script>
    let deferredPrompt;
    
    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent default mini-infobar
        e.preventDefault();
        // Store the event for later use
        deferredPrompt = e;
        console.log('PWA install prompt ready');
        
        // Show floating button
        const btn = document.createElement('button');
        btn.innerHTML = '📲 Install App';
        btn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            padding: 12px 20px;
            background: #FF6B6B;
            color: white;
            border: none;
            border-radius: 50px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            cursor: pointer;
        `;
        
        btn.onclick = () => {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choice) => {
                if (choice.outcome === 'accepted') {
                    console.log('Installed!');
                }
                deferredPrompt = null;
                btn.remove();
            });
        };
        
        document.body.appendChild(btn);
    });
    </script>
""", unsafe_allow_html=True)
# ────────────────────────────────────────────────
#  Visible "Install App" Button for PWA
# ────────────────────────────────────────────────

st.markdown("---")

st.subheader("📲 Make KitchenMate Your App!")

st.info("""
Want quick access like a real app?  
Install it to your phone home screen — works offline too!
""")

# Big install button
if st.button("📱 Install KitchenMate App", type="primary", use_container_width=True):
    st.markdown("""
        <script>
        if (window.deferredPrompt) {
            window.deferredPrompt.prompt();
            window.deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                } else {
                    console.log('User dismissed the install prompt');
                }
                window.deferredPrompt = null;
            });
        } else {
            alert("Install prompt not available. On mobile: tap browser menu → 'Add to Home Screen'");
        }
        </script>
    """, unsafe_allow_html=True)
    st.success("Install prompt triggered! If nothing happens, check your browser menu → 'Add to Home Screen'")

# Fallback message for desktop users
st.caption("""
Desktop: This feature works best on mobile Chrome/Safari.  
Mobile: Look for 'Install' in address bar or browser menu.
""")

# Footer
st.markdown("---")
st.caption("KitchenMate By Manas  • Chat + Meal Planner + Grocery + Custom Recipes + Tried + Favourites • " + datetime.now().strftime("%Y-%m-%d"))