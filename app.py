import os
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
import openai
import smtplib
from email.message import EmailMessage

# Initialize Flask app
app = Flask(__name__)

# Set OpenAI API key
openai.api_key = os.environ["OPENAI_API_KEY"]

# Email settings
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

# Phone numbers for forwarding
FORWARD_NUMBERS = {
    "jayson": "+19076060669",
    "art": "+19413501228",
    "paul": "+19712171878"
}

@app.route("/call", methods=["POST"])
def call():
    response = VoiceResponse()
    gather = Gather(input="speech", action="/transcription", method="POST")
    gather.say("Hi, this is Kitchen Design. How can I help you today?", voice="alice")
    response.append(gather)
    return str(response)

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("SpeechResult", "").lower()
    print("Transcript:", transcript)

    if not transcript.strip():
        response = VoiceResponse()
        response.say("Sorry, I didn't catch that. Can you repeat?", voice="alice")
        response.redirect("/call")
        return str(response)

    # Check for transfer intent
    for name, number in FORWARD_NUMBERS.items():
        if name in transcript:
            response = VoiceResponse()
            response.say(f"Transferring you to {name.title()}.", voice="alice")
            response.dial(number)
            return str(response)

    # AI response
    reply = generate_ai_response(transcript)
    is_lead = any(kw in transcript for kw in ["quote", "estimate", "kitchen", "interested", "design"])

    if is_lead:
        forward_number = FORWARD_NUMBERS["jayson"]
        response = VoiceResponse()
        response.say(reply, voice="alice")
        response.dial(forward_number)
    else:
        response = VoiceResponse()
        response.say(reply, voice="alice")
        response.redirect("/call")

    send_email_summary(transcript, reply, is_lead)
    return str(response)

def generate_ai_response(message):
    try:
        result = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI answering service for a kitchen design company."},
                {"role": "user", "content": message}
            ]
        )
        return result.choices[0].message["content"]
    except Exception as e:
        print("OpenAI error:", e)
        return "Sorry, something went wrong. Please try again."

def send_email_summary(transcript, ai_reply, is_lead):
    try:
        subject = "New Call Summary" + (" [LEAD]" if is_lead else "")
        body = f"Transcript: {transcript}\n\nAI Reply: {ai_reply}"
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print("Email error:", e)

@app.route("/", methods=["GET"])
def home():
    return "Kitchen Design AI answering service is running."

if __name__ == "__main__":
    app.run(debug=True)
