import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Environment variables
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]
JAYSON_PHONE = os.environ["JAYSON_PHONE"]
PAUL_PHONE = os.environ["PAUL_PHONE"]
ART_PHONE = os.environ["ART_PHONE"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Memory to avoid infinite loop
last_transcript = {"text": ""}

@app.route("/", methods=["GET"])
def home():
    return "Kitchen Design AI is live"

@app.route("/call", methods=["POST"])
def inbound_call():
    response = VoiceResponse()
    gather = Gather(input="speech", action="/transcription", method="POST", timeout=5)
    gather.say("Hi, this is Kitchen Design. How can I help you today?")
    response.append(gather)
    response.redirect("/call")
    return Response(str(response), mimetype="application/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("SpeechResult", "").strip()
    if not transcript:
        return _say_again()

    print("Transcript:", transcript)

    if transcript.lower() == last_transcript["text"].lower():
        return _say_again()
    last_transcript["text"] = transcript

    reply, transfer_to = analyze_intent(transcript)

    if transfer_to:
        response = VoiceResponse()
        response.say("Transferring your call now.")
        response.dial(transfer_to)
        return Response(str(response), mimetype="application/xml")

    send_email(transcript, reply)

    response = VoiceResponse()
    gather = Gather(input="speech", action="/transcription", method="POST", timeout=5)
    gather.say(reply)
    response.append(gather)
    response.redirect("/call")
    return Response(str(response), mimetype="application/xml")

def analyze_intent(message):
    try:
        chat = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You're an AI assistant for a kitchen design company. Detect if the caller wants to speak to Jayson, Paul, or Art. If not, determine if it's a new kitchen inquiry or something else."},
                {"role": "user", "content": message}
            ]
        )
        ai_reply = chat.choices[0].message.content.strip()

        # Transfer logic
        lowered = message.lower()
        if "paul" in lowered:
            return ai_reply, PAUL_PHONE
        if "art" in lowered:
            return ai_reply, ART_PHONE
        if "jayson" in lowered or "you" in lowered:
            return ai_reply, JAYSON_PHONE

        # Detect lead intent
        lead_keywords = ["kitchen", "quote", "estimate", "remodel", "design"]
        if any(word in lowered for word in lead_keywords):
            return ai_reply, JAYSON_PHONE

        return ai_reply, None
    except Exception as e:
        print("Error from OpenAI:", e)
        return "Sorry, I didn't catch that. Could you repeat it?", None

def send_email(transcript, reply):
    msg = MIMEText(f"Caller said: {transcript}\n\nAI replied: {reply}")
    msg["Subject"] = "Kitchen Design Call Summary"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
    except Exception as e:
        print("Email failed:", e)

def _say_again():
    response = VoiceResponse()
    gather = Gather(input="speech", action="/transcription", method="POST", timeout=5)
    gather.say("Sorry, I didn't catch that. Can you please repeat?")
    response.append(gather)
    response.redirect("/call")
    return Response(str(response), mimetype="application/xml")
