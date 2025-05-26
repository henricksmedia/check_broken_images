#!/usr/bin/env python
"""
===============================================================================
Script Name: check_broken_images.py
Description:
    This script scans web pages—either a single page or multiple pages from a user-provided sitemap—to identify broken images.

    How It Works:
    -------------
    1. **Page Retrieval and Parsing:**
       - Retrieves HTML content of each page using HTTP requests.
       - Uses BeautifulSoup to parse HTML and extract <img> elements from designated content containers.

    2. **URL Normalization and Validation:**
       - Normalizes image URLs (converts relative URLs to absolute).
       - Checks URLs with an HTTP HEAD request, falling back to GET if HEAD returns 405.
       - Flags HTTP responses outside 2xx range (e.g., 404, 500) or network timeouts as errors.

    3. **Content Security Policy (CSP) and Storage Classification:**
       - Verifies image domains against a user-defined allowed list.
       - Classifies images based on URL patterns (e.g., AWS, Base64, etc.).

    4. **CSV Reporting:**
       - Compiles broken image details (Article ID, Title, Page URL, Image URL, HTTP error, storage classification) into a timestamped CSV file.

    This process ensures broken images are identified, classified, and reported for review.

Version: 1.1.0
Author: Jeremy Henricks
Last Updated: 2025-05-26
===============================================================================
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import csv
from pathlib import Path
import concurrent.futures
import logging
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,  # Set to INFO for less verbosity
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------------------------------------------------------------------------
# Configuration: Allowed Domains and Storage Classification Mapping
# ---------------------------------------------------------------------------
def get_allowed_domains():
    """
    Prompt user for allowed image domains or use defaults.
    
    Returns:
        list: List of allowed domains.
    """
    default_domains = ['example.com', 'cdn.example.com']
    user_input = input("Enter allowed image domains (comma-separated, press Enter for defaults): ").strip()
    if user_input:
        return [domain.strip() for domain in user_input.split(',')]
    return default_domains

def get_storage_classification():
    """
    Return a default storage classification mapping.
    
    Returns:
        dict: Mapping of URL patterns to storage classifications.
    """
    return {
        "s3.amazonaws.com": "Amazon Web Services",
        "data:image": "Base64 Encoded Image",
        "blob:": "Blob",
        "box.com": "Box",
        "confluence": "Confluence",
        "etrack:": "Etrack",
        "googleusercontent": "Google CDN",
        "chat.google.com": "Google Chat",
        "mail.google.com": "Google Mail",
        "gstatic.com": "Google Static Content",
        "imgur": "Imgur",
        "jira": "JIRA",
        "c:\\": "Local",
        "file:///": "Local",
        "wp-content": "WordPress",
        "zendesk": "Zendesk"
    }

ALLOWED_IMG_DOMAINS = get_allowed_domains()
STORAGE_CLASSIFICATION = get_storage_classification()

# ---------------------------------------------------------------------------
# Timeout, Request Delay, and Concurrency Settings
# ---------------------------------------------------------------------------
REQUEST_DELAY = 1  # Delay between page fetches (seconds)
OUTPUT_DIRECTORY = Path(input("Enter output directory path: ").strip() or "reports/broken_images")

# ---------------------------------------------------------------------------
# Storage Classification Function
# ---------------------------------------------------------------------------
def classify_image_storage(url):
    """
    Classify the storage location based on URL patterns.

    Args:
        url (str): The image URL.

    Returns:
        str: The storage classification or "Other".
    """
    lower_url = url.lower()
    for key, classification in STORAGE_CLASSIFICATION.items():
        if key.lower() in lower_url:
            return classification
    return "Other"

# ---------------------------------------------------------------------------
# Domain Allowance Check
# ---------------------------------------------------------------------------
def is_allowed_domain(url):
    """
    Verify if the URL's domain is allowed.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if domain is allowed, False otherwise.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    result = any(allowed.lower() in domain for allowed in ALLOWED_IMG_DOMAINS)
    logging.debug(f"Domain check for {url} -> domain: {domain}, allowed: {result}")
    return result

# ---------------------------------------------------------------------------
# Image Checking Function
# ---------------------------------------------------------------------------
def check_image(url, session):
    """
    Check if an image URL is broken.

    Args:
        url (str): The image URL.
        session (requests.Session): HTTP session for requests.

    Returns:
        str or None: Error reason if broken, None if image is valid.
    """
    if not is_allowed_domain(url):
        logging.info(f"CSP violation: Image {url} is not hosted on an allowed domain.")
        return "CSP Violation"

    try:
        response = session.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 405:
            logging.debug(f"HEAD not allowed for {url}; trying GET.")
            response = session.get(url, timeout=10, stream=True, allow_redirects=True)

        logging.debug(f"Fetched {url} with status code {response.status_code}")
        if not (200 <= response.status_code < 300):
            logging.info(f"Image {url} returned non-2xx status code: {response.status_code}")
            return f"HTTP {response.status_code}"
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error for image {url}: {e}")
        return f"Network Error: {e}"

