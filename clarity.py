import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Set up the OpenAI API key from Streamlit secrets
import openai
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Flexible Academic Program URL Extractor")

st.write("Upload your reference CSV file (if needed) and enter the base URL for academic programs.")
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
base_url = st.text_input("Enter base URL", value="https://www.ithaca.edu/academics")

st.markdown("**Title Tag Flexibility:** Enter a comma-separated list of HTML tags (or CSS selectors) to look for a program title. For example: `h1,h2,div.program-title`")
title_tags_input = st.text_input("Title tags to search", value="h1,h2")

if st.button("Run Extraction"):
    if not base_url:
        st.error("Please enter a valid base URL.")
    else:
        st.write("Crawling the website—this may take a few moments...")

        # Convert the comma-separated list into a list of tags/selectors
        title_tags = [tag.strip() for tag in title_tags_input.split(",") if tag.strip()]
        
        def crawl_website(base_url, max_depth=2):
            """
            Crawl pages under the base URL up to a given depth while skipping URLs
            containing forbidden keywords like 'faculty', 'catalog', or 'directory'.
            """
            forbidden_keywords = ["faculty", "catalog", "directory"]
            visited = set()
            to_crawl = [(base_url, 0)]
            while to_crawl:
                url, depth = to_crawl.pop(0)
                # Skip URLs that contain any forbidden keyword
                if any(keyword in url.lower() for keyword in forbidden_keywords):
                    continue
                if url in visited:
                    continue
                visited.add(url)
                if depth < max_depth:
                    try:
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            for a in soup.find_all("a", href=True):
                                href = a["href"]
                                full_url = urljoin(base_url, href)
                                # Only follow links that start with the base URL and do not contain forbidden keywords
                                if full_url.startswith(base_url) and full_url not in visited:
                                    if not any(keyword in full_url.lower() for keyword in forbidden_keywords):
                                        to_crawl.append((full_url, depth + 1))
                    except Exception as e:
                        st.write(f"Error crawling {url}: {e}")
            return visited

        all_urls = crawl_website(base_url, max_depth=2)
        st.write(f"Found {len(all_urls)} pages. Now extracting program information...")

        results = []
        for url in all_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Try each provided tag until a valid title is found
                    program_title = None
                    for tag in title_tags:
                        # Use select_one to allow for CSS selectors too (like div.program-title)
                        candidate = soup.select_one(tag)
                        if candidate and candidate.get_text(strip=True):
                            program_title = candidate.get_text(strip=True)
                            break

                    if program_title:
                        # Compute the URL suffix (i.e. the part after the base URL)
                        suffix = url.replace(base_url, "").lstrip("/")
                        parts = suffix.split("/")
                        # Process only pages that have a non-empty suffix with two segments (directory/program_slug)
                        if suffix and "-" in suffix and len(parts) == 2:
                            directory = parts[0]
                            program_slug = parts[1]
                            # Build the regex pattern based on the text after the last dash in the program slug
                            if "-" in program_slug:
                                suffix_end = program_slug.split("-")[-1]
                                pattern = f"/{directory}/.*{suffix_end}"
                            else:
                                pattern = f"/{directory}/.*"
                            
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

        if results:
            df = pd.DataFrame(results)
            st.write("Extraction complete. Here is a preview:")
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
