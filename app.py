import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Set up environment variables
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
FORWARD_NUMBER = os.environ["FORWARD_NUMBER"]
EMAIL_TO = os.environ["EMAIL_TO"]
PAUL_NUMBER = os.environ.get("PAUL_NUMBER")
ART_NUMBER = os.environ.get("ART_NUMBER")
JAYSON_NUMBER = os.environ.get("JAYSON_NUMBER")

@app.route("/", methods=["GET"])
def index():
    return "AI Call System is running"

@app.route("/call", methods=["POST"])
def call():
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/transcription",
        speechTimeout="auto"
    )
    gather.say("Hi, this is Kitchen Design. How can I help you today?", voice="Polly.Nicole", language="en-AU")
    response.append(gather)
    response.redirect("/call")  # Loop in case no speech input
    return Response(str(response), mimetype="application/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("SpeechResult", "").strip()
    print("Transcript:", transcript)

    if not transcript:
        return redirect_back()

    reply, is_lead, transfer_to = generate_reply_and_lead_flag(transcript)
    print("AI Reply:", reply)

    if transfer_to:
        response = VoiceResponse()
        response.say(f"Transferring you to {transfer_to['name']}. Please hold.", voice="Polly.Nicole", language="en-AU")
        dial = Dial()
        dial.number(transfer_to["number"])
        response.append(dial)
        return Response(str(response), mimetype="application/xml")

    if is_lead:
        response = VoiceResponse()
        response.say("Please hold while I transfer you to someone who can help.", voice="Polly.Nicole", language="en-AU")
        dial = Dial()
        dial.number(FORWARD_NUMBER)
        response.append(dial)
    else:
        response = VoiceResponse()
        response.say(reply, voice="Polly.Nicole", language="en-AU")
        response.redirect("/call")

    send_email_summary(transcript, reply, is_lead)
    return Response(str(response), mimetype="application/xml")

def redirect_back():
    response = VoiceResponse()
    response.redirect("/call")
    return Response(str(response), mimetype="application/xml")

def generate_reply_and_lead_flag(message):
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a polite receptionist for a Sarasota-based cabinet company called Kitchen Design."},
            {"role": "user", "content": message}
        ]
    )
    reply = completion.choices[0].message.content.strip()

    # Determine if it's a lead or specific person request
    lowered = message.lower()
    transfer_to = None
    if "paul" in lowered:
        transfer_to = {"name": "Paul", "number": PAUL_NUMBER}
    elif "art" in lowered:
        transfer_to = {"name": "Art", "number": ART_NUMBER}
    elif "jayson" in lowered:
        transfer_to = {"name": "Jayson", "number": JAYSON_NUMBER}

    lead_keywords = ["kitchen", "cabinet", "quote", "estimate", "interested", "remodel", "design"]
    is_lead = any(kw in lowered for kw in lead_keywords)

    return reply, is_lead, transfer_to

def send_email_summary(transcript, reply, is_lead):
    subject = "New AI Call Summary"
    body = f"Transcript: {transcript}\n\nAI Response: {reply}\n\nLead: {'Yes' if is_lead else 'No'}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("Email summary sent.")
    except Exception as e:
        print("Email send failed:", str(e))

if __name__ == "__main__":
    app.run(debug=True)
