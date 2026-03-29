# Bedside Assistant - Patient Support Voice System

A Flask-based voice assistance application designed for hospital patients. The system helps patients request services through natural language voice input and automatically alerts management staff via email.

## Features

- **Voice-Activated Requests**: Patients can speak naturally to request services
- **Conversation State Management**: Intelligent conversation flow with contextual responses
- **Audio Generation**: Text-to-Speech (gTTS) for all assistant responses
- **Auto-Email Notifications**: Manager alerts sent via SMTP when patients complete requests
- **Conversation Logging**: Complete conversation history saved for audit trails
- **Service Categories**:
  - Housekeeping (cleaning, towels, laundry)
  - Room Service (food, drinks, snacks, tiffins)
  - Beverages (coffee, drinks, water)
  - Transport (wheelchair, stretcher, room changes)
  - Toiletries (dental, bath, shaving kits)
  - Entertainment (newspapers)
  - Urgent Support (nurse assistance, complaints)

## Project Structure

```
Bedside Assistant/
├── app.py                 # Main Flask application
├── voice_assistance.html  # Frontend UI
├── patient_audio_responses/    # Generated audio files
└── patient_conversations/      # Conversation logs
```

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. **Clone/Download the project**:
   ```bash
   cd "Bedside Assistant"
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install flask flask-cors gtts python-dotenv
   ```

## Configuration

### Email Configuration (IMPORTANT)

The application sends email notifications to hospital managers. Configure these settings using environment variables:

1. **Create a `.env` file** in the project root:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-app-password
   MANAGER_EMAIL=manager-email@example.com
   ```

2. **For Gmail**:
   - Use your Gmail address for `SENDER_EMAIL`
   - Use a 16-character [App Password](https://support.google.com/accounts/answer/185833) for `SENDER_PASSWORD`
   - Never use your main Gmail password

3. **For Other Email Providers**:
   - Get SMTP server details from your provider
   - Use appropriate port (typically 587 for TLS or 465 for SSL)

## Running the Application

1. **Ensure virtual environment is activated** (if using one)

2. **Start the Flask server**:
   ```bash
   python app.py
   ```

3. **Access the application**:
   - Open browser to `http://127.0.0.1:5000`
   - Allow microphone access when prompted
   - Start speaking to the assistant

## API Endpoints

### POST `/start_conversation`
Initiates a new patient assistance session.

**Response**:
```json
{
  "success": true,
  "session_id": "20260329_143022_123456",
  "response_text": "Hello! I'm your Patient Assistance. How can I help you today?",
  "audio_url": "http://127.0.0.1:5000/audio/greeting_20260329_143022_123456.mp3",
  "should_listen": true
}
```

### POST `/process_conversation`
Processes user voice input and generates response.

**Request**:
```json
{
  "query": "I need a cup of coffee",
  "session_id": "20260329_143022_123456"
}
```

**Response**:
```json
{
  "success": true,
  "response_text": "I can arrange some fresh coffee for you. What type would you prefer? We have Black Coffee, Cappuccino, and Latte.",
  "audio_url": "http://127.0.0.1:5000/audio/response_20260329_143022_123456_143025.mp3",
  "session_id": "20260329_143022_123456",
  "should_listen": true,
  "conversation_ended": false
}
```

### POST `/end_conversation`
Manually ends a conversation and triggers manager notification.

**Request**:
```json
{
  "session_id": "20260329_143022_123456"
}
```

### GET `/audio/<filename>`
Retrieves generated audio files.

### GET `/conversations`
Lists all saved conversation logs.

## Conversation Flow Examples

### Coffee Request
1. Patient: "I need coffee"
2. Assistant: "What type would you prefer? Black Coffee, Cappuccino, or Latte?"
3. Patient: "Cappuccino please"
4. Assistant: "Would you like sugar with that?"
5. Patient: "Yes"
6. Assistant: "Is there anything else you need?"

### Emergency Assistance
1. Patient: "I'm in pain"
2. Assistant: "I am alerting your floor nurse! Assistance will be there soon. Please stay safe."
3. **Manager receives immediate email notification**

## File Structure - Conversation Logs

**Location**: `patient_conversations/`

- `conversation_{session_id}.txt` - Real-time conversation log
- `final_{session_id}.txt` - Complete session summary with patient details

**Example final log**:
```
=== CONVERSATION SESSION: 20260329_143022_123456 ===
Date: 2026-03-29 14:30:22
Patient Details Collected: {
  "coffee_type": "cappuccino",
  "coffee_sugar": "sugar"
}

--- Conversation Flow ---
Patient: I need coffee
Assistant: What type would you prefer? We have Black Coffee, Cappuccino, and Latte.
...
```

## Troubleshooting

### Issue: Emails not being sent
- Verify SMTP credentials in `.env` file
- Check Gmail App Password (not regular password)
- Enable "Less secure apps" for non-Gmail SMTP providers
- Check firewall/network restrictions on port 587/465

### Issue: Audio not generating
- Ensure `gtts` library is installed: `pip install gtts`
- Check internet connection (gTTS requires online connection)
- Verify `patient_audio_responses/` folder exists and is writable

### Issue: Microphone not working
- Check browser permissions for microphone access
- Ensure `voice_assistance.html` is being served correctly
- Verify browser is updated with Web Audio API support

### Issue: Conversations not being saved
- Check that `patient_conversations/` folder exists and is writable
- Verify file system permissions

## Supported Service Requests

| Category | Keywords | Sub-options |
|----------|----------|-------------|
| Beverages | coffee, caffeine | Black Coffee, Cappuccino, Latte (with/without sugar) |
| Meals | food, lunch, hungry | Missed meal, Special diet |
| Snacks | snack, bite, munch | Fruits, Sandwiches, Cookies |
| Drinks | drink, water, juice | Water, Juice, Soft drinks, Soda |
| Breakfast | tiffin, idli, dosa | Idli, Dosa, Upma |
| Cleaning | bedsheet, dirty, clean | Housekeeping alert |
| Laundry | laundry, wash clothes | Washing, Dry Cleaning, Ironing |
| Towels | towel, fresh towel | Small, Medium, Large |
| Toiletries | toothbrush, soap | Dental Kit, Bath Kit, Shaving Kit |
| Transport | wheelchair, stretcher | Wheelchair, Stretcher, Room transfer |
| Entertainment | newspaper, news | English, Hindi, Business |
| Emergency | nurse, pain, dizzy | Immediate nurse alert |
| Complaints | problem, issue | Complaint escalation |

## Development Notes

- **State Machine**: Conversation flow uses state-based architecture (state transitions in `CONVERSATION_STATES`)
- **Keyword Matching**: Uses longest keyword match for specificity
- **Threading**: Manager emails sent in background threads to avoid blocking
- **Session Management**: Each session stored in memory with unique ID
- **CORS Enabled**: Supports cross-origin requests for frontend

## Security Notes

⚠️ **IMPORTANT**: 
- Never commit sensitive credentials to version control
- Store email credentials in environment variables or `.env` files (not in code)
- Use application-specific passwords for Gmail (not main account password)
- Consider encrypting sensitive logs in production

## Future Enhancements

- [ ] Database integration for persistent storage
- [ ] Multi-language support
- [ ] Sentiment analysis for complaint detection
- [ ] Integration with hospital management system
- [ ] SMS notifications as alternative to email
- [ ] Advanced analytics dashboard
- [ ] Request fulfillment tracking
- [ ] Patient profile customization

## License

This project is the property of Apollo Hospitals Group. Unauthorized distribution is prohibited.

## Support

For issues or feature requests, contact the development team.

---

**Version**: 1.0  
**Last Updated**: March 29, 2026
