#!/usr/bin/env python3
"""
scrape_aldi.py

Scrapes ALDI UK groceries and outputs a CSV of category, name, and price.
"""

import csv
import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
BASE_URL = "https://groceries.aldi.co.uk"
START_PATH = "/en-GB/groceries"
CSV_FILE = "aldi_uk_groceries.csv"
PAGE_LOAD_TIMEOUT = 10
PRODUCT_TILE_SELECTOR = "div.product-teaser-item"
CATEGORY_SELECTOR = "a.product-category-teaser-list-item"
COOKIE_BUTTON_SELECTOR = "button#onetrust-accept-btn-handler"


def configure_driver():
    """Configure and return a headless Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


def accept_cookies(driver, wait):
    """Accept the cookie banner if it appears."""
    try:
        button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, COOKIE_BUTTON_SELECTOR))
        )
        button.click()
    except Exception:
        pass


def get_category_urls(driver, wait):
    """Return a list of category page URLs from the homepage."""
    driver.get(urljoin(BASE_URL, START_PATH))
    accept_cookies(driver, wait)
    elements = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, CATEGORY_SELECTOR))
    )
    return [elem.get_attribute("href") for elem in elements]


def scrape_category(driver, wait, category_url):
    """
    Scrape all products from a single category by paging through until no more are found.
    Returns a list of product dicts.
    """
    products = []
    page = 1

    while True:
        url = f"{category_url}?page={page}" if page > 1 else category_url
        driver.get(url)

        try:
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_TILE_SELECTOR))
            )
        except Exception:
            break  # No items on this page

        tiles = driver.find_elements(By.CSS_SELECTOR, PRODUCT_TILE_SELECTOR)
        print(f"  Page {page}: found {len(tiles)} products")
        if not tiles:
            break

        for tile in tiles:
            name_el = tile.find_element(By.CSS_SELECTOR, "div.product-tile__name p")
            price_el = tile.find_element(
                By.CSS_SELECTOR,
                "div.product-tile__price .base-price__regular span"
            )
            products.append({
                "category": category_url.rstrip("/").split("/")[-1],
                "name": name_el.text.strip(),
                "price": price_el.text.strip(),
            })

        page += 1
        time.sleep(1)  # polite pause between pages

    return products


def save_to_csv(products, filename=CSV_FILE):
    """Save scraped products to a CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "name", "price"])
        writer.writeheader()
        writer.writerows(products)
    print(f"Done — exported {len(products)} products to {filename}")


def main():
    driver = configure_driver()
    wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)

    print("Retrieving category URLs...")
    categories = get_category_urls(driver, wait)
    print(f"Found {len(categories)} categories.")

    all_products = []
    for url in categories:
        print(f"Scraping category: {url}")
        all_products.extend(scrape_category(driver, wait, url))

    driver.quit()
    save_to_csv(all_products)


if __name__ == "__main__":
    main()
