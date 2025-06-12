from flask import Flask, request, Response

app = Flask(__name__)

@app.route("/call", methods=["POST"])
def call():
    response = """
    <Response>
        <Say voice="Polly.Nicole">Hi, this is Kitchen Design. How can I help you today?</Say>
        <Record maxLength="30" transcribe="true" transcribeCallback="https://kitchen-design-ai-1.onrender.com/transcription" />
    </Response>
    """
    return Response(response, mimetype="text/xml")

@app.route("/transcription", methods=["POST"])
def transcription():
    transcript = request.form.get("TranscriptionText", "").strip()
    print("Transcript:", transcript)

    return Response("""
        <Response>
            <Say voice="Polly.Nicole">Thanks! We'll get back to you shortly.</Say>
            <Hangup/>
        </Response>
    """, mimetype="text/xml")
