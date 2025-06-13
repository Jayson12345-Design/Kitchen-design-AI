import os
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client as TwilioClient
from openai import OpenAI
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TWILIO_SID = os.environ["TWILIO_SID"]
TWILIO_AUTH = os.environ["TWILIO_AUTH"]
TWILIO_NUMBER = os.environ["TWILIO_NUMBER"]
JAYSON_PHONE = os.environ["JAYSON_PHONE"]
PAUL_PHONE = os.environ["PAUL_PHONE"]
ART_PHONE = os.environ["ART_PHONE"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
SUMMARY_EMAIL = os.environ["SUMMARY_EMAIL"]

twilio_client = TwilioClient(TWILIO_SID, TWILIO_AUTH)
client = OpenAI(api_key=OPENAI_API_KEY)

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = SUMMARY_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()
    gather = Gather(input="speech", timeout=3, speechTimeout="auto", action="/gather")
    gather.say("Hi, this is Kitchen Design. How can I help you today?")
    response.append(gather)
    response.redirect("/voice")
    return str(response)

@app.route("/gather", methods=["POST"])
def gather():
    response = VoiceResponse()
    speech_result = request.form.get("SpeechResult", "").lower()
    from_number = request.form.get("From")

    if "kitchen" in speech_result or "cabinet" in speech_result:
        response.say("Let me transfer you to someone who can help.")
        response.dial(JAYSON_PHONE)
        send_email("Lead Detected", f"Lead from {from_number}: {speech_result}")
    elif "paul" in speech_result:
        response.say("Transferring you to Paul now.")
        response.dial(PAUL_PHONE)
    elif "art" in speech_result or "architect" in speech_result:
        response.say("Transferring you to Art now.")
        response.dial(ART_PHONE)
    else:
        prompt = f"Customer: {speech_result}\nReceptionist:"
        try:
            chat_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You're a helpful receptionist for a custom cabinet company."},
                    {"role": "user", "content": speech_result}
                ],
                max_tokens=150,
            )
            reply = chat_response.choices[0].message.content.strip()
        except Exception as e:
            reply = "Sorry, I had trouble understanding that. Could you repeat it?"

        response.say(reply)
        response.redirect("/voice")
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)
