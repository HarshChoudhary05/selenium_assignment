from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import os
import requests
from googletrans import Translator
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.remote.remote_connection import RemoteConnection

# Constants
BASE_URL = "https://elpais.com/"
OPINION_URL = "https://elpais.com/opinion/"
IMG_DIR = "downloaded_images"
os.makedirs(IMG_DIR, exist_ok=True)

translator = Translator()

def setup_driver(remote=False, browserstack_caps=None):
    if remote:
        executor = 'https://YOUR_USERNAME:YOUR_ACCESS_KEY@hub-cloud.browserstack.com/wd/hub'
        return webdriver.Remote(command_executor=executor, desired_capabilities=browserstack_caps)
    else:
        options = Options()
        options.add_argument("--headless")
        return webdriver.Chrome(options=options)

def scrape_articles(driver):
    driver.get(OPINION_URL)
    time.sleep(5)

    # Collect article links first
    articles = driver.find_elements(By.CSS_SELECTOR, "article")[:5]
    links = []
    for article in articles:
        try:
            link = article.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            links.append(link)
        except Exception as e:
            print(f"Error getting link: {e}")

    article_data = []
    for link in links:
        try:
            driver.get(link)
            time.sleep(2)
            title = driver.find_element(By.TAG_NAME, "h1").text
            paragraphs = driver.find_elements(By.CSS_SELECTOR, "p")
            content = "\n".join([p.text for p in paragraphs if p.text.strip()])
            
            # Download image
            img_name = None
            try:
                # Try <picture><img>
                img = driver.find_element(By.CSS_SELECTOR, "picture img").get_attribute("src")
            except Exception:
                try:
                    # Try <meta property="og:image">
                    img = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]').get_attribute("content")
                except Exception:
                    try:
                        # Try first <img> in article
                        img = driver.find_element(By.CSS_SELECTOR, "article img").get_attribute("src")
                    except Exception:
                        img = None
            if img:
                img_name = os.path.join(IMG_DIR, title[:50].replace(" ", "_") + ".jpg")
                with open(img_name, "wb") as f:
                    f.write(requests.get(img).content)

            article_data.append({
                "title": title,
                "content": content,
                "image": img_name
            })

            print(f"\n📰 Title (Spanish): {title}\n📄 Content:\n{content[:300]}...\n🖼️ Image: {img_name or 'Not Found'}")

        except Exception as e:
            print(f"Error reading article: {e}")
    return article_data

def translate_titles(articles):
    translated = []
    for art in articles:
        en_title = translator.translate(art['title'], src='es', dest='en').text
        translated.append(en_title)
        print(f"\n🔤 Translated Title: {en_title}")
    return translated

def analyze_titles(titles):
    words = ' '.join(titles).lower().split()
    freq = Counter(words)
    print("\n📊 Repeated Words:")
    for word, count in freq.items():
        if count > 2:
            print(f"{word}: {count}")

def run_test(remote=False, browserstack_caps=None):
    driver = setup_driver(remote, browserstack_caps)
    try:
        articles = scrape_articles(driver)
        translated = translate_titles(articles)
        analyze_titles(translated)
    finally:
        driver.quit()

# ---- Local run ----
print("\n🔧 Running Locally...")
run_test()

# ---- BrowserStack Run (parallel) ----
print("\n☁️ Running on BrowserStack...")

BROWSERSTACK_USERNAME = 'YOUR_USERNAME'
BROWSERSTACK_ACCESS_KEY = 'YOUR_ACCESS_KEY'

caps_list = [
    {
        'os': 'Windows', 'os_version': '10', 'browser': 'Chrome', 'browser_version': 'latest',
        'name': 'Chrome Test', 'build': 'SeleniumAssignment'
    },
    {
        'os': 'OS X', 'os_version': 'Monterey', 'browser': 'Safari', 'browser_version': 'latest',
        'name': 'Safari Test', 'build': 'SeleniumAssignment'
    },
    {
        'device': 'iPhone 14', 'real_mobile': 'true', 'os_version': '16', 'browserName': 'iPhone',
        'name': 'iOS Test', 'build': 'SeleniumAssignment'
    },
    {
        'device': 'Samsung Galaxy S22', 'real_mobile': 'true', 'os_version': '12.0', 'browserName': 'Android',
        'name': 'Android Test', 'build': 'SeleniumAssignment'
    },
    {
        'os': 'Windows', 'os_version': '10', 'browser': 'Edge', 'browser_version': 'latest',
        'name': 'Edge Test', 'build': 'SeleniumAssignment'
    }
]

# Add BrowserStack credentials
for caps in caps_list:
    caps['browserstack.user'] = BROWSERSTACK_USERNAME
    caps['browserstack.key'] = BROWSERSTACK_ACCESS_KEY

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(lambda c: run_test(remote=True, browserstack_caps=c), caps_list)
