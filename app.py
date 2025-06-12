from flask import Flask, request, Response
import openai
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
FORWARD_NUMBER = os.getenv("FORWARD_NUMBER", "+19076060669")
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

def generate_ai_decision(transcript):
    prompt = (
        f"You are an AI receptionist at Kitchen Design. A customer said: '{transcript}'. "
        "Determine the intent of the caller. If it sounds like they are asking about a kitchen remodel, cabinets, or requesting service, "
        "respond with 'forward'. Otherwise, respond with 'email'. Only say 'forward' or 'email'."
    )
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content.strip().lower()

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
    response = """
    <Response>
        <Say voice="Polly.Nicole">Hi, this is Kitchen Design. How can I help you today?</Say>
        <Record maxLength="30" transcribe="true" transcribeCallback="/transcription" />
    </Response>
    """
    return Response(response, mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("TranscriptionText", "").strip()
    caller = request.form.get("From", "Unknown")
    decision = generate_ai_decision(transcript)

    if decision == "forward":
        response = f"""
        <Response>
            <Say voice="Polly.Nicole">Great, connecting you now.</Say>
            <Dial>{FORWARD_NUMBER}</Dial>
        </Response>
        """
    else:
        ai_reply = generate_reply(transcript)
        email_body = f"📞 Call from: {caller}

📝 Transcript:
{transcript}

🤖 AI Reply:
{ai_reply}"
        send_email("Kitchen Design Call Summary", email_body)
        response = f"""
        <Response>
            <Say voice="Polly.Nicole">{ai_reply}</Say>
            <Hangup/>
        </Response>
        """
    return Response(response, mimetype="text/xml")
