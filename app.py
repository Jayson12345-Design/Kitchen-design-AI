from flask import Flask, request, Response
import openai
import os
import smtplib
from email.mime.text import MIMEText
import urllib.parse

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

def generate_reply(transcript):
    prompt = (
        f"You are a helpful receptionist at Kitchen Design. A customer said: '{transcript}'. "
        "Reply in a helpful, friendly tone without repeating a greeting."
    )
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content.strip()

@app.route("/call", methods=["POST"])
def call():
    return Response("""
        <Response>
            <Say voice="Polly.Nicole">Hi, this is Kitchen Design. How can I help you today?</Say>
            <Record maxLength="30" transcribe="true" transcribeCallback="https://kitchen-design-ai-1.onrender.com/transcription" />
        </Response>
    """, mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("TranscriptionText", "").strip()
    caller = request.form.get("From", "Unknown")
    ai_reply = generate_reply(transcript)

    email_body = f"📞 Call from: {caller}\n\n📝 Transcript:\n{transcript}\n\n🤖 AI Reply:\n{ai_reply}"
    send_email("Kitchen Design Call Summary", email_body)

    # Encode the reply to pass it safely in the URL
    encoded_reply = urllib.parse.quote(ai_reply)
    return Response(f"""
        <Response>
            <Redirect method="POST">https://kitchen-design-ai-1.onrender.com/response?msg={encoded_reply}</Redirect>
        </Response>
    """, mimetype="text/xml")

@app.route("/response", methods=["POST"])
def response():
    ai_reply = request.args.get("msg", "Thank you. We'll be in touch.")
    return Response(f"""
        <Response>
            <Say voice="Polly.Nicole">{ai_reply}</Say>
            <Hangup/>
        </Response>
    """, mimetype="text/xml")
