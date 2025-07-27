const API_BASE_URL = 'http://localhost:5000/api';

class WebScraperClient {
    constructor() {
        this.currentResults = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        const form = document.getElementById('scrapingForm');
        const scrapingType = document.getElementById('scrapingType');
        const customSelectorGroup = document.getElementById('customSelectorGroup');
        const exportBtn = document.getElementById('exportBtn');

        scrapingType.addEventListener('change', () => {
            if (scrapingType.value === 'custom') {
                customSelectorGroup.style.display = 'block';
            } else {
                customSelectorGroup.style.display = 'none';
            }
        });

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleScrapeRequest();
        });

        exportBtn.addEventListener('click', () => {
            this.exportResults();
        });

        this.checkApiHealth();
    }

    async checkApiHealth() {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            const data = await response.json();
            if (data.status === 'healthy') {
                console.log('API is healthy');
            } else {
                this.showError('API is not responding properly');
            }
        } catch (error) {
            this.showError('Cannot connect to scraping server. Make sure the Flask server is running.');
        }
    }

    async handleScrapeRequest() {
        const url = document.getElementById('url').value;
        const scrapingType = document.getElementById('scrapingType').value;
        const customSelector = document.getElementById('customSelector').value;

        if (!url || !scrapingType) {
            this.showError('Please fill in all required fields.');
            return;
        }

        if (scrapingType === 'custom' && !customSelector) {
            this.showError('Please provide a CSS selector for custom scraping.');
            return;
        }

        const requestData = {
            url: url,
            scrapingType: scrapingType
        };

        if (scrapingType === 'custom') {
            requestData.customSelector = customSelector;
        }

        await this.performScraping(requestData);
    }

    async performScraping(requestData) {
        this.hideMessages();
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('loading').style.display = 'block';
        document.getElementById('scrapeBtn').disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/scrape`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displayResults(result);
                this.showSuccess(`Successfully scraped ${result.count} items from ${result.url} in ${result.execution_time}s`);
            } else {
                this.showError(result.error || 'Failed to scrape the website');
            }

        } catch (error) {
            console.error('Scraping error:', error);
            this.showError('Network error: Could not connect to the scraping server');
        } finally {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('scrapeBtn').disabled = false;
        }
    }

    displayResults(result) {
        const dataContainer = document.getElementById('scrapedData');
        dataContainer.innerHTML = '';
        this.currentResults = result;

        if (!result.data || result.data.length === 0) {
            dataContainer.innerHTML = '<p>No data found matching your criteria.</p>';
            document.getElementById('resultsSection').style.display = 'block';
            return;
        }

        const metaDiv = document.createElement('div');
        metaDiv.className = 'data-item';
        metaDiv.style.background = '#e8f4f8';
        metaDiv.innerHTML = `
            <strong>📊 Scraping Summary:</strong><br>
            URL: ${result.url}<br>
            Type: ${result.type}<br>
            Items Found: ${result.count}<br>
            Execution Time: ${result.execution_time}s<br>
            Timestamp: ${new Date(result.timestamp).toLocaleString()}
            ${result.selector ? `<br>CSS Selector: ${result.selector}` : ''}
        `;
        dataContainer.appendChild(metaDiv);

        result.data.forEach((item, index) => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'data-item';
            
            if (result.type === 'links' && typeof item === 'object') {
                itemDiv.innerHTML = `
                    <strong>🔗 Link ${index + 1}:</strong><br>
                    <strong>Text:</strong> ${this.escapeHtml(item.text)}<br>
                    <strong>URL:</strong> <a href="${item.url}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(item.url)}</a>
                `;
            } else if (result.type === 'images') {
                itemDiv.innerHTML = `
                    <strong>🖼️ Image ${index + 1}:</strong><br>
                    <a href="${item}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(item)}</a>
                `;
            } else {
                itemDiv.innerHTML = `<strong>${this.getItemLabel(result.type)} ${index + 1}:</strong> ${this.escapeHtml(item)}`;
            }
            
            dataContainer.appendChild(itemDiv);
        });

        document.getElementById('resultsSection').style.display = 'block';
    }

    getItemLabel(type) {
        const labels = {
            text: '📝 Text',
            titles: '📋 Title',
            custom: '🎯 Custom',
            links: '🔗 Link',
            images: '🖼️ Image'
        };
        return labels[type] || '📄 Item';
    }

    exportResults() {
        if (this.currentResults) {
            const dataStr = JSON.stringify(this.currentResults, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `scraped_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
            link.click();
            URL.revokeObjectURL(url);
            this.showSuccess('Results exported successfully!');
        }
    }

    showError(message) {
        this.hideMessages();
        const errorElement = document.getElementById('errorMessage');
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 10000);
    }

    showSuccess(message) {
        this.hideMessages();
        const successElement = document.getElementById('successMessage');
        successElement.textContent = message;
        successElement.style.display = 'block';
        setTimeout(() => {
            successElement.style.display = 'none';
        }, 5000);
    }

    hideMessages() {
        document.getElementById('errorMessage').style.display = 'none';
        document.getElementById('successMessage').style.display = 'none';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new WebScraperClient();
});
