import streamlit as st
import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

st.title("Dynamic Academic Program Spreadsheet Generator")

st.write("Enter the base URL for academic programs, the HTML tag(s) to search for program titles, and select the maximum crawl depth.")
base_url = st.text_input("Enter base URL", value="https://admissions.msu.edu/academics/majors-degrees-programs")
title_tags_input = st.text_input("Title tags to search", value="h1")
max_depth = st.selectbox("Select maximum crawl depth", [1, 2, 3, 4, 5], index=1)

def scroll_page(driver, pause_time=2):
    """Scroll to the bottom of the page until no more content loads."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

if st.button("Create Spreadsheet"):
    if not base_url:
        st.error("Please enter a valid base URL.")
    else:
        st.write("Crawling the website dynamically. This may take some time...")

        # Set up Selenium Chromium in headless mode.
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Use the installed Chromium binary (adjust path if needed)
        chrome_options.binary_location = "/usr/bin/chromium"

        # Force webdriver-manager to get the driver matching Chrome version 120.
        service = Service(ChromeDriverManager(driver_version="120.0.6099.224").install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(180)

        # Convert the comma-separated title tags into a list.
        title_tags = [tag.strip() for tag in title_tags_input.split(",") if tag.strip()]

        def crawl_website_dynamic(base_url, max_depth):
            """
            Crawl pages under the base URL using Selenium (with scrolling)
            up to a given depth while skipping URLs with forbidden keywords.
            """
            forbidden_keywords = ["faculty", "catalog", "directory"]
            visited = set()
            to_crawl = [(base_url, 0)]
            while to_crawl:
                current_url, depth = to_crawl.pop(0)
                if any(keyword in current_url.lower() for keyword in forbidden_keywords):
                    continue
                if current_url in visited:
                    continue
                visited.add(current_url)
                try:
                    driver.get(current_url)
                    # Wait for the page to load and simulate scrolling.
                    time.sleep(2)
                    scroll_page(driver, pause_time=2)
                    html = driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                    if depth < max_depth:
                        # Look for all links on the page.
                        for a in soup.find_all("a", href=True):
                            href = a["href"]
                            full_url = urljoin(base_url, href)
                            # Only consider links that start with the base URL.
                            if full_url.startswith(base_url) and full_url not in visited:
                                if not any(keyword in full_url.lower() for keyword in forbidden_keywords):
                                    to_crawl.append((full_url, depth + 1))
                except Exception as e:
                    st.write(f"Error crawling {current_url}: {e}")
            return visited

        all_urls = crawl_website_dynamic(base_url, max_depth)
        st.write(f"Found {len(all_urls)} pages. Extracting program information...")

        # Use the last element of the base URL's path for columns C and G.
        parsed = urlparse(base_url)
        base_path = parsed.path.rstrip("/")
        base_last = base_path.split("/")[-1] if base_path else ""

        results = []
        for url in all_urls:
            try:
                driver.get(url)
                time.sleep(2)
                scroll_page(driver, pause_time=2)
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                # Try to extract the program title using the specified tags.
                program_title = None
                for tag in title_tags:
                    candidate = soup.select_one(tag)
                    if candidate and candidate.get_text(strip=True):
                        program_title = candidate.get_text(strip=True)
                        break

                if program_title:
                    raw_suffix = url.replace(base_url, "").lstrip("/")
                    if raw_suffix:
                        suffix = f"{base_last}/{raw_suffix}"
                        parts = raw_suffix.split("/")
                        if parts:
                            program_slug = parts[-1]
                            if "-" in program_slug:
                                suffix_end = program_slug.split("-")[-1]
                                pattern = f"/{base_last}/.*{suffix_end}"
                            else:
                                pattern = f"/{base_last}/.*"
                        else:
                            pattern = f"/{base_last}/.*"
                        results.append({
                            "A": program_title,
                            "B": url,
                            "C": suffix,
                            "D": "",
                            "E": "",
                            "F": "",
                            "G": pattern
                        })
            except Exception as e:
                st.write(f"Error processing {url}: {e}")

        driver.quit()

        if results:
            df = pd.DataFrame(results)
            st.write("Spreadsheet created. Here is a preview:")
            st.dataframe(df)
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="academic_programs.csv",
                mime="text/csv"
            )
        else:
            st.write("No academic program pages were found with the specified criteria.")
