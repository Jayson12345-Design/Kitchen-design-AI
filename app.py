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

def generate_reply_and_lead_flag(transcript):
    system_prompt = (
        "You are an AI receptionist for a kitchen remodeling business. "
        "Analyze the message below. Respond professionally and briefly. "
        "Also determine if the caller is a LEAD (interested in getting a kitchen done). "
        "Reply in JSON format with two fields: 'reply' and 'is_lead' (true/false)."
    )
    user_prompt = f"Customer said: '{transcript}'"
    
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format="json"
    )

    reply_json = chat.choices[0].message.content
    import json
    result = json.loads(reply_json)
    return result["reply"], result["is_lead"]

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
    reply, is_lead = generate_reply_and_lead_flag(transcript)

    email_body = f"📞 Call from: {caller}\n\n📝 Transcript:\n{transcript}\n\n🤖 AI Reply:\n{reply}\n\nLead: {is_lead}"
    send_email("Kitchen Design Call Summary", email_body)

    if is_lead:
        return Response("""
            <Response>
                <Redirect method="POST">https://kitchen-design-ai-1.onrender.com/transfer</Redirect>
            </Response>
        """, mimetype="text/xml")
    else:
        encoded = urllib.parse.quote(reply)
        return Response(f"""
            <Response>
                <Redirect method="POST">https://kitchen-design-ai-1.onrender.com/response?msg={encoded}</Redirect>
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

@app.route("/transfer", methods=["POST"])
def transfer():
    return Response("""
        <Response>
            <Say voice="Polly.Nicole">One moment while I transfer you to Jayson.</Say>
            <Dial>+19076060669</Dial>
        </Response>
    """, mimetype="text/xml")
