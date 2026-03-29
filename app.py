import os
import json
import logging
import smtplib
import threading
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from gtts import gTTS
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
app = Flask(__name__)
CORS(app)

# Folders
AUDIO_FOLDER = 'patient_audio_responses'
CONVERSATION_FOLDER = 'patient_conversations'
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(CONVERSATION_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)

# --- EMAIL CONFIGURATION ---
# REPLACE THESE WITH YOUR ACTUAL DETAILS
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your-email@gmail.com")     
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "your-app-password")     
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "manager-email@example.com")   

# --- Enhanced Conversation States ---
CONVERSATION_STATES = {
    "initial": {
        "towel": {
            "keywords": ["towel", "fresh towel", "new towel", "clean towel", "bath towel"],
            "response": "I hear you need a towel. Would you like a small, medium, or large towel?",
            "next_state": "towel_size"
        },
        "Cleaning": {
            "keywords": ["bedsheet","bed sheet","Curtains", "smell","pillow","dirty", "cleaning", "clean", "fresh linen", "change bed", "change sheets", "change pillowcase"],
            "response": "I will inform housekeeping. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "snacks": {
            "keywords": ["snack", "snacks", "something to eat", "bite", "munch"],
            "response": "What kind of snack would you like? We have fruits, sandwiches, or cookies available.",
            "next_state": "snack_type"
        },
        "Water": {
            "keywords": ["water", "bottle of water","glass of water","Juice"],
            "response": "We have hot water, cold water and normal available.",
            "next_state": "water_type"
        },
        "Drinks": {
            "keywords": ["drink", "beverage","Juice","Soda","soft drink"],
            "response": "What kind of drink would you like? We have water, soft drink, juice, or soda available.",
            "next_state": "drink_type"
        },
        "food": {
            "keywords": ["food", "meal", "lunch", "dinner", "breakfast", "hungry", "starving"],
            "response": "I can help with your food request. Is this for a missed meal or a special dietary requirement?",
            "next_state": "food_type"
        },
        "nurse": {
            "keywords": ["nurse", "assistance", "dizy", "not feeling well", "headach", "pain", "vomiting", "chills"],
            "response": "I am alerting your floor nurse! and the assistance will be there soon. Please stay safe",
            "next_state": "end_conversation"   
        },
        "transport": {
            "keywords": ["transport", "room change", "room_change", "wheel chair", "wheelchair", "stretcher", "move", "transfer", "assistance moving", "need to move"],
            "response": "I can help with transport. Are you needing a wheelchair, stretcher, or room change?",
            "next_state": "transport_type"
        },
        "complaint": {
            "keywords": ["complaint", "problem", "issue", "wrong", "not working", "bad", "unhappy"],
            "response": "I'm sorry to hear you have a complaint. Please tell me more about what's bothering you.",
            "next_state": "complaint_details"
        },
        # --- COFFEE (Points to coffee_type) ---
        "Coffee": {
            "keywords": ["coffee", "caffeine", "hot drink", "espresso", "brew"],
            "response": "I can arrange some fresh coffee for you. What type would you prefer? We have Black Coffee, Cappuccino, and Latte.",
            "next_state": "coffee_type"
        },
        # --- TIFFINS ---
        "Tiffins": {
            "keywords": ["tiffin", "breakfast", "morning meal", "idli", "dosa", "puri"],
            "response": "I can help with a tiffin request. What would you like? We have Idli, Dosa, and Upma available.",
            "next_state": "tiffin_type"
        },
        # --- LAUNDRY ---
        "Laundry": {
            "keywords": ["laundry", "wash clothes", "dry clean", "ironing", "press clothes", "dirty clothes"],
            "response": "I can arrange for laundry service. Do you need Washing, Dry Cleaning, or just Ironing?",
            "next_state": "laundry_service"
        },
        # --- TOILETRIES ---
        "Toiletries": {
            "keywords": ["toothbrush", "toothpaste", "soap", "shampoo", "comb", "shaving", "razor", "toiletries", "kit"],
            "response": "I can send up some toiletries. Do you need a Dental Kit, Bath Kit (Soap/Shampoo), or Shaving Kit?",
            "next_state": "toiletry_item"
        },
        # --- NEWSPAPER ---
        "Newspaper": {
            "keywords": ["news", "newspaper", "paper", "magazine", "read", "morning paper"],
            "response": "I can request a newspaper for you. Would you prefer English, Hindi, or a Business paper?",
            "next_state": "newspaper_lang"
        },
        "default": {
            "response": "I'm here to help. Could you please tell me what you need assistance with?",
            "next_state": "initial"
        }
    },
    
    # --- SUB-STATES ---

    # 1. Coffee Flow (Type -> Sugar)
    "coffee_type": {
        "black": {
            "keywords": ["black", "black coffee", "americano", "no milk", "sugar free"],
            "response": "Understood, a Black Coffee. Would you like to add sugar?",
            "next_state": "coffee_sugar"
        },
        "cappuccino": {
            "keywords": ["cappuccino", "foam", "froth"],
            "response": "A Cappuccino. Would you like sugar with that?",
            "next_state": "coffee_sugar"
        },
        "latte": {
            "keywords": ["latte", "milk coffee", "milky"],
            "response": "A Latte. Do you want sugar added?",
            "next_state": "coffee_sugar"
        },
        "default": {
            "response": "Please choose from Black Coffee, Cappuccino, or Latte.",
            "next_state": "coffee_type"
        }
    },
    "coffee_sugar": {
        "sugar": {
            "keywords": ["sugar", "yes", "sweet", "add sugar", "sugar please", "with sugar"],
            "response": "Noted, with sugar. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "no_sugar": {
            "keywords": ["no", "no sugar", "sugar free", "without sugar", "plain"],
            "response": "Okay, no sugar. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Could you please clarify? Do you want sugar or no sugar?",
            "next_state": "coffee_sugar"
        }
    },

    # 2. Other Sub-States
    "laundry_service": {
        "wash": {
            "keywords": ["wash", "washing", "laundry", "clean"],
            "response": "I'll send a housekeeping attendant to collect your clothes for washing. Is there anything else?",
            "next_state": "anything_else"
        },
        "dry_clean": {
            "keywords": ["dry clean", "dry cleaning", "delicate"],
            "response": "Noted. I'll arrange for the dry cleaning service to pick up your items. Anything else?",
            "next_state": "anything_else"
        },
        "ironing": {
            "keywords": ["iron", "ironing", "press", "pressing"],
            "response": "I'll have someone come by to collect your clothes for ironing. Would you like anything else?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose between Washing, Dry Cleaning, or Ironing.",
            "next_state": "laundry_service"
        }
    },
    "toiletry_item": {
        "dental": {
            "keywords": ["dental", "toothbrush", "paste", "teeth", "mouth"],
            "response": "I'm sending a Dental Kit to your room now. Anything else?",
            "next_state": "anything_else"
        },
        "bath": {
            "keywords": ["bath", "soap", "shampoo", "shower", "conditioner", "body wash"],
            "response": "I'll have a Bath Kit delivered. Do you need anything else?",
            "next_state": "anything_else"
        },
        "shaving": {
            "keywords": ["shaving", "razor", "cream", "shave", "foam"],
            "response": "I'm requesting a Shaving Kit for you immediately. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please specify if you need a Dental Kit, Bath Kit, or Shaving Kit.",
            "next_state": "toiletry_item"
        }
    },
    "newspaper_lang": {
        "english": {
            "keywords": ["english", "times", "hindu", "telegraph"],
            "response": "I'll ensure an English newspaper is brought to your room. Anything else?",
            "next_state": "anything_else"
        },
        "hindi": {
            "keywords": ["hindi", "local", "regional", "dainik"],
            "response": "I'll request a Hindi newspaper for you. Would you like anything else?",
            "next_state": "anything_else"
        },
        "business": {
            "keywords": ["business", "financial", "economic", "finance", "mint"],
            "response": "I'll have a Business/Financial paper sent up. Anything else I can help with?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose between English, Hindi, or Business newspaper.",
            "next_state": "newspaper_lang"
        }
    },
    "tiffin_type": {
        "idli": {
            "keywords": ["idli", "rice cake", "steamed"],
            "response": "I've noted your request for Idli. I'll send that to the kitchen. Is there anything else?",
            "next_state": "anything_else"
        },
        "dosa": {
            "keywords": ["dosa", "plain dosa", "masala dosa"],
            "response": "I've requested a Dosa for your tiffin. Would you like anything else?",
            "next_state": "anything_else"
        },
        "upma": {
            "keywords": ["upma", "rava", "semolina"],
            "response": "I'll ensure some warm Upma is brought to your room. Anything else I can help with?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose from Idli, Dosa, or Upma. What would you prefer?",
            "next_state": "tiffin_type"
        }
    },
    "drink_type": {
        "Water": {
            "keywords": ["water", "glass of water", "bottle of water"],
            "response": "Got it. I'll request water for you. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "Juice": {
            "keywords": ["juice", "fruit juice", "orange juice", "apple juice"],
            "response": "Alright. I'll request a Juice to your room. Would you like anything else?",
            "next_state": "anything_else"
        },
        "Softdrinks": {
            "keywords": ["soft drink", "cola", "pepsi", "coke","drink"],
            "response": "Okay. I'm sending a request for a Drink. Anything else I can help you with?",
            "next_state": "anything_else"
        },
        "Soda": {
            "keywords": ["soda", "carbonated drink", "fizzy drink"],
            "response": "Okay. I'm sending a request for a Soda. Anything else I can help you with?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose from water, juice, soft drink, or soda. What would you like?",
            "next_state": "drink_type"
        }
    },
    "water_type": {
        "Water": {
            "keywords": ["water", "glass of water", "bottle of water","plain water","normal"],
            "response": "Got it. I'll request water for you. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "Hot": {
            "keywords": ["Hot", "warm water", "heated water"],
            "response": "Alright. I'll request hot water for you. Would you like anything else?",
            "next_state": "anything_else"
        },
        "Cold": {
            "keywords": ["cold water", "iced", "chilled"],
            "response": "Okay. I'm sending a request for a Drink. Anything else I can help you with?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose from water, hot water, cold water. What would you like?",
            "next_state": "water_type"
        }
    },
    "towel_size": {
        "small": {
            "keywords": ["small", "little", "tiny"],
            "response": "Got it, a small towel. I'll alert the housekeeping team to bring you a small towel right away. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "medium": {
            "keywords": ["medium", "regular", "normal", "standard"],
            "response": "Alright, a medium towel. I'm notifying the housekeeping team to deliver a medium towel to your room. Would you like anything else?",
            "next_state": "anything_else"
        },
        "large": {
            "keywords": ["large", "big", "huge", "extra large", "xl"],
            "response": "Okay, a large towel. I'm sending a request to the housekeeping department for a large towel. Anything else I can help you with?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose between small, medium, or large towel. Which size would you prefer?",
            "next_state": "towel_size"
        }
    },
    "anything_else": {
        "yes": {
            "keywords": ["yes", "yeah", "sure", "okay", "please", "yep", "yes please"],
            "response": "What else can I help you with today?",
            "next_state": "initial"
        },
        "no": {
            "keywords": ["no", "nope", "nah", "no thanks", "no thank you", "that's all", "nothing else", "all set"],
            "response": "Thank you for your request. I've alerted the respective teams. Someone will attend to you shortly. Have a good day!",
            "next_state": "end_conversation"
        },
        "default": {
            "response": "Could you please let me know if you need anything else? Just say yes or no.",
            "next_state": "anything_else"
        }
    },
    "transport_type": {
        "wheelchair": {
            "keywords": ["wheelchair", "wheel chair", "chair", "wheel", "wheelchair assistance"],
            "response": "I've requested a wheelchair for you. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "stretcher": {
            "keywords": ["stretcher", "bed", "gurney", "medical bed", "patient bed"],
            "response": "I've requested a stretcher for you. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "room_change": {
            "keywords": ["room change", "change room", "transfer room", "move room", "different room"],
            "response": "I've notified the transport department about your room change request. Someone will assist you shortly. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please specify if you need a wheelchair, stretcher, or room change assistance.",
            "next_state": "transport_type"
        }
    },
    "snack_type": {
        "fruits": {
            "keywords": ["fruit", "fruits", "apple", "banana", "orange", "fruit salad", "fruit plate"],
            "response": "I'll request a fruit platter for you. Is there anything else you'd like?",
            "next_state": "anything_else"
        },
        "sandwich": {
            "keywords": ["sandwich", "sandwiches", "bread", "cheese sandwich", "ham sandwich", "veg sandwich"],
            "response": "I'll put in an order for a sandwich. Would you like anything else with that?",
            "next_state": "anything_else"
        },
        "cookies": {
            "keywords": ["cookie", "cookies", "biscuit", "biscuits", "sweet", "dessert"],
            "response": "I'll arrange for some cookies to be brought to your room. Anything else I can help with?",
            "next_state": "anything_else"
        },
        "Water": {
            "keywords": ["water", "bottle of water", "drink", "beverage", "glass of water"],
            "response": "I'll request this for you. Is there anything else you'd like?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Please choose from fruits, sandwiches,cookies or drinks and beverages. What would you like?",
            "next_state": "snack_type"
        }
    },
    "food_type": {
        "missed meal": {
            "keywords": ["missed", "missed meal", "late", "didn't get", "forgot", "no meal"],
            "response": "I'm sorry you missed your meal. I'll notify the kitchen to prepare a meal for you right away. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "special diet": {
            "keywords": ["special", "diet", "dietary", "allergy", "vegetarian", "vegan", "gluten", "diabetic"],
            "response": "I'll inform the dietary department about your special requirements. They'll prepare a suitable meal for you. Anything else I can help with?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "Is this about a missed meal or do you have special dietary requirements?",
            "next_state": "food_type"
        }
    },
    "complaint_details": {
        "resolved": {
            "keywords": ["fixed", "resolved", "okay now", "working now", "fine"],
            "response": "I'm glad to hear your issue was resolved. Is there anything else I can help you with?",
            "next_state": "anything_else"
        },
        "escalate": {
            "keywords": ["still", "not fixed", "worse", "urgent", "emergency", "help now"],
            "response": "I'm escalating your complaint to the supervisor immediately. Someone will be with you shortly. Is there anything else you need?",
            "next_state": "anything_else"
        },
        "default": {
            "response": "I've noted your complaint and will forward it to the appropriate department. Is there anything else I can help you with?",
            "next_state": "anything_else"
        }
    },
    "end_conversation": {
        "default": {
            "response": "Conversation ended. Thank you!",
            "next_state": "end_conversation"
        }
    }
}

# Store conversation sessions
conversation_sessions = {}

# --- Helper Functions ---
def log_conversation(session_id, speaker, message):
    """Log conversation to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {speaker}: {message}\n"
    
    log_file = os.path.join(CONVERSATION_FOLDER, f"conversation_{session_id}.txt")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    logging.info(f"Logged: {speaker}: {message}")

def generate_session_id():
    """Generate unique session ID"""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def find_best_match(user_input, state_options):
    """Find the best matching option based on keywords"""
    user_input_lower = user_input.lower().strip()
    
    best_match = None
    best_score = 0
    
    for option_name, option_data in state_options.items():
        if option_name == 'default':
            continue
            
        # Check each keyword
        for keyword in option_data.get('keywords', [option_name]):
            if keyword in user_input_lower:
                # Score based on keyword length (longer keywords are more specific)
                score = len(keyword)
                if score > best_score:
                    best_score = score
                    best_match = option_name
    
    return best_match

def send_manager_alert(session_id, details):
    """
    Sends an email to the manager with the patient's requests.
    Run this in a separate thread to avoid lagging the voice assistant.
    """
    if not details:
        logging.info(f"Session {session_id} ended with no requests. No email sent.")
        return

    try:
        # 1. Create a readable list of requests
        request_summary = ""
        for category, item in details.items():
            # Formats "coffee_sugar" to "Coffee Sugar: Yes"
            readable_category = category.replace('_', ' ').title() 
            readable_item = str(item).replace('_', ' ').title()
            request_summary += f"• {readable_category}: {readable_item}\n"

        # 2. Prepare Email
        subject = f"URGENT: New Patient Request (Session {session_id})"
        body = f"""
        Hello Manager,

        A patient has finished a request session. Please attend to the following:

        --------------------------------------
        {request_summary}
        --------------------------------------

        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Session ID: {session_id}
        """

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = MANAGER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # 3. Send Email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, MANAGER_EMAIL, msg.as_string())
        server.quit()

        logging.info(f"Alert email sent to manager for session {session_id}")

    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")

def process_user_input(user_input, session_id):

    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = {
            'state': 'initial', 
            'conversation': [], 
            'details': {}
        }
    
    session = conversation_sessions[session_id]
    current_state = session['state']
    
    matched_option = None
    response_info = None

    # --- 1. SPECIAL LOGIC FOR "ANYTHING ELSE" ---
    if current_state == "anything_else":
        no_match = find_best_match(user_input, CONVERSATION_STATES["anything_else"])
        if no_match == "no":
            response_info = CONVERSATION_STATES["anything_else"]["no"]
        
        if not response_info:
            # Check if they asked for a new service directly
            service_match = find_best_match(user_input, CONVERSATION_STATES["initial"])
            if service_match and service_match != "default":
                response_info = CONVERSATION_STATES["initial"][service_match]
        
        if not response_info:
            if no_match == "yes":
                response_info = CONVERSATION_STATES["anything_else"]["yes"]

        if not response_info:
             response_info = CONVERSATION_STATES["anything_else"]["default"]

    # --- 2. STANDARD LOGIC FOR ALL OTHER STATES ---
    else:
        matched_option = find_best_match(user_input, CONVERSATION_STATES[current_state])
        
        if matched_option:
            response_info = CONVERSATION_STATES[current_state][matched_option]
        else:
            response_info = CONVERSATION_STATES[current_state]['default']

    # --- 3. "FAST FORWARD" LOGIC ---
    # We found a category (e.g. Transport), but let's see if the user was specific
    if response_info:
        next_state_name = response_info['next_state']
        
        # Only check if the next state is a specific submenu (not initial/end)
        if next_state_name in CONVERSATION_STATES and next_state_name not in ['initial', 'anything_else', 'end_conversation']:
            
            # Check the NEXT state's keywords against the CURRENT input
            specific_match = find_best_match(user_input, CONVERSATION_STATES[next_state_name])
            
            # If we found a specific match (e.g. they said "Wheelchair" which is in transport_type)
            if specific_match and specific_match != 'default':
                # OVERRIDE the generic response with the specific response
                response_info = CONVERSATION_STATES[next_state_name][specific_match]
                # Save the detail immediately
                session['details'][next_state_name] = specific_match

    # --- SAVE DETAILS ---
    # This handles details if we are actually IN the sub-state (not fast-forwarded)
    if matched_option:
        # Existing options
        if current_state == "towel_size":
            session['details']['towel_size'] = matched_option
        elif current_state == "snack_type":
            session['details']['snack_type'] = matched_option
        elif current_state == "food_type":
            session['details']['food_type'] = matched_option
        elif current_state == "transport_type":
            session['details']['transport_type'] = matched_option
        
        # New Options
        elif current_state == "coffee_type":
            session['details']['coffee_type'] = matched_option
        elif current_state == "coffee_sugar":
            session['details']['coffee_sugar'] = matched_option
        elif current_state == "tiffin_type":
            session['details']['tiffin_type'] = matched_option
        elif current_state == "laundry_service":
            session['details']['laundry_service'] = matched_option
        elif current_state == "toiletry_item":
            session['details']['toiletry_item'] = matched_option
        elif current_state == "newspaper_lang":
            session['details']['newspaper_lang'] = matched_option

    # Update State & Log
    session['state'] = response_info['next_state']
    
    log_conversation(session_id, "Patient", user_input)
    session['conversation'].append(f"Patient: {user_input}")
    
    if response_info['next_state'] == 'end_conversation':
        save_final_conversation(session_id)
    
    return response_info['response']

def save_final_conversation(session_id):
    """Save complete conversation and NOTIFY MANAGER"""
    if session_id in conversation_sessions:
        session = conversation_sessions[session_id]
        
        # --- SEND EMAIL IN BACKGROUND ---
        # We check if 'details' is not empty before sending
        if session['details']:
            email_thread = threading.Thread(
                target=send_manager_alert, 
                args=(session_id, session['details'])
            )
            email_thread.start()
        # -------------------------------

        # Create final conversation file
        final_file = os.path.join(CONVERSATION_FOLDER, f"final_{session_id}.txt")
        
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(f"=== CONVERSATION SESSION: {session_id} ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Patient Details Collected: {json.dumps(session['details'], indent=2)}\n")
            f.write("\n--- Conversation Flow ---\n")
            
            # Write all conversation entries
            for entry in session['conversation']:
                f.write(f"{entry}\n")
            
            f.write("\n=== END OF CONVERSATION ===\n")
        
        logging.info(f"Final conversation saved for session {session_id}")
        
        # Remove from active sessions
        del conversation_sessions[session_id]

# --- Backend Routes ---
@app.route('/')
def index():
    return send_file('voice_assistance.html')

@app.route('/start_conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation session"""
    session_id = generate_session_id()
    conversation_sessions[session_id] = {
        'state': 'initial',
        'conversation': [],
        'details': {}
    }
    
    initial_response = "Hello! I'm your Patient Assistance. How can I help you today?"
    log_conversation(session_id, "Assistant", initial_response)
    
    # Generate audio for initial response
    try:
        audio_filename = f"greeting_{session_id}.mp3"
        audio_filepath = os.path.join(AUDIO_FOLDER, audio_filename)
        
        tts = gTTS(text=initial_response, lang='en', slow=False)
        tts.save(audio_filepath)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "response_text": initial_response,
            "audio_url": f"http://127.0.0.1:5000/audio/{audio_filename}",
            "should_listen": True
        })
        
    except Exception as e:
        logging.error(f"Error generating greeting audio: {e}")
        return jsonify({
            "success": False,
            "message": "Error starting conversation"
        }), 500

@app.route('/process_conversation', methods=['POST'])
def process_conversation():
    """Process conversation turn"""
    data = request.json
    user_input = data.get('query', '').strip()
    session_id = data.get('session_id', '')
    
    if not user_input:
        return jsonify({
            "success": False,
            "message": "No input detected"
        }), 400
    
    if not session_id:
        return jsonify({
            "success": False,
            "message": "Invalid session"
        }), 400
    
    # Process user input
    try:
        response_text = process_user_input(user_input, session_id)
    except Exception as e:
        logging.error(f"Logic Error: {e}")
        return jsonify({"success": False, "message": "Logic Error"}), 500
    
    # Check if session still exists (it might have been deleted if conversation ended)
    if session_id in conversation_sessions:
        session = conversation_sessions[session_id]
        should_listen = session['state'] != 'end_conversation'
        
        # Log assistant response
        log_conversation(session_id, "Assistant", response_text)
        session['conversation'].append(f"Assistant: {response_text}")
    else:
        # If session is gone, it means conversation ended and was saved/deleted
        should_listen = False
        logging.info(f"Session {session_id} ended and removed.")
    
    # Generate audio
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"response_{session_id}_{timestamp}.mp3"
        audio_filepath = os.path.join(AUDIO_FOLDER, audio_filename)
        
        tts = gTTS(text=response_text, lang='en', slow=False)
        tts.save(audio_filepath)
        
        return jsonify({
            "success": True,
            "response_text": response_text,
            "audio_url": f"http://127.0.0.1:5000/audio/{audio_filename}",
            "session_id": session_id,
            "should_listen": should_listen,
            "conversation_ended": not should_listen
        })
        
    except Exception as e:
        logging.error(f"Error generating audio: {e}")
        return jsonify({
            "success": False,
            "message": "Error generating response"
        }), 500

@app.route('/end_conversation', methods=['POST'])
def end_conversation():
    """Manually end a conversation"""
    data = request.json
    session_id = data.get('session_id', '')
    
    if session_id in conversation_sessions:
        # Add manual end note
        conversation_sessions[session_id]['details']['ended_manually'] = True
        save_final_conversation(session_id)
        return jsonify({"success": True, "message": "Conversation ended"})
    
    return jsonify({"success": False, "message": "Session not found"}), 404

@app.route('/audio/<filename>')
def serve_audio(filename):
    try:
        return send_file(os.path.join(AUDIO_FOLDER, filename), mimetype='audio/mp3')
    except Exception as e:
        logging.error(f"Error serving audio {filename}: {e}")
        return jsonify({"error": "Audio file not found"}), 404

@app.route('/conversations')
def list_conversations():
    """List all saved conversations"""
    conversations = []
    for file in os.listdir(CONVERSATION_FOLDER):
        if file.startswith('final_'):
            conversations.append(file)
    return jsonify({"conversations": conversations})

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)