import { elements } from './elements.js';
import { tooltipManager } from './tooltipManager.js';

export const tokenManager = {
    appendToken(data, insertionRange) {
        const tokenSpan = this.createTokenSpan(data);
        this.attachTokenEvents(tokenSpan);
        this.insertToken(tokenSpan, insertionRange);
    },

    createTokenSpan(data) {
        const tokenSpan = document.createElement('span');
        tokenSpan.className = 'token';
        tokenSpan.textContent = data.token;
        tokenSpan.dataset.probabilities = JSON.stringify(data.probabilities);
        
        if (data.probabilities && Object.keys(data.probabilities).length > 0) {
            this.applyProbabilityStyles(tokenSpan, data.probabilities);
        }
        
        return tokenSpan;
    },

    applyProbabilityStyles(tokenSpan, probabilities) {
        const [currentToken, alternatives] = Object.entries(probabilities)[0];
        const currentProb = this.calculateProbability(currentToken, alternatives);
        const color = this.calculateColor(currentProb);
        
        tokenSpan.style.setProperty('--probability-color', color);
        tokenSpan.dataset.probability = currentProb;
    },

    calculateProbability(currentToken, alternatives) {
        if (currentToken in alternatives) {
            const logprob = alternatives[currentToken];
            return Math.min(100, Math.max(0, Math.exp(logprob) * 100));
        }
        return 0;
    },

    calculateColor(probability) {
        const hue = Math.round((probability / 100) * 140);
        const saturation = 85 + (probability / 100) * 15;
        const lightness = 70 - (probability / 100) * 20;
        const alpha = 0.3 + (probability / 100) * 0.1;
        return `hsla(${hue}, ${saturation}%, ${lightness}%, ${alpha})`;
    },

    attachTokenEvents(tokenSpan) {
        tokenSpan.addEventListener('mouseover', tooltipManager.showTooltip);
        tokenSpan.addEventListener('mouseout', tooltipManager.hideTooltip);
        tokenSpan.addEventListener('mousemove', tooltipManager.moveTooltip);
    },

    insertToken(tokenSpan, insertionRange) {
        insertionRange.insertNode(tokenSpan);
        insertionRange.setStartAfter(tokenSpan);
        insertionRange.collapse(true);
    }
};