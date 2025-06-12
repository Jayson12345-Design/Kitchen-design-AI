from flask import Flask, request, Response

app = Flask(__name__)

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
    return Response("""
        <Response>
            <Hangup/>
        </Response>
    """, mimetype="text/xml")
