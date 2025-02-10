import { elements } from './elements.js';

export const temperatureControl = {
    init() {
        elements.temperatureSlider.addEventListener('input', (e) => {
            elements.temperatureInput.value = e.target.value;
        });

        elements.temperatureInput.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            if (value >= 0 && value <= 2) {
                elements.temperatureSlider.value = value;
            }
        });
    }
};

export const textProcessor = {
    prepareText(text) {
        return text
            .replace(/[\r\n]+/g, ' ')  // Replace line breaks with spaces
            .trim();                    // Remove all whitespace from both ends
    }
};