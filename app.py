import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

YOUR_PHONE = os.environ.get("FORWARD_TO")  # Your number to forward leads to
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

@app.route("/", methods=["GET"])
def index():
    return "Kitchen Design AI is running."

@app.route("/call", methods=["POST"])
def call():
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/transcription",
        speech_timeout="auto",
        method="POST"
    )
    gather.say("Hi, this is Kitchen Design. How can I help you today?", voice="Polly.Nicole", language="en-AU")
    response.append(gather)
    response.redirect("/call")  # Loop if no input
    return Response(str(response), mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.values.get("SpeechResult", "")
    print("Transcript:", transcript)

    if not transcript.strip():
        return redirect_to_call()

    reply, is_lead, contact_person = get_reply(transcript)
    send_email_summary(transcript, reply)

    if contact_person:
        return transfer_call(contact_person)

    if is_lead:
        return transfer_call(YOUR_PHONE)

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/transcription",
        speech_timeout="auto",
        method="POST"
    )
    gather.say(reply, voice="Polly.Nicole", language="en-AU")
    response.append(gather)
    response.redirect("/call")
    return Response(str(response), mimetype="text/xml")

def get_reply(transcript):
    system_prompt = (
        "You are a friendly receptionist for Kitchen Design. "
        "Determine if this is a potential customer interested in kitchen work. "
        "Also detect if they ask for Jayson, Art, or Paul by name."
    )
    chat = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ]
    )
    message = chat.choices[0].message.content.lower()

    is_lead = any(keyword in message for keyword in ["lead", "kitchen-related", "interested", "quote", "estimate"])
    contact_person = None
    if "art" in message:
        contact_person = os.environ.get("PHONE_ART")
    elif "paul" in message:
        contact_person = os.environ.get("PHONE_PAUL")
    elif "jayson" in message:
        contact_person = os.environ.get("PHONE_JAYSON")

    return chat.choices[0].message.content.strip(), is_lead, contact_person

def transfer_call(number):
    response = VoiceResponse()
    dial = Dial()
    dial.number(number)
    response.append(dial)
    return Response(str(response), mimetype="text/xml")

def redirect_to_call():
    response = VoiceResponse()
    response.redirect("/call")
    return Response(str(response), mimetype="text/xml")

def send_email_summary(transcript, reply):
    body = f"Transcript:\n{transcript}\n\nAI Reply:\n{reply}"
    msg = MIMEText(body)
    msg["Subject"] = "📞 New Kitchen Design Call"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
    except Exception as e:
        print("Failed to send email:", e)

if __name__ == "__main__":
    app.run(debug=True)
