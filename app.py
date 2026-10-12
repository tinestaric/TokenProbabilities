from flask import Flask, render_template, request, Response, stream_with_context
import requests
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_MODEL = "llama3.1:8b-text-q4_K_M"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_PS_URL = "http://localhost:11434/api/ps"
OLLAMA_KEEP_ALIVE_WARM = "2h"  # covers a full 45-90min session plus setup buffer; regular /stream calls omit keep_alive, so Ollama's normal 5m default takes back over once generation starts

OPENAI_MODEL = "gpt-5.4-nano"
OPENAI_SYSTEM_PROMPT = (
    "You are a text-continuation engine. Continue the user's text exactly where it leaves off, "
    "mid-sentence if necessary. Output only the continuation: no preamble, no quotes, "
    "and do not repeat the user's text."
)

load_dotenv(Path(__file__).parent / '.env', override=True)
_openai_client = None

def get_openai_client():
    # Created lazily so the Ollama-only flow works without an OpenAI key
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    return _openai_client

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html', ollama_controls=True)

@app.route('/model/status', methods=['GET'])
def model_status():
    try:
        resp = requests.get(OLLAMA_PS_URL, timeout=5)
        resp.raise_for_status()
        for m in resp.json().get('models', []):
            if m.get('name') == OLLAMA_MODEL or m.get('model') == OLLAMA_MODEL:
                return {'loaded': True, 'expires_at': m.get('expires_at')}
        return {'loaded': False}
    except Exception as e:
        logger.error(f"Error in model_status: {str(e)}")
        return {'error': str(e)}, 500

def ollama_is_up():
    try:
        requests.get(OLLAMA_PS_URL, timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False

def ensure_ollama_running(timeout=30):
    """Start `ollama serve` in the background if nothing is listening, then wait until it answers."""
    if ollama_is_up():
        return
    exe = shutil.which('ollama')
    if not exe:
        raise RuntimeError("Ollama is not running and the 'ollama' executable was not found on PATH")
    logger.info("Ollama not reachable, starting 'ollama serve'")
    flags = 0
    if os.name == 'nt':
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe, 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, creationflags=flags)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ollama_is_up():
            return
        time.sleep(0.5)
    raise RuntimeError(f"Started 'ollama serve' but it did not respond within {timeout}s")

@app.route('/model/warmup', methods=['POST'])
def warmup():
    try:
        ensure_ollama_running()
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
    provider = request.json.get('provider', 'ollama')

    if not normalized_text:
        return Response('No input text provided', status=400)

    def generate_openai():
        stream = None
        try:
            stream = get_openai_client().chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {'role': 'system', 'content': OPENAI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': normalized_text}
                ],
                max_completion_tokens=max_tokens,
                temperature=temperature,
                logprobs=True,
                top_logprobs=5,  # gpt-5.4-nano rejects anything above 5
                stream=True
            )

            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                content = choice.delta.content
                if not content:
                    continue

                logprobs = {}
                if choice.logprobs and choice.logprobs.content:
                    for token_logprob in choice.logprobs.content:
                        logprobs[token_logprob.token] = {
                            top.token: float(top.logprob)
                            for top in token_logprob.top_logprobs
                        }

                yield f"data: {json.dumps({'token': content, 'probabilities': logprobs})}\n\n"

        except Exception as e:
            logger.error(f"Error in OpenAI stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Runs when the client stops generation, so the upstream request is cancelled too
            if stream is not None:
                stream.close()

    def generate():
        response = None
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
        finally:
            if response is not None:
                response.close()

    source = generate_openai if provider == 'openai' else generate
    return Response(stream_with_context(source()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
