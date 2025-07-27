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
import ssl
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
import logging

# Disable SSL warnings for problematic sites
urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

class SmartWebScraper:
    def __init__(self):
        self.driver = None
        self.user_data_dir = None
        
    def get_random_user_agent(self):
        """Get a random realistic user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)
    
    def test_url_smart(self, url):
        """Smart URL testing with HTTP/HTTPS fallback"""
        logger.info(f"🔍 Smart testing URL: {url}")
        
        # Create list of URLs to test
        urls_to_test = []
        
        if url.startswith('https://'):
            urls_to_test.append(url)  # Try HTTPS first
            urls_to_test.append(url.replace('https://', 'http://'))  # Then HTTP
        elif url.startswith('http://'):
            urls_to_test.append(url)  # Try HTTP first
            urls_to_test.append(url.replace('http://', 'https://'))  # Then HTTPS
        else:
            # If no protocol specified, try both
            urls_to_test.append(f"https://{url}")
            urls_to_test.append(f"http://{url}")
        
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        for test_url in urls_to_test:
            try:
                logger.info(f"Testing: {test_url}")
                response = requests.get(
                    test_url, 
                    headers=headers,
                    timeout=15, 
                    verify=False,  # Ignore SSL issues
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ SUCCESS: {test_url} (Status: {response.status_code})")
                    return test_url, True
                else:
                    logger.warning(f"⚠️ {test_url} returned status: {response.status_code}")
                    
            except requests.exceptions.SSLError as e:
                logger.warning(f"🔒 SSL error for {test_url}: {e}")
                continue
            except requests.exceptions.Timeout as e:
                logger.warning(f"⏰ Timeout for {test_url}: {e}")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"🔌 Connection error for {test_url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"❌ Error testing {test_url}: {e}")
                continue
        
        logger.error(f"❌ All URL variants failed for: {url}")
        return url, False
    
    def setup_smart_driver(self, headless=True):
        """Setup Chrome WebDriver with smart configuration"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Generate unique user data directory
        unique_id = uuid.uuid4().hex[:8]
        self.user_data_dir = f"/tmp/chrome_smart_{unique_id}"
        
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
        
        # Smart Chrome arguments
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument(f"--remote-debugging-port={random.randint(9000, 9999)}")
        
        # Core options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        
        # SSL and security handling
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Anti-detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance and compatibility
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--window-size=1366,768")
        chrome_options.add_argument(f"--user-agent={self.get_random_user_agent()}")
        
        # Preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Find Chrome binary
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
            # Clean up old directories
            self.cleanup_temp_dirs()
            
            # Initialize Chrome
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(45)
            self.driver.implicitly_wait(10)
            
            # Execute stealth JavaScript
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
            """
            
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': stealth_js
            })
            
            # Test basic navigation
            try:
                logger.info("Testing smart WebDriver...")
                self.driver.get("data:text/html,<html><body><h1>Smart Test</h1></body></html>")
                logger.info("✅ Smart WebDriver test passed")
            except Exception as e:
                logger.warning(f"Smart WebDriver test failed: {e}")
            
            logger.info(f"✅ Smart WebDriver initialized: {self.user_data_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Smart WebDriver initialization failed: {e}")
            self.cleanup_current_session()
            return False
    
    def smart_get_page(self, url, max_retries=3):
        """Smart page loading with automatic HTTP/HTTPS fallback"""
        
        # First, find the working URL
        working_url, is_accessible = self.test_url_smart(url)
        
        if not is_accessible:
            raise Exception(f"URL {url} is not accessible via HTTP or HTTPS")
        
        logger.info(f"🎯 Using working URL: {working_url}")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Smart attempt {attempt + 1}/{max_retries}: Loading {working_url}")
                
                # Random delay before navigation (human-like)
                time.sleep(random.uniform(1, 3))
                
                # Navigate to the working URL
                self.driver.get(working_url)
                
                # Wait for page to load
                WebDriverWait(self.driver, 25).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Additional wait for dynamic content
                time.sleep(random.uniform(2, 4))
                
                # Simulate human behavior
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(1)
                    self.driver.execute_script("window.scrollTo(0, 0);")
                except:
                    pass
                
                # Verify page loaded properly
                page_source = self.driver.page_source
                if len(page_source) < 200:
                    raise Exception("Page appears to be empty or not fully loaded")
                
                logger.info(f"✅ Successfully loaded: {working_url}")
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))
                    continue
                else:
                    raise TimeoutException(f"Failed to load {working_url} after {max_retries} attempts")
                    
            except WebDriverException as e:
                error_str = str(e)
                logger.warning(f"WebDriver error on attempt {attempt + 1}: {error_str}")
                
                if any(err in error_str for err in ["ERR_CONNECTION_REFUSED", "ERR_CONNECTION_CLOSED", "net::"]):
                    if attempt < max_retries - 1:
                        logger.info("Restarting WebDriver due to connection error...")
                        self.close()
                        time.sleep(random.uniform(3, 6))
                        self.setup_smart_driver()
                        continue
                    else:
                        raise Exception(f"Persistent connection issues: {error_str}")
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                    continue
                else:
                    raise
    
    def scrape_text_content(self, url):
        """Smart text content scraping"""
        try:
            logger.info(f"Smart scraping text content from: {url}")
            
            # Use smart navigation
            self.smart_get_page(url)
            
            # Wait for dynamic content
            time.sleep(2)
            
            # Get all text elements
            elements = self.driver.find_elements(By.XPATH, "//p | //h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //span | //div[not(script) and not(style)] | //li | //td | //th")
            
            text_content = []
            for element in elements:
                try:
                    text = element.text.strip()
                    if text and len(text) > 5:  # Include shorter texts
                        text_content.append(text)
                except Exception:
                    continue
            
            # Remove duplicates and limit results
            unique_content = list(dict.fromkeys(text_content))[:100]  # Increased limit
            logger.info(f"Found {len(unique_content)} text elements")
            return unique_content
            
        except Exception as e:
            logger.error(f"Error in smart text scraping: {e}")
            raise
    
    def scrape_links(self, url):
        """Smart link scraping"""
        try:
            logger.info(f"Smart scraping links from: {url}")
            self.smart_get_page(url)
            time.sleep(2)
            
            links = self.driver.find_elements(By.TAG_NAME, "a")
            link_data = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    if href and href.startswith(('http://', 'https://', '/')):
                        if not text:
                            text = href  # Use URL as text if no text available
                        
                        link_data.append({
                            "text": text[:150],  # Increased text length
                            "url": href
                        })
                except Exception:
                    continue
            
            # Remove duplicates
            unique_links = []
            seen_urls = set()
            for link in link_data:
                if link["url"] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link["url"])
                if len(unique_links) >= 75:  # Increased limit
                    break
            
            logger.info(f"Found {len(unique_links)} unique links")
            return unique_links
            
        except Exception as e:
            logger.error(f"Error in smart link scraping: {e}")
            raise
    
    def scrape_images(self, url):
        """Smart image scraping"""
        try:
            logger.info(f"Smart scraping images from: {url}")
            self.smart_get_page(url)
            time.sleep(3)
            
            images = self.driver.find_elements(By.TAG_NAME, "img")
            image_urls = []
            
            for img in images:
                try:
                    src = img.get_attribute("src")
                    if src:
                        # Convert relative URLs to absolute
                        if src.startswith('/'):
                            current_url = self.driver.current_url
                            base_url = f"{current_url.split('://')[0]}://{current_url.split('/')[2]}"
                            src = base_url + src
                        
                        if src.startswith(('http://', 'https://', 'data:')):
                            image_urls.append(src)
                except Exception:
                    continue
            
            unique_images = list(dict.fromkeys(image_urls))[:75]  # Increased limit
            logger.info(f"Found {len(unique_images)} unique images")
            return unique_images
            
        except Exception as e:
            logger.error(f"Error in smart image scraping: {e}")
            raise
    
    def scrape_titles(self, url):
        """Smart title scraping"""
        try:
            logger.info(f"Smart scraping titles from: {url}")
            self.smart_get_page(url)
            time.sleep(2)
            
            # Get page title first
            titles = []
            try:
                page_title = self.driver.title
                if page_title:
                    titles.append(f"Page Title: {page_title}")
            except:
                pass
            
            # Get all headings
            headings = self.driver.find_elements(By.XPATH, "//h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //title")
            
            for heading in headings:
                try:
                    text = heading.text.strip()
                    if text and text not in titles:
                        titles.append(text)
                except Exception:
                    continue
            
            unique_titles = titles[:75]  # Increased limit
            logger.info(f"Found {len(unique_titles)} unique titles")
            return unique_titles
            
        except Exception as e:
            logger.error(f"Error in smart title scraping: {e}")
            raise
    
    def scrape_custom_selector(self, url, selector):
        """Smart custom selector scraping"""
        try:
            logger.info(f"Smart scraping with selector '{selector}' from: {url}")
            self.smart_get_page(url)
            time.sleep(3)
            
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            results = []
            
            for element in elements:
                try:
                    # Try multiple ways to get content
                    text = element.text.strip()
                    if not text:
                        text = (element.get_attribute("value") or 
                               element.get_attribute("alt") or 
                               element.get_attribute("title") or
                               element.get_attribute("href") or
                               element.get_attribute("src"))
                    
                    if text:
                        results.append(text)
                    else:
                        # Get limited HTML as fallback
                        html = element.get_attribute("outerHTML")
                        if html:
                            results.append(html[:300] + "..." if len(html) > 300 else html)
                except Exception:
                    continue
            
            unique_results = list(dict.fromkeys(results))[:75]  # Increased limit
            logger.info(f"Found {len(unique_results)} elements with selector '{selector}'")
            return unique_results
            
        except Exception as e:
            logger.error(f"Error in smart custom selector scraping: {e}")
            raise
    
    def cleanup_current_session(self):
        """Clean up current session data"""
        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir)
                logger.info(f"Cleaned up smart session directory: {self.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {self.user_data_dir}: {e}")
    
    def cleanup_temp_dirs(self):
        """Clean up old temp directories"""
        try:
            temp_dirs = glob.glob("/tmp/chrome_smart_*")
            for temp_dir in temp_dirs:
                try:
                    if os.path.getctime(temp_dir) < time.time() - 3600:
                        shutil.rmtree(temp_dir)
                except Exception:
                    pass
        except Exception:
            pass
    
    def close(self):
        """Enhanced cleanup"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Smart WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing smart WebDriver: {e}")
            finally:
                self.driver = None
        
        self.cleanup_current_session()
        self.cleanup_temp_dirs()

