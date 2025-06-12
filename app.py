import os
import json
import smtplib
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
from email.message import EmailMessage
import urllib.parse

app = Flask(__name__)

# Initialize OpenAI client (no proxies arg)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Environment variables
FORWARD_NUMBER = os.environ["FORWARD_NUMBER"]
EMAIL_TO       = os.environ["EMAIL_TO"]
EMAIL_FROM     = os.environ["EMAIL_FROM"]
EMAIL_PASS     = os.environ["EMAIL_PASS"]

@app.route("/", methods=["GET"])
def index():
    return "Kitchen Design AI receptionist is running."

@app.route("/call", methods=["POST"])
def call():
    resp = VoiceResponse()
    # Gather speech input
    gather = Gather(
        input="speech",
        action="/transcription",
        method="POST",
        timeout=3
    )
    gather.say(
        "Hi, this is Kitchen Design. How can I help you today?",
        voice="Polly.Nicole",
        language="en-AU"
    )
    resp.append(gather)
    # If no speech, repeat
    resp.redirect("/call")
    return Response(str(resp), mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("SpeechResult", "").strip()
    caller     = request.form.get("From", "Unknown")
    print("Transcript:", transcript)

    # Ask OpenAI to reply and flag as lead or not
    reply, is_lead = generate_reply_and_lead_flag(transcript)

    # Send you an email summary
    send_email_summary(caller, transcript, reply, is_lead)

    resp = VoiceResponse()
    if is_lead:
        resp.say("Transferring you now.", voice="Polly.Nicole", language="en-AU")
        dial = Dial()
        dial.number(FORWARD_NUMBER)
        resp.append(dial)
    else:
        # Speak the AI reply and loop back
        gather = Gather(
            input="speech",
            action="/transcription",
            method="POST",
            timeout=3
        )
        gather.say(reply, voice="Polly.Nicole", language="en-AU")
        resp.append(gather)
        resp.redirect("/call")

    return Response(str(resp), mimetype="text/xml")

def generate_reply_and_lead_flag(transcript):
    system_prompt = (
        "You are a receptionist for a kitchen remodeling business.  "
        "If the caller is a lead (interested in a kitchen remodel, quote, or consultation), "
        "respond in JSON: {\"reply\": \"…\", \"is_lead\": true}.  "
        "Otherwise respond {\"reply\": \"…\", \"is_lead\": false}.  "
        "Do not include any extra text."
    )
    messages = [
        {"role": "system",  "content": system_prompt},
        {"role": "user",    "content": f"Caller said: {transcript}"}
    ]
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    raw = chat.choices[0].message.content
    try:
        data = json.loads(raw.strip())
        return data["reply"], data["is_lead"]
    except Exception as e:
        print("Failed to parse AI JSON:", e, "raw:", raw)
        return "Sorry, I didn't catch that. Could you repeat?", False

def send_email_summary(caller, transcript, ai_reply, is_lead):
    msg = EmailMessage()
    msg["Subject"] = "📞 New Kitchen Design Call Summary"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.set_content(
        f"Caller: {caller}\n\n"
        f"Transcript:\n{transcript}\n\n"
        f"AI Reply:\n{ai_reply}\n\n"
        f"Lead: {is_lead}"
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASS)
            smtp.send_message(msg)
        print("Email sent.")
    except Exception as e:
        print("Email send failed:", e)

if __name__ == "__main__":
    # local debug
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
