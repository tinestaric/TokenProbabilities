import { elements } from './elements.js';
import { textProcessor } from './controls.js';
import { tokenManager } from './tokenManager.js';

export const streamManager = {
    resolveInsertionRange() {
        const selection = window.getSelection();
        const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
        const endContainer = range ? range.endContainer : null;

        // Fall back to the end of the text box whenever there's no selection, the
        // caret is on the text box itself (e.g. it's empty), or the caret is outside
        // the text box entirely (e.g. left in the Temperature input).
        if (!endContainer || endContainer === elements.textContent || !elements.textContent.contains(endContainer)) {
            const fallbackRange = document.createRange();
            fallbackRange.selectNodeContents(elements.textContent);
            fallbackRange.collapse(false);
            return fallbackRange;
        }

        const insertionRange = document.createRange();
        insertionRange.setStartAfter(endContainer);
        insertionRange.collapse(true);
        return insertionRange;
    },

    async startStreaming() {
        elements.loading.style.display = 'block';

        try {
            const insertionRange = this.resolveInsertionRange();
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

            await this.processStreamResponse(response, insertionRange);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            elements.loading.style.display = 'none';
        }
    },

    async processStreamResponse(response, insertionRange) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let isFirstToken = true;

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