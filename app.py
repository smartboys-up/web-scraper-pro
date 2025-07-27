from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class WebScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        if os.environ.get('DYNO') or os.environ.get('PORT'):
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def scrape_text_content(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            elements = self.driver.find_elements(By.XPATH, "//p | //h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //span | //div[not(script) and not(style)]")
            text_content = []
            for element in elements:
                text = element.text.strip()
                if text and len(text) > 10:
                    text_content.append(text)
            return list(set(text_content))[:50]
        except Exception as e:
            logger.error(f"Error scraping text content: {e}")
            raise
    
    def scrape_links(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            links = self.driver.find_elements(By.TAG_NAME, "a")
            link_data = []
            for link in links:
                href = link.get_attribute("href")
                text = link.text.strip()
                if href and text:
                    link_data.append({"text": text, "url": href})
            return link_data[:50]
        except Exception as e:
            logger.error(f"Error scraping links: {e}")
            raise
    
    def scrape_images(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            images = self.driver.find_elements(By.TAG_NAME, "img")
            image_urls = []
            for img in images:
                src = img.get_attribute("src")
                if src:
                    image_urls.append(src)
            return list(set(image_urls))[:50]
        except Exception as e:
            logger.error(f"Error scraping images: {e}")
            raise
    
    def scrape_titles(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            headings = self.driver.find_elements(By.XPATH, "//h1 | //h2 | //h3 | //h4 | //h5 | //h6")
            titles = []
            for heading in headings:
                text = heading.text.strip()
                if text:
                    titles.append(text)
            return titles[:50]
        except Exception as e:
            logger.error(f"Error scraping titles: {e}")
            raise
    
    def scrape_custom_selector(self, url, selector):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            results = []
            for element in elements:
                text = element.text.strip()
                if not text:
                    text = element.get_attribute("value") or element.get_attribute("alt") or element.get_attribute("title")
                if text:
                    results.append(text)
                else:
                    html = element.get_attribute("outerHTML")
                    if html:
                        results.append(html[:200] + "..." if len(html) > 200 else html)
            return results[:50]
        except Exception as e:
            logger.error(f"Error scraping with custom selector: {e}")
            raise
    
    def close(self):
        if self.driver:
            self.driver.quit()

scraper = WebScraper()

@app.route('/')
def index():
    with open('templates/index.html', 'r') as f:
        return render_template_string(f.read())

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/api/scrape', methods=['POST'])
def scrape_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        url = data.get('url')
        scraping_type = data.get('scrapingType')
        custom_selector = data.get('customSelector')
        
        if not url or not scraping_type:
            return jsonify({"error": "URL and scraping type are required"}), 400
        
        if not url.startswith(('http://', 'https://')):
            return jsonify({"error": "Invalid URL format"}), 400
        
        if not scraper.driver:
            if not scraper.setup_driver():
                return jsonify({"error": "Failed to initialize web driver"}), 500
        
        start_time = time.time()
        
        try:
            if scraping_type == 'text':
                results = scraper.scrape_text_content(url)
            elif scraping_type == 'links':
                results = scraper.scrape_links(url)
            elif scraping_type == 'images':
                results = scraper.scrape_images(url)
            elif scraping_type == 'titles':
                results = scraper.scrape_titles(url)
            elif scraping_type == 'custom':
                if not custom_selector:
                    return jsonify({"error": "Custom selector is required"}), 400
                results = scraper.scrape_custom_selector(url, custom_selector)
            else:
                return jsonify({"error": "Invalid scraping type"}), 400
            
            end_time = time.time()
            
            response_data = {
                "success": True,
                "url": url,
                "type": scraping_type,
                "count": len(results),
                "data": results,
                "timestamp": datetime.now().isoformat(),
                "execution_time": round(end_time - start_time, 2)
            }
            
            if scraping_type == 'custom':
                response_data["selector"] = custom_selector
            
            logger.info(f"Successfully scraped {len(results)} items from {url}")
            return jsonify(response_data)
            
        except TimeoutException:
            return jsonify({"error": "Page load timeout"}), 408
        except NoSuchElementException:
            return jsonify({"error": "Could not find specified elements"}), 404
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return jsonify({"error": f"Scraping failed: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Request processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "driver_active": scraper.driver is not None
    })

def cleanup():
    scraper.close()

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    logger.info("Initializing WebDriver...")
    if scraper.setup_driver():
        logger.info("WebDriver initialized successfully")
    else:
        logger.error("Failed to initialize WebDriver")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
