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
import tempfile
import uuid
import shutil
import glob
import random
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

class WebScraper:
    def __init__(self):
        self.driver = None
        self.user_data_dir = None
        
    def setup_driver(self, headless=True):
        """WSL-optimized Chrome WebDriver setup with conflict resolution"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Generate unique user data directory in /tmp
        unique_id = uuid.uuid4().hex[:8]
        self.user_data_dir = f"/tmp/chrome_scraper_{unique_id}"
        
        # Clean up if directory exists
        if os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir)
            except Exception as e:
                logger.warning(f"Failed to remove existing directory: {e}")
        
        # Create directory
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create directory: {e}")
        
        # WSL-specific Chrome arguments
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument(f"--remote-debugging-port={random.randint(9000, 9999)}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Try to find Chrome/Chromium binary
        chrome_binaries = [
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome",
            "/usr/bin/chromium",
            "/snap/bin/chromium"
        ]
        
        for binary in chrome_binaries:
            if os.path.exists(binary):
                chrome_options.binary_location = binary
                logger.info(f"Using Chrome binary: {binary}")
                break
        
        try:
            # Clean up any existing temp directories first
            self.cleanup_temp_dirs()
            
            # Try with webdriver-manager first
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logger.warning(f"WebDriver Manager failed, trying direct Chrome: {e}")
                # Fallback to direct Chrome
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            logger.info(f"✅ WebDriver initialized successfully with directory: {self.user_data_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebDriver initialization failed: {e}")
            self.cleanup_current_session()
            return False
    
    def cleanup_current_session(self):
        """Clean up current session data"""
        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir)
                logger.info(f"Cleaned up session directory: {self.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {self.user_data_dir}: {e}")
    
    def cleanup_temp_dirs(self):
        """Clean up old temp directories"""
        try:
            temp_dirs = glob.glob("/tmp/chrome_scraper_*")
            for temp_dir in temp_dirs:
                try:
                    # Only remove directories older than 1 hour
                    if os.path.getctime(temp_dir) < time.time() - 3600:
                        shutil.rmtree(temp_dir)
                except Exception:
                    pass
        except Exception:
            pass
    
    def scrape_text_content(self, url):
        """Scrape all text content from the page"""
        try:
            logger.info(f"Scraping text content from: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get all text elements, excluding script and style tags
            elements = self.driver.find_elements(By.XPATH, "//p | //h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //span | //div[not(script) and not(style)]")
            
            text_content = []
            for element in elements:
                try:
                    text = element.text.strip()
                    if text and len(text) > 10:  # Filter out very short texts
                        text_content.append(text)
                except Exception:
                    continue
            
            # Remove duplicates and limit results
            unique_content = list(dict.fromkeys(text_content))[:50]
            logger.info(f"Found {len(unique_content)} text elements")
            return unique_content
            
        except Exception as e:
            logger.error(f"Error scraping text content: {e}")
            raise
    
    def scrape_links(self, url):
        """Scrape all links from the page"""
        try:
            logger.info(f"Scraping links from: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            links = self.driver.find_elements(By.TAG_NAME, "a")
            link_data = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    if href and text and href.startswith(('http://', 'https://')):
                        link_data.append({
                            "text": text[:100],  # Limit text length
                            "url": href
                        })
                except Exception:
                    continue
            
            # Remove duplicates and limit results
            unique_links = []
            seen_urls = set()
            for link in link_data:
                if link["url"] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link["url"])
                if len(unique_links) >= 50:
                    break
            
            logger.info(f"Found {len(unique_links)} unique links")
            return unique_links
            
        except Exception as e:
            logger.error(f"Error scraping links: {e}")
            raise
    
    def scrape_images(self, url):
        """Scrape all image URLs from the page"""
        try:
            logger.info(f"Scraping images from: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            images = self.driver.find_elements(By.TAG_NAME, "img")
            image_urls = []
            
            for img in images:
                try:
                    src = img.get_attribute("src")
                    if src and src.startswith(('http://', 'https://')):
                        image_urls.append(src)
                except Exception:
                    continue
            
            # Remove duplicates and limit results
            unique_images = list(dict.fromkeys(image_urls))[:50]
            logger.info(f"Found {len(unique_images)} unique images")
            return unique_images
            
        except Exception as e:
            logger.error(f"Error scraping images: {e}")
            raise
    
    def scrape_titles(self, url):
        """Scrape all heading elements (h1-h6) from the page"""
        try:
            logger.info(f"Scraping titles from: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            headings = self.driver.find_elements(By.XPATH, "//h1 | //h2 | //h3 | //h4 | //h5 | //h6")
            titles = []
            
            for heading in headings:
                try:
                    text = heading.text.strip()
                    if text:
                        titles.append(text)
                except Exception:
                    continue
            
            # Remove duplicates and limit results
            unique_titles = list(dict.fromkeys(titles))[:50]
            logger.info(f"Found {len(unique_titles)} unique titles")
            return unique_titles
            
        except Exception as e:
            logger.error(f"Error scraping titles: {e}")
            raise
    
    def scrape_custom_selector(self, url, selector):
        """Scrape elements using custom CSS selector"""
        try:
            logger.info(f"Scraping with custom selector '{selector}' from: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            results = []
            
            for element in elements:
                try:
                    # Try to get text content first
                    text = element.text.strip()
                    if not text:
                        # Try other attributes if no text
                        text = (element.get_attribute("value") or 
                               element.get_attribute("alt") or 
                               element.get_attribute("title") or
                               element.get_attribute("href"))
                    
                    if text:
                        results.append(text)
                    else:
                        # If no text, get limited HTML
                        html = element.get_attribute("outerHTML")
                        if html:
                            results.append(html[:200] + "..." if len(html) > 200 else html)
                except Exception:
                    continue
            
            # Remove duplicates and limit results
            unique_results = list(dict.fromkeys(results))[:50]
            logger.info(f"Found {len(unique_results)} elements with selector '{selector}'")
            return unique_results
            
        except Exception as e:
            logger.error(f"Error scraping with custom selector: {e}")
            raise
    
    def close(self):
        """Enhanced cleanup for WSL"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
        
        # Cleanup session directory
        self.cleanup_current_session()
        
        # Cleanup old temp directories
        self.cleanup_temp_dirs()

