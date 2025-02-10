import { elements } from './elements.js';

export const tooltipManager = {
    showTooltip(event) {
        const probabilities = JSON.parse(event.target.dataset.probabilities);
        const tooltipContent = tooltipManager.generateTooltipContent(probabilities);
        elements.tooltipDiv.innerHTML = tooltipContent;
        elements.tooltipDiv.style.display = 'block';
        tooltipManager.moveTooltip(event);
    },

    generateTooltipContent(probabilities) {
        let content = '<strong>Token Probabilities:</strong><br>';
        const [currentToken, alternatives] = Object.entries(probabilities)[0];
        const allProbs = { ...alternatives };

        if (!(currentToken in allProbs)) {
            content += tooltipManager.generateAlternativesList(allProbs, currentToken);
        } else {
            content += tooltipManager.generateFullProbabilitiesList(allProbs, currentToken);
        }

        return content;
    },

    generateAlternativesList(alternatives, currentToken) {
        const sortedEntries = Object.entries(alternatives)
            .sort((a, b) => b[1] - a[1])
            .map(([token, logprob]) => {
                const probability = (Math.exp(logprob) * 100).toFixed(2);
                return `<div class="probability-item">${token}: ${probability}%</div>`;
            });
        
        sortedEntries.push(
            `<div class="probability-item" style="font-weight: bold; border: 1px solid #007bff;">${currentToken}: 0.00%</div>`
        );
        
        return sortedEntries.join('');
    },

    generateFullProbabilitiesList(probabilities, currentToken) {
        return Object.entries(probabilities)
            .sort((a, b) => b[1] - a[1])
            .map(([token, logprob]) => {
                const probability = (Math.exp(logprob) * 100).toFixed(2);
                const isCurrentToken = token === currentToken;
                return `<div class="probability-item" ${
                    isCurrentToken ? 'style="font-weight: bold; border: 1px solid #007bff;"' : ''
                }>${token}: ${probability}%</div>`;
            })
            .join('');
    },

    hideTooltip() {
        elements.tooltipDiv.style.display = 'none';
    },

    moveTooltip(event) {
        const tooltip = elements.tooltipDiv;
        const padding = 10;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;
        
        let left = event.clientX + padding;
        let top = event.clientY - tooltipHeight - padding;
        
        if (left + tooltipWidth > viewportWidth - padding) {
            left = event.clientX - tooltipWidth - padding;
        }
        
        if (top < padding) {
            top = event.clientY + padding;
        }
        
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
    }
};