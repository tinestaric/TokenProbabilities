from flask import Flask, render_template, request, Response, stream_with_context
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_MODEL = "llama3.1:8b-text-q4_K_M"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_KEEP_ALIVE_WARM = "2h"  # covers a full 45-90min session plus setup buffer; regular /stream calls omit keep_alive, so Ollama's normal 5m default takes back over once generation starts

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html', ollama_controls=True)

@app.route('/model/warmup', methods=['POST'])
def warmup():
    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={'model': OLLAMA_MODEL, 'keep_alive': OLLAMA_KEEP_ALIVE_WARM}
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error in warmup: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/model/shutdown', methods=['POST'])
def shutdown():
    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={'model': OLLAMA_MODEL, 'keep_alive': 0}
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error in shutdown: {str(e)}")
        return {'error': str(e)}, 500

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
            response = requests.post(
                OLLAMA_GENERATE_URL,
                json={
                    'model': OLLAMA_MODEL,
                    'prompt': normalized_text,
                    'raw': True,
                    'stream': True,
                    'logprobs': True,
                    'top_logprobs': 10,
                    'options': {
                        'temperature': temperature,
                        'num_predict': max_tokens
                    }
                },
                stream=True
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get('response')
                if not content:
                    continue

                logprobs = {}
                for token_logprob in chunk.get('logprobs') or []:
                    alternatives = {
                        str(top['token']): float(top['logprob'])
                        for top in token_logprob.get('top_logprobs', [])
                    }
                    logprobs[str(token_logprob['token'])] = alternatives

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
    app.run(debug=True, port=5001)