# Initialize scraper instance
scraper = WebScraper()

@app.route('/')
def index():
    """Serve the main page"""
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return """
        <html>
        <head><title>Web Scraper Pro</title></head>
        <body>
        <h1>Web Scraper Pro</h1>
        <p>The templates/index.html file is missing. Please create it first.</p>
        <p>API is available at <a href="/api/health">/api/health</a></p>
        </body>
        </html>
        """, 200

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    try:
        return send_from_directory('static', filename)
    except FileNotFoundError:
        return "Static file not found", 404

@app.route('/api/scrape', methods=['POST'])
def scrape_endpoint():
    """Main scraping endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        url = data.get('url')
        scraping_type = data.get('scrapingType')
        custom_selector = data.get('customSelector')
        
        if not url or not scraping_type:
            return jsonify({"error": "URL and scraping type are required"}), 400
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            return jsonify({"error": "Invalid URL format. Must start with http:// or https://"}), 400
        
        # Setup driver if not already done
        if not scraper.driver:
            logger.info("WebDriver not initialized, setting up...")
            if not scraper.setup_driver():
                return jsonify({"error": "Failed to initialize web driver. Please check Chrome/Chromium installation."}), 500
        
        # Perform scraping based on type
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
                    return jsonify({"error": "Custom selector is required for custom scraping type"}), 400
                results = scraper.scrape_custom_selector(url, custom_selector)
            else:
                return jsonify({"error": "Invalid scraping type. Must be: text, links, images, titles, or custom"}), 400
            
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
            
            logger.info(f"✅ Successfully scraped {len(results)} items from {url} in {response_data['execution_time']}s")
            return jsonify(response_data)
            
        except TimeoutException:
            return jsonify({"error": "Page load timeout - website may be slow or unresponsive"}), 408
        except NoSuchElementException:
            return jsonify({"error": "Could not find specified elements on the page"}), 404
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return jsonify({"error": f"Scraping failed: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Request processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "driver_active": scraper.driver is not None,
        "user_data_dir": scraper.user_data_dir
    })

@app.route('/api/restart-driver', methods=['POST'])
def restart_driver():
    """Restart the WebDriver instance"""
    try:
        logger.info("Restarting WebDriver...")
        scraper.close()
        
        if scraper.setup_driver():
            return jsonify({
                "success": True, 
                "message": "Driver restarted successfully",
                "user_data_dir": scraper.user_data_dir
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Failed to restart driver"
            }), 500
    except Exception as e:
        logger.error(f"Driver restart error: {e}")
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

def cleanup():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application...")
    scraper.close()

# Register cleanup function
import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Initialize driver on startup
    logger.info("🚀 Starting Web Scraper Pro...")
    logger.info("Initializing WebDriver...")
    
    if scraper.setup_driver():
        logger.info("✅ WebDriver initialized successfully")
    else:
        logger.warning("⚠️  WebDriver initialization failed - will retry on first scrape request")
    
    # Get port from environment (for deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app
    logger.info(f"🌐 Starting server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)