import { elements } from './modules/elements.js';
import { temperatureControl, textProcessor } from './modules/controls.js';
import { streamManager } from './modules/streamManager.js';

function init() {
    temperatureControl.init();
    
    // Add event listener for generate button
    const generateButton = document.getElementById('generateButton');
    if (generateButton) {
        generateButton.addEventListener('click', () => streamManager.startStreaming());
    }
}

// Start the application
init();