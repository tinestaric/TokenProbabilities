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
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=normalized_text,
                max_tokens=max_tokens,
                temperature=temperature,
                logprobs=10,
                stream=True
            )

            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'text') and chunk.choices[0].text:
                    content = chunk.choices[0].text
                    logprobs = {}
                    
                    if hasattr(chunk.choices[0], 'logprobs') and chunk.choices[0].logprobs and hasattr(chunk.choices[0].logprobs, 'top_logprobs'):
                        token_idx = 0
                        for token_logprobs in chunk.choices[0].logprobs.top_logprobs:
                            if token_logprobs:
                                token = chunk.choices[0].logprobs.tokens[token_idx] if hasattr(chunk.choices[0].logprobs, 'tokens') else f"token_{token_idx}"
                                alternatives = {}
                                for token_text, logprob in token_logprobs.items():
                                    alternatives[str(token_text)] = float(logprob)
                                logprobs[str(token)] = alternatives
                            token_idx += 1
                    
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