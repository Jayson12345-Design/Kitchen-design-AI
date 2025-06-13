import os
from flask import Flask, request, Response
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse, Say, Dial
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Load environment variables
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TWILIO_NUMBER = os.environ["TWILIO_NUMBER"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]
JAYSON_PHONE = os.environ["JAYSON_PHONE"]
PAUL_PHONE = os.environ["PAUL_PHONE"]
ART_PHONE = os.environ["ART_PHONE"]
MODEL_VERSION = os.environ.get("MODEL_VERSION", "gpt-4")

client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/voice", methods=["POST"])
def voice():
    call_sid = request.form.get("CallSid")
    transcript = request.form.get("SpeechResult")
    caller_number = request.form.get("From")

    print(f"Transcript: {transcript}")

    response = VoiceResponse()

    if not transcript:
        response.say("Hi, this is Kitchen Design. How can I help you today?", voice='alice')
        return Response(str(response), mimetype="text/xml")

    # Forward call based on keywords
    message = transcript.lower()
    is_lead = any(keyword in message for keyword in ["lead", "kitchen", "interested", "quote", "estimate"])
    wants_jayson = "jayson" in message or "talk to someone" in message or "speak to someone" in message
    wants_paul = "paul" in message
    wants_art = "art" in message

    if MODEL_VERSION == "gpt-3.5":
        response_obj = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're a helpful receptionist for a kitchen design company."},
                {"role": "user", "content": message}
            ]
        )
        ai_reply = response_obj.choices[0].message.content.strip()
    else:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're a helpful receptionist for a kitchen design company."},
                {"role": "user", "content": message}
            ]
        )
        ai_reply = completion.choices[0].message.content.strip()

    # Call routing
    if wants_jayson or is_lead:
        dial = Dial(callerId=TWILIO_NUMBER)
        dial.number(JAYSON_PHONE)
        response.say("Transferring you now.", voice='alice')
        response.append(dial)
    elif wants_paul:
        dial = Dial(callerId=TWILIO_NUMBER)
        dial.number(PAUL_PHONE)
        response.say("Transferring you to Paul now.", voice='alice')
        response.append(dial)
    elif wants_art:
        dial = Dial(callerId=TWILIO_NUMBER)
        dial.number(ART_PHONE)
        response.say("Transferring you to Art now.", voice='alice')
        response.append(dial)
    else:
        response.say(ai_reply, voice='alice')
        send_email_summary(caller_number, transcript, ai_reply)

    return Response(str(response), mimetype="text/xml")

def send_email_summary(caller_number, transcript, ai_reply):
    msg = MIMEText(f"Call from: {caller_number}\n\nTranscript: {transcript}\n\nAI Response: {ai_reply}")
    msg['Subject'] = "Kitchen Design - Call Summary"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    app.run(debug=True)
