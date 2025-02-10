import os
from flask import Flask, render_template, request, Response, stream_with_context
from openai import OpenAI
from dotenv import load_dotenv
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
current_dir = Path(__file__).parent.absolute()
env_path = current_dir / '.env'
if 'OPENAI_API_KEY' in os.environ:
    del os.environ['OPENAI_API_KEY']
load_dotenv(dotenv_path=env_path, override=True)

app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/stream', methods=['POST'])
def stream():
    input_text = request.json.get('text', '')
    # Replace newlines with spaces and normalize multiple spaces
    normalized_text = ' '.join(input_text.split())
    temperature = request.json.get('temperature', 1.0)
    max_tokens = request.json.get('maxTokens', 500)

    if not normalized_text:
        return Response('No input text provided', status=400)

    def generate():
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "When completing a partial sentence, first complete the sentence naturally, then continue with several additional related sentences to expand on the theme. Be thorough and descriptive in your continuation."},
                    {"role": "user", "content": normalized_text}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                logprobs=True,
                top_logprobs=10,
                stream=True
            )

            for chunk in response:
                if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logprobs = {}
                    
                    if hasattr(chunk.choices[0], 'logprobs'):
                        for token in chunk.choices[0].logprobs.content:
                            alternatives = {}
                            for top_logprob in token.top_logprobs:
                                alternatives[str(top_logprob.token)] = float(top_logprob.logprob)
                            logprobs[str(token.token)] = alternatives
                    
                    data = {
                        'token': content,
                        'probabilities': logprobs
                    }
                    yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            logger.error(f"Error in stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)