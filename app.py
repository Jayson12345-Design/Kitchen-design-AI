from flask import Flask, request, Response
import openai
import os

app = Flask(__name__)

# Initialize the OpenAI client with your API key from the environment
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
FORWARD_NUMBER = os.getenv("FORWARD_NUMBER", "+19076060669")

def generate_ai_response(transcript):
    # If no transcript text was captured, return a fallback message
    if not transcript.strip():
        return "I'm sorry, I didn't catch that. Could you please repeat your message?"
    
    # Build a prompt that instructs GPT not to repeat the greeting and to provide a concise helpful reply.
    prompt = (
        f"You are a receptionist at Kitchen Design. "
        f"A customer said: '{transcript}'. "
        "Please provide a clear, brief, and helpful response, and do not repeat any greeting."
    )
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content

@app.route("/call", methods=["POST"])
def call():
    # This TwiML tells Twilio to greet the caller and record a message that it will transcribe.
    response = """
    <Response>
        <Say voice="Polly.Nicole">Hi, this is Kitchen Design. How can I help you today?</Say>
        <Record maxLength="30" transcribe="true" transcribeCallback="/transcription" />
    </Response>
    """
    return Response(response, mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    # Grab the transcription text from Twilio's POST data.
    transcript = request.form.get("TranscriptionText", "").strip().lower()
    caller = request.form.get("From")
    print("Transcript:", transcript)  # This will appear in Render logs for debugging.
    
    # If the transcript indicates the caller wants to speak to someone, forward the call.
    if "talk to" in transcript or "speak to" in transcript or "real person" in transcript:
        response = f"""
        <Response>
            <Say voice="Polly.Nicole">Sure, connecting you to someone now.</Say>
            <Dial>{FORWARD_NUMBER}</Dial>
        </Response>
        """
    else:
        # Otherwise, generate an AI reply based on the transcript.
        ai_reply = generate_ai_response(transcript)
        response = f"""
        <Response>
            <Say voice="Polly.Nicole">{ai_reply}</Say>
        </Response>
        """
    return Response(response, mimetype="text/xml")
