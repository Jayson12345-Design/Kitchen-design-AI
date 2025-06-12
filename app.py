from flask import Flask, request, Response
import openai
import os

app = Flask(__name__)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
FORWARD_NUMBER = os.getenv("FORWARD_NUMBER", "+19076060669")

def generate_ai_response(transcript):
    prompt = f"You are a receptionist at Kitchen Design. A customer says: '{transcript}'. How do you respond?"
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content

@app.route("/call", methods=["POST"])
def call():
    response = """
    <Response>
        <Say voice="alice">Hi, this is Kitchen Design. How can I help you today?</Say>
        <Record maxLength="30" transcribe="true" transcribeCallback="/transcription" />
    </Response>
    """
    return Response(response, mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("TranscriptionText", "").lower()
    caller = request.form.get("From")

    if "talk to" in transcript or "speak to" in transcript or "real person" in transcript:
        response = f"""
        <Response>
            <Say voice="alice">Sure, connecting you to someone now.</Say>
            <Dial>{FORWARD_NUMBER}</Dial>
        </Response>
        """
    else:
        ai_reply = generate_ai_response(transcript)
        response = f"""
        <Response>
            <Say voice="alice">{ai_reply}</Say>
        </Response>
        """

    return Response(response, mimetype="text/xml")