# Initialize smart scraper
scraper = SmartWebScraper()

@app.route('/')
def index():
    """Serve the main page"""
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return """
        <html>
        <head><title>🧠 Smart Web Scraper Pro</title></head>
        <body>
        <h1>🧠 Smart Web Scraper Pro</h1>
        <p>Automatic HTTP/HTTPS detection and intelligent scraping</p>
        <p>The templates/index.html file is missing. Please create it first.</p>
        <p>API is available at <a href="/api/health">/api/health</a></p>
        <h2>✅ Test Sites:</h2>
        <ul>
            <li><strong>http://deepthpk.com</strong> - Should work now!</li>
            <li>https://httpbin.org/html - Always works</li>
            <li>https://example.com - Reliable</li>
            <li>https://quotes.toscrape.com - Scraping friendly</li>
        </ul>
        <h2>🚀 Features:</h2>
        <ul>
            <li>✅ Automatic HTTP/HTTPS fallback</li>
            <li>✅ Smart SSL handling</li>
            <li>✅ Anti-detection stealth mode</li>
            <li>✅ Enhanced error recovery</li>
            <li>✅ Increased result limits</li>
        </ul>
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
    """Smart scraping endpoint with HTTP/HTTPS auto-detection"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        url = data.get('url')
        scraping_type = data.get('scrapingType')
        custom_selector = data.get('customSelector')
        
        if not url or not scraping_type:
            return jsonify({"error": "URL and scraping type are required"}), 400
        
        # Basic URL validation (allow URLs without protocol)
        if not any(url.startswith(proto) for proto in ['http://', 'https://']):
            if '.' in url:  # Looks like a domain
                url = f"https://{url}"  # Default to HTTPS, will fallback to HTTP if needed
            else:
                return jsonify({"error": "Invalid URL format"}), 400
        
        # Setup smart driver if needed
        if not scraper.driver:
            logger.info("Smart WebDriver not initialized, setting up...")
            if not scraper.setup_smart_driver():
                return jsonify({"error": "Failed to initialize smart web driver"}), 500
        
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
                "execution_time": round(end_time - start_time, 2),
                "smart_mode": True,
                "actual_url": scraper.driver.current_url if scraper.driver else url
            }
            
            if scraping_type == 'custom':
                response_data["selector"] = custom_selector
            
            logger.info(f"✅ Smart scraping successful: {len(results)} items from {url}")
            return jsonify(response_data)
            
        except Exception as e:
            error_msg = str(e)
            if "not accessible via HTTP or HTTPS" in error_msg:
                return jsonify({
                    "error": f"Website is not accessible via HTTP or HTTPS: {error_msg}",
                    "suggestion": "Check if the website URL is correct and the site is online"
                }), 502
            else:
                logger.error(f"Smart scraping error: {e}")
                return jsonify({"error": f"Smart scraping failed: {error_msg}"}), 500
            
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
        "smart_mode": True,
        "features": ["HTTP/HTTPS auto-fallback", "SSL tolerance", "Anti-detection", "Enhanced scraping"]
    })

@app.route('/api/restart-driver', methods=['POST'])
def restart_driver():
    """Restart the smart WebDriver"""
    try:
        logger.info("Restarting smart WebDriver...")
        scraper.close()
        
        if scraper.setup_smart_driver():
            return jsonify({
                "success": True, 
                "message": "Smart driver restarted successfully"
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Failed to restart smart driver"
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
    logger.info("Shutting down smart application...")
    scraper.close()

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    logger.info("🧠 Starting Smart Web Scraper Pro...")
    logger.info("Features: HTTP/HTTPS auto-fallback, SSL tolerance, Anti-detection")
    logger.info("Initializing smart WebDriver...")
    
    if scraper.setup_smart_driver():
        logger.info("✅ Smart WebDriver initialized successfully")
    else:
        logger.warning("⚠️ Smart WebDriver initialization failed - will retry on first request")
    
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting smart server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)