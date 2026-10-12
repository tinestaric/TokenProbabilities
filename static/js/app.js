import { elements } from './modules/elements.js';
import { temperatureControl, textProcessor } from './modules/controls.js';
import { streamManager } from './modules/streamManager.js';
import { tooltipManager } from './modules/tooltipManager.js';

function init() {
    temperatureControl.init();
    tooltipManager.init();
    
    // Add event listener for generate button
    const generateButton = document.getElementById('generateButton');
    if (generateButton) {
        generateButton.addEventListener('click', () => streamManager.toggleStreaming());
    }
}

// Start the application
init();