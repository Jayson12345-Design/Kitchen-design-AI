import os
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
TRANSFER_NUMBERS = {
    "jayson": "+19076060669",
    "art": "+1xxxxxxxxxx",   # Replace with Art's number
    "paul": "+1xxxxxxxxxx"   # Replace with Paul's number
}

CALLER_LOG = {}

@app.route("/call", methods=["POST"])
def call():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/transcription', method='POST', timeout=5)
    gather.say("Hi, this is Kitchen Design. How can I help you today?", voice="Polly.Nicole", language="en-AU")
    response.append(gather)
    response.redirect('/call')
    return str(response)

@app.route("/transcription", methods=["POST"])
def transcription():
    call_sid = request.values.get("CallSid")
    caller = request.values.get("From")
    transcript = request.values.get("SpeechResult", "").strip()

    print(f"Transcript: {transcript}")

    if not transcript:
        return str(redirect_to_gather())

    reply, lead_type = generate_reply_and_lead_flag(transcript)

    # Store logs for later email
    CALLER_LOG.setdefault(call_sid, {"caller": caller, "log": []})
    CALLER_LOG[call_sid]["log"].append((transcript, reply))

    response = VoiceResponse()

    # Transfer logic
    if lead_type in TRANSFER_NUMBERS:
        response.say(f"Transferring you to {lead_type.capitalize()}", voice="Polly.Nicole", language="en-AU")
        response.dial(TRANSFER_NUMBERS[lead_type])
        return str(response)

    elif lead_type == "lead":
        response.say("Great! Let me transfer you to someone who can help.", voice="Polly.Nicole", language="en-AU")
        response.dial(TRANSFER_NUMBERS["jayson"])
        return str(response)

    else:
        gather = Gather(input='speech', action='/transcription', method='POST', timeout=5)
        gather.say(reply, voice="Polly.Nicole", language="en-AU")
        response.append(gather)
        response.redirect('/call')
        return str(response)

@app.route("/hangup", methods=["POST"])
def hangup():
    call_sid = request.values.get("CallSid")
    if call_sid in CALLER_LOG:
        caller = CALLER_LOG[call_sid]["caller"]
        logs = CALLER_LOG[call_sid]["log"]
        summary = "\n".join([f"User: {q}\nAI: {a}" for q, a in logs])
        email_summary(caller, summary)
    return ""

def generate_reply_and_lead_flag(transcript):
    messages = [
        {"role": "system", "content": "You're an assistant for a cabinet company. Help customers professionally."},
        {"role": "user", "content": transcript}
    ]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    reply = response.choices[0].message.content.strip().replace("\n", " ")

    lower = transcript.lower()
    if any(name in lower for name in TRANSFER_NUMBERS):
        for name in TRANSFER_NUMBERS:
            if name in lower:
                return reply, name
    elif any(word in lower for word in ["kitchen", "cabinets", "remodel", "quote", "design"]):
        return reply, "lead"
    else:
        return reply, None

def email_summary(caller, summary):
    subject = f"📞 Call Summary from {caller}"
    body = f"Caller: {caller}\n\nCall Transcript:\n{summary}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    except Exception as e:
        print(f"Email error: {e}")

def redirect_to_gather():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/transcription', method='POST', timeout=5)
    gather.say("I'm sorry, I didn't catch that. Can you please repeat?", voice="Polly.Nicole", language="en-AU")
    response.append(gather)
    response.redirect('/call')
    return response

@app.route("/", methods=["GET"])
def home():
    return "Kitchen Design AI Answering Service is running."

if __name__ == "__main__":
    app.run(debug=True)