# ---------------------------------------------------------------------------
# Page Scraping and Image Checking Function
# ---------------------------------------------------------------------------
def scrape_and_check_images(url, session):
    """
    Retrieve page HTML, extract image URLs, and check for errors.

    Args:
        url (str): The page URL.
        session (requests.Session): HTTP session for requests.

    Returns:
        list: List of dictionaries with broken image details.
    """
    time.sleep(REQUEST_DELAY)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve {url}. Error: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    container_selectors = ['.article-detail-card-content']
    images = []
    for selector in container_selectors:
        container = soup.select_one(selector)
        if container:
            images_in_container = container.find_all('img', src=True)
            images.extend(images_in_container)
            logging.debug(f"Found {len(images_in_container)} images in container {selector}.")
        else:
            logging.debug(f"Container {selector} not found in {url}.")

    broken_images = []
    for image in images:
        image_url = urljoin(url, image['src'])
        logging.debug(f"Found image: {image_url}")

        if image_url.startswith("data:image"):
            prefix, base64_data = image_url.split(',', 1)
            shortened_base64 = base64_data[:20] + "..." + base64_data[-20:] if len(base64_data) > 40 else base64_data
            image_url = prefix + "," + shortened_base64

        reason = check_image(image_url, session)
        if reason:
            storage = classify_image_storage(image_url)
            logging.info(f"Flagging broken image: {image_url} -> {reason} (Storage: {storage})")
            broken_images.append({
                'Article ID': get_article_id(url),
                'Title': get_title(soup),
                'Page URL': url,
                'Broken Image URL': image_url,
                'HTTP Status Code': reason,
                'Storage Location': storage
            })

    return broken_images

# ---------------------------------------------------------------------------
# Utility Functions for Data Extraction
# ---------------------------------------------------------------------------
def get_article_id(url):
    """
    Extract numeric article ID from URL.

    Args:
        url (str): The article URL.

    Returns:
        str: Article ID or empty string.
    """
    parsed_url = urlparse(url)
    path_parts = [segment for segment in parsed_url.path.split('/') if segment]
    if "article" in path_parts:
        idx = path_parts.index("article")
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]
    return ""

def get_title(soup):
    """
    Extract page title from parsed HTML.

    Args:
        soup (BeautifulSoup): Parsed HTML content.

    Returns:
        str: Page title or empty string.
    """
    return soup.title.string.strip() if soup.title and soup.title.string else ''

# ---------------------------------------------------------------------------
# CSV Output Function
# ---------------------------------------------------------------------------
def save_to_csv(data, filename_prefix):
    """
    Save broken image data to a timestamped CSV file.

    Args:
        data (list): List of broken image details.
        filename_prefix (str): Prefix for output filename.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{filename_prefix}_{timestamp}.csv"
    output_path = OUTPUT_DIRECTORY / filename
    fieldnames = ['Article ID', 'Title', 'Page URL', 'Broken Image URL', 'HTTP Status Code', 'Storage Location']
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open('w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(data)
        logging.info(f"Data saved to {output_path}.")
    except Exception as e:
        logging.error(f"Failed to save CSV file. Error: {e}")

# ---------------------------------------------------------------------------
# Single Page Checking Function
# ---------------------------------------------------------------------------
def check_single_page(session):
    """
    Prompt for a single page URL, check for broken images, and save to CSV.

    Args:
        session (requests.Session): HTTP session.
    """
    page_url = input("Enter the page URL to check: ").strip()
    if not page_url:
        logging.error("No URL provided. Exiting single page check.")
        return
    logging.info(f"Checking single page: {page_url}")
    broken_images = scrape_and_check_images(page_url, session)
    logging.info(f"Found {len(broken_images)} broken images on {page_url}" if broken_images else "No broken images found.")
    save_to_csv(broken_images, "broken_images_single_page")

# ---------------------------------------------------------------------------
# All Pages (Sitemap) Checking Function
# ---------------------------------------------------------------------------
def check_all_pages(session):
    """
    Process user-provided sitemap URLs to check all pages for broken images.

    Args:
        session (requests.Session): HTTP session.
    """
    main_sitemap_url = input("Enter the main sitemap URL: ").strip()
    if not main_sitemap_url:
        logging.error("No sitemap URL provided. Exiting all pages check.")
        return

    try:
        response = session.get(main_sitemap_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve main sitemap: {main_sitemap_url}. Error: {e}")
        return

    main_soup = BeautifulSoup(response.content, 'xml')
    sitemap_urls = [loc.text.strip() for loc in main_soup.find_all('loc')]
    logging.info(f"Found {len(sitemap_urls)} sitemap URLs.")

    broken_images = []
    max_threads = 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        for sitemap_url in sitemap_urls:
            try:
                response = session.get(sitemap_url, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to retrieve sitemap: {sitemap_url}. Error: {e}")
                continue

            sitemap_soup = BeautifulSoup(response.content, 'xml')
            loc_tags = sitemap_soup.find_all('loc')
            future_to_url = {
                executor.submit(scrape_and_check_images, loc.text, session): loc.text
                for loc in loc_tags
            }

            for future in concurrent.futures.as_completed(future_to_url):
                page_url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        broken_images.extend(result)
                except Exception as exc:
                    logging.error(f"Error for URL: {page_url}. Exception: {exc}")

            time.sleep(2)

    logging.info(f"Total broken images found: {len(broken_images)}")
    save_to_csv(broken_images, "broken_images_all_pages")

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main():
    """
    Prompt user to check a single page or all pages from a sitemap.
    """
    mode = input("Enter 'single' to check a single page or 'all' to check all pages: ").strip().lower()
    session = requests.Session()
    session.headers.update({'User-Agent': 'BrokenImageChecker/1.0'})

    if mode == 'single':
        check_single_page(session)
    elif mode == 'all':
        check_all_pages(session)
    else:
        logging.error("Invalid input. Enter 'single' or 'all'.")

# ---------------------------------------------------------------------------
# Script Execution
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    main()
