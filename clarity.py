import streamlit as st
import pandas as pd
import time
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

if st.button("Create Spreadsheet"):
    if not base_url:
        st.error("Please enter a valid base URL.")
    else:
        st.write("Crawling the website dynamically. This may take some time...")

        # Set up Selenium Chrome (Chromium) in headless mode using a Service.
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Set the binary location to the correct path on Streamlit Cloud.
        chrome_options.binary_location = "/usr/bin/chromium"

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Convert the comma-separated title tags into a list.
        title_tags = [tag.strip() for tag in title_tags_input.split(",") if tag.strip()]

        def crawl_website_dynamic(base_url, max_depth):
            """
            Crawl pages under the base URL using Selenium (to render JavaScript)
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
                    time.sleep(2)  # wait for dynamic content to load
                    html = driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                    if depth < max_depth:
                        for a in soup.find_all("a", href=True):
                            href = a["href"]
                            full_url = urljoin(base_url, href)
                            if full_url.startswith(base_url) and full_url not in visited:
                                if not any(keyword in full_url.lower() for keyword in forbidden_keywords):
                                    to_crawl.append((full_url, depth + 1))
                except Exception as e:
                    st.write(f"Error crawling {current_url}: {e}")
            return visited

        all_urls = crawl_website_dynamic(base_url, max_depth)
        st.write(f"Found {len(all_urls)} pages. Extracting program information...")

        # Determine the last element of the base URL's path for use in columns C and G.
        parsed = urlparse(base_url)
        base_path = parsed.path.rstrip("/")
        base_last = base_path.split("/")[-1] if base_path else ""

        results = []
        for url in all_urls:
            try:
                driver.get(url)
                time.sleep(2)  # allow dynamic content to load
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                # Look for a program title using one of the specified tags.
                program_title = None
                for tag in title_tags:
                    candidate = soup.select_one(tag)
                    if candidate and candidate.get_text(strip=True):
                        program_title = candidate.get_text(strip=True)
                        break

                if program_title:
                    # Compute the raw URL suffix (the part after the base URL)
                    raw_suffix = url.replace(base_url, "").lstrip("/")
                    if raw_suffix:
                        # Prepend the last element from the base URL to form column C.
                        suffix = f"{base_last}/{raw_suffix}"
                        parts = raw_suffix.split("/")
                        if parts:
                            program_slug = parts[-1]
                            # Create the regex pattern using base_last as the directory.
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
