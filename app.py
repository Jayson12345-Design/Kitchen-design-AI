import os
import json
import smtplib
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
from email.message import EmailMessage

app = Flask(__name__)

# Setup OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Get environment variables
FORWARD_NUMBER = os.environ["FORWARD_NUMBER"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

@app.route("/", methods=["GET"])
def index():
    return "Kitchen Design AI is live!"

@app.route("/call", methods=["POST"])
def call():
    response = VoiceResponse()

    gather = Gather(
        input="speech",
        action="/transcription",
        method="POST",
        timeout=3
    )
    gather.say("Hi, this is Kitchen Design. How can I help you today?", voice="Polly.Nicole", language="en-AU")
    response.append(gather)
    response.redirect("/call")
    return Response(str(response), mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("SpeechResult", "").strip()
    caller = request.form.get("From", "Unknown")
    print("Transcript:", transcript)

    reply, is_lead = generate_reply_and_lead_flag(transcript)

    # Send email summary either way
    send_email_summary(caller, transcript, reply, is_lead)

    response = VoiceResponse()

    if is_lead:
        dial = Dial()
        dial.number(FORWARD_NUMBER)
        response.say("Transferring you now.", voice="Polly.Nicole", language="en-AU")
        response.append(dial)
    else:
        gather = Gather(
            input="speech",
            action="/transcription",
            method="POST",
            timeout=3
        )
        gather.say(reply, voice="Polly.Nicole", language="en-AU")
        response.append(gather)
        response.redirect("/call")

    return Response(str(response), mimetype="text/xml")

def generate_reply_and_lead_flag(transcript):
    system_prompt = (
        "You are a receptionist for a kitchen remodeling company. "
        "If the caller is a lead (wants a kitchen remodel, quote, or meeting), reply in JSON: "
        '{"reply": "say this to the caller", "is_lead": true}. '
        "If not a lead, use is_lead: false. Only reply in JSON format."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Caller said: {transcript}"}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    try:
        content = response.choices[0].message.content
        print("AI response:", content)
        parsed = json.loads(content)
        return parsed["reply"], parsed["is_lead"]
    except Exception as e:
        print("⚠️ Failed to parse AI response:", e)
        return "Sorry, could you say that again?", False

def send_email_summary(caller, transcript, ai_reply, is_lead):
    try:
        msg = EmailMessage()
        msg["Subject"] = "📞 New AI Call Summary"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg.set_content(
            f"Caller: {caller}\n\nTranscript:\n{transcript}\n\nAI Reply:\n{ai_reply}\n\nLead: {is_lead}"
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASS)
            smtp.send_message(msg)
        print("📧 Email sent.")
    except Exception as e:
        print("⚠️ Failed to send email:", e)

