from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import json
import time
import os
import tempfile
import uuid
import shutil
import glob
import random
import requests
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

class StealthWebScraper:
    def __init__(self):
        self.driver = None
        self.user_data_dir = None
        
    def get_random_user_agent(self):
        """Get a random realistic user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)
    
    def test_url_with_requests(self, url):
        """Test URL accessibility with requests library using realistic headers"""
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            logger.info(f"Testing URL with requests: {url}")
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True, verify=False)
            logger.info(f"Requests test response: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ URL is accessible via requests")
                return True
            else:
                logger.warning(f"⚠️ URL returned status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Requests test failed: {e}")
            return False
        
    def setup_stealth_driver(self, headless=True):
        """Setup Chrome WebDriver with maximum stealth features"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Generate unique user data directory
        unique_id = uuid.uuid4().hex[:8]
        self.user_data_dir = f"/tmp/chrome_stealth_{unique_id}"
        
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
        
        # Stealth Chrome arguments
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument(f"--remote-debugging-port={random.randint(9000, 9999)}")
        
        # Basic stealth options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-background-networking")
        
        # Anti-detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # Mimic real browser behavior
        chrome_options.add_argument("--window-size=1366,768")  # Common screen size
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-agent={self.get_random_user_agent()}")
        
        # Disable automation indicators
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Additional preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # Block notifications
                "media_stream": 2,   # Block media access
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Block images for faster loading
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
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
            
            # Try direct Chrome initialization (skip webdriver-manager for stealth)
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Execute stealth JavaScript to hide automation
            stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            window.chrome = {
                runtime: {},
            };
            
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: async (parameters) => ({
                        state: Notification.permission === 'denied' ? 'denied' : 'granted'
                    }),
                }),
            });
            """
            
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': stealth_js
            })
            
            # Test basic navigation
            try:
                logger.info("Testing stealth WebDriver with basic navigation...")
                self.driver.get("data:text/html,<html><body><h1>Stealth Test</h1></body></html>")
                logger.info("✅ Stealth WebDriver basic navigation test passed")
            except Exception as e:
                logger.warning(f"Stealth WebDriver basic test failed: {e}")
            
            logger.info(f"✅ Stealth WebDriver initialized successfully with directory: {self.user_data_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Stealth WebDriver initialization failed: {e}")
            self.cleanup_current_session()
            return False
    
    def stealth_get_page(self, url, max_retries=3):
        """Navigate to page with maximum stealth and retries"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Stealth attempt {attempt + 1}/{max_retries}: Loading {url}")
                
                # Test with requests first
                if not self.test_url_with_requests(url):
                    if attempt == max_retries - 1:
                        raise Exception(f"URL {url} is not accessible via requests")
                    else:
                        logger.info("Requests failed, but trying with WebDriver anyway...")
                
                # Random delay before navigation (human-like behavior)
                time.sleep(random.uniform(1, 3))
                
                # Navigate to page
                self.driver.get(url)
                
                # Random delay after navigation
                time.sleep(random.uniform(2, 4))
                
                # Wait for page to load
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Additional wait for dynamic content
                time.sleep(random.uniform(1, 3))
                
                # Scroll page to simulate human behavior
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, 0);")
                
                logger.info(f"✅ Successfully loaded with stealth: {url}")
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout loading {url} on stealth attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))
                    continue
                else:
                    raise TimeoutException(f"Failed to load {url} after {max_retries} stealth attempts")
                    
            except WebDriverException as e:
                error_str = str(e)
                if any(err in error_str for err in ["ERR_CONNECTION_REFUSED", "ERR_CONNECTION_CLOSED", "net::"]):
                    logger.warning(f"Network error on stealth attempt {attempt + 1}: {error_str}")
                    if attempt < max_retries - 1:
                        # Restart driver with new settings
                        logger.info("Restarting stealth WebDriver due to network error...")
                        self.close()
                        time.sleep(random.uniform(5, 8))
                        self.setup_stealth_driver()
                        continue
                    else:
                        raise Exception(f"Network connection failed after {max_retries} stealth attempts: {error_str}")
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error on stealth attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))
                    continue
                else:
                    raise
    
    def cleanup_current_session(self):
        """Clean up current session data"""
        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir)
                logger.info(f"Cleaned up stealth session directory: {self.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {self.user_data_dir}: {e}")
    
    def cleanup_temp_dirs(self):
        """Clean up old temp directories"""
        try:
            temp_dirs = glob.glob("/tmp/chrome_stealth_*")
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
        """Scrape all text content from the page with stealth"""
        try:
            logger.info(f"Stealth scraping text content from: {url}")
            
            # Use stealth navigation
            self.stealth_get_page(url)
            
            # Wait a bit more for dynamic content
            time.sleep(2)
            
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
            logger.info(f"Found {len(unique_content)} text elements with stealth scraping")
            return unique_content
            
        except Exception as e:
            logger.error(f"Error in stealth text scraping: {e}")
            raise
    
    def scrape_links(self, url):
        """Scrape all links from the page with stealth"""
        try:
            logger.info(f"Stealth scraping links from: {url}")
            
            # Use stealth navigation
            self.stealth_get_page(url)
            
            # Wait for dynamic links to load
            time.sleep(2)
            
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
            
            logger.info(f"Found {len(unique_links)} unique links with stealth scraping")
            return unique_links
            
        except Exception as e:
            logger.error(f"Error in stealth link scraping: {e}")
            raise
    
    def scrape_images(self, url):
        """Scrape all image URLs from the page with stealth"""
        try:
            logger.info(f"Stealth scraping images from: {url}")
            
            # Use stealth navigation
            self.stealth_get_page(url)
            
            # Wait for images to load
            time.sleep(3)
            
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
            logger.info(f"Found {len(unique_images)} unique images with stealth scraping")
            return unique_images
            
        except Exception as e:
            logger.error(f"Error in stealth image scraping: {e}")
            raise
    
    def scrape_titles(self, url):
        """Scrape all heading elements (h1-h6) from the page with stealth"""
        try:
            logger.info(f"Stealth scraping titles from: {url}")
            
            # Use stealth navigation
            self.stealth_get_page(url)
            
            # Wait for content to load
            time.sleep(2)
            
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
            logger.info(f"Found {len(unique_titles)} unique titles with stealth scraping")
            return unique_titles
            
        except Exception as e:
            logger.error(f"Error in stealth title scraping: {e}")
            raise
    
    def scrape_custom_selector(self, url, selector):
        """Scrape elements using custom CSS selector with stealth"""
        try:
            logger.info(f"Stealth scraping with custom selector '{selector}' from: {url}")
            
            # Use stealth navigation
            self.stealth_get_page(url)
            
            # Wait for dynamic content
            time.sleep(3)
            
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
            logger.info(f"Found {len(unique_results)} elements with stealth selector '{selector}'")
            return unique_results
            
        except Exception as e:
            logger.error(f"Error in stealth custom selector scraping: {e}")
            raise
    
    def close(self):
        """Enhanced cleanup for stealth scraper"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Stealth WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing stealth WebDriver: {e}")
            finally:
                self.driver = None
        
        # Cleanup session directory
        self.cleanup_current_session()
        
        # Cleanup old temp directories
        self.cleanup_temp_dirs()

# Initialize stealth scraper instance
scraper = StealthWebScraper()

@app.route('/')
def index():
    """Serve the main page"""
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return """
        <html>
        <head><title>Stealth Web Scraper Pro</title></head>
        <body>
        <h1>🥷 Stealth Web Scraper Pro</h1>
        <p>Advanced anti-detection web scraping with Selenium</p>
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
    """Main stealth scraping endpoint"""
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
        
        # Setup stealth driver if not already done
        if not scraper.driver:
            logger.info("Stealth WebDriver not initialized, setting up...")
            if not scraper.setup_stealth_driver():
                return jsonify({"error": "Failed to initialize stealth web driver. Please check Chrome/Chromium installation."}), 500
        
        # Perform stealth scraping based on type
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
                "execution_time": round(end_time - start_time, 2),
                "stealth_mode": True
            }
            
            if scraping_type == 'custom':
                response_data["selector"] = custom_selector
            
            logger.info(f"✅ Successfully stealth scraped {len(results)} items from {url} in {response_data['execution_time']}s")
            return jsonify(response_data)
            
        except TimeoutException:
            return jsonify({"error": "Page load timeout - website may be slow, protected, or unresponsive"}), 408
        except NoSuchElementException:
            return jsonify({"error": "Could not find specified elements on the page"}), 404
        except Exception as e:
            error_msg = str(e)
            if any(err in error_msg for err in ["ERR_CONNECTION_REFUSED", "ERR_CONNECTION_CLOSED", "net::"]):
                return jsonify({"error": f"Network connection blocked. Website may have anti-bot protection: {error_msg}"}), 502
            else:
                logger.error(f"Stealth scraping error: {e}")
                return jsonify({"error": f"Stealth scraping failed: {error_msg}"}), 500
            
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
        "user_data_dir": scraper.user_data_dir,
        "stealth_mode": True
    })

@app.route('/api/restart-driver', methods=['POST'])
def restart_driver():
    """Restart the stealth WebDriver instance"""
    try:
        logger.info("Restarting stealth WebDriver...")
        scraper.close()
        
        if scraper.setup_stealth_driver():
            return jsonify({
                "success": True, 
                "message": "Stealth driver restarted successfully",
                "user_data_dir": scraper.user_data_dir
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Failed to restart stealth driver"
            }), 500
    except Exception as e:
        logger.error(f"Stealth driver restart error: {e}")
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
    logger.info("Shutting down stealth application...")
    scraper.close()

# Register cleanup function
import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Initialize stealth driver on startup
    logger.info("🥷 Starting Stealth Web Scraper Pro...")
    logger.info("Initializing stealth WebDriver...")
    
    if scraper.setup_stealth_driver():
        logger.info("✅ Stealth WebDriver initialized successfully")
    else:
        logger.warning("⚠️  Stealth WebDriver initialization failed - will retry on first scrape request")
    
    # Get port from environment (for deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app
    logger.info(f"🌐 Starting stealth server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)