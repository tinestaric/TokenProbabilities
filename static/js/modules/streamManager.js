import { elements } from './elements.js';
import { textProcessor } from './controls.js';
import { tokenManager } from './tokenManager.js';

export const streamManager = {
    async startStreaming() {
        const selection = window.getSelection();
        const range = selection.getRangeAt(0);
        const insertionPoint = range.endContainer;
        elements.loading.style.display = 'block';
        
        try {
            const response = await fetch('/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: textProcessor.prepareText(elements.textContent.innerText),
                    temperature: parseFloat(elements.temperatureInput.value),
                    maxTokens: parseInt(elements.maxTokens.value)
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            await this.processStreamResponse(response, insertionPoint);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            elements.loading.style.display = 'none';
        }
    },

    async processStreamResponse(response, insertionPoint) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let isFirstToken = true;

        const insertionRange = document.createRange();
        insertionRange.setStartAfter(insertionPoint);
        insertionRange.collapse(true);

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value);
                const lines = buffer.split('\n\n');
                buffer = lines.pop();

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            tokenManager.appendToken(data, insertionRange);
                        } catch (e) {
                            console.error('Error parsing JSON:', e, line);
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Error processing stream:', error);
        }
    }
};