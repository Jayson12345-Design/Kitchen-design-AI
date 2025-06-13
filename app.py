import os
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
JAYSON_PHONE = os.environ["JAYSON_PHONE"]
PAUL_PHONE = os.environ["PAUL_PHONE"]
ART_PHONE = os.environ["ART_PHONE"]
SUMMARY_EMAIL = os.environ["SUMMARY_EMAIL"]

greeting = "Hi, this is Kitchen Design. How can I help you today?"

@app.route("/", methods=["GET"])
def home():
    return "Kitchen AI is live!"

@app.route("/call", methods=["POST"])
def call():
    response = VoiceResponse()
    gather = Gather(input="speech", action="/transcription", method="POST", timeout=5)
    gather.say(greeting)
    response.append(gather)
    response.redirect("/call")
    return str(response)

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("SpeechResult", "").lower()
    reply, is_lead, transfer_number = generate_reply_and_lead_flag(transcript)

    response = VoiceResponse()
    if transfer_number:
        response.say("Transferring you now.")
        dial = Dial()
        dial.number(transfer_number)
        response.append(dial)
    else:
        gather = Gather(input="speech", action="/transcription", method="POST", timeout=5)
        gather.say(reply)
        response.append(gather)
        response.redirect("/call")

    send_summary_email(transcript, reply, is_lead)
    return str(response)

def generate_reply_and_lead_flag(message):
    is_lead = any(keyword in message for keyword in ["lead", "kitchen", "interested", "quote", "estimate", "remodel", "job", "cabinet"])
    transfer_number = None

    if "paul" in message:
        transfer_number = PAUL_PHONE
    elif "art" in message:
        transfer_number = ART_PHONE
    elif "jayson" in message or is_lead:
        transfer_number = JAYSON_PHONE

    prompt = f"You are a friendly receptionist at a kitchen cabinet company. Respond to this customer query naturally:\n\nCustomer: {message}\nReceptionist:"
    chat = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = chat.choices[0].message.content.strip()
    return reply, is_lead, transfer_number

def send_summary_email(transcript, reply, is_lead):
    subject = "📞 New AI Call Summary"
    body = f"Transcript:\n{transcript}\n\nAI Reply:\n{reply}\n\nLead Detected: {is_lead}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = SUMMARY_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print("Email send failed:", e)
