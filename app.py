from flask import Flask, request, Response
import openai
import os
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import json

app = Flask(__name__)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASS)
        smtp.send_message(msg)

def generate_reply_and_lead_flag(transcript):
    system_prompt = (
        "You are a smart receptionist for a kitchen remodeling company. "
        "If the caller sounds like a lead (interested in getting a kitchen done), respond with JSON: "
        '{"reply": "...", "is_lead": true}. If not a lead, use is_lead: false. Respond only in JSON.'
    )
    user_prompt = f"Caller said: {transcript}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format="json"
    )
    try:
        reply_data = json.loads(response.choices[0].message.content.strip())
        return reply_data["reply"], reply_data["is_lead"]
    except Exception as e:
        print("Failed to parse AI response:", e)
        return "Sorry, I didn't catch that. Can you please repeat?", False

@app.route("/call", methods=["POST"])
def call():
    return Response("""
        <Response>
            <Say voice="Polly.Nicole">Hi, this is Kitchen Design. How can I help you today?</Say>
            <Record maxLength="30" transcribe="true" transcribeCallback="/transcription" />
        </Response>
    """, mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("TranscriptionText", "").strip()
    caller = request.form.get("From", "Unknown")
    print("Transcript:", transcript)

    reply, is_lead = generate_reply_and_lead_flag(transcript)

    email_body = f"📞 Call from: {caller}\n\n📝 Transcript:\n{transcript}\n\n🤖 AI Reply:\n{reply}\n\nLead: {is_lead}"
    send_email("Kitchen Design Call Summary", email_body)

    if is_lead:
        return Response("""
            <Response>
                <Say voice="Polly.Nicole">Transferring you to Jayson now.</Say>
                <Dial>+19076060669</Dial>
            </Response>
        """, mimetype="text/xml")

    encoded = urllib.parse.quote(reply)
    return Response(f"""
        <Response>
            <Redirect method="POST">/respond?msg={encoded}</Redirect>
        </Response>
    """, mimetype="text/xml")

@app.route("/respond", methods=["POST"])
def respond():
    ai_reply = request.args.get("msg", "Thanks! How else can I help?")
    return Response(f"""
        <Response>
            <Say voice="Polly.Nicole">{ai_reply}</Say>
            <Redirect method="POST">/call</Redirect>
        </Response>
    """, mimetype="text/xml")

@app.route("/", methods=["GET"])
def index():
    return "✅ AI receptionist is running."
