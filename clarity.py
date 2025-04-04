import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

st.title("Academic Program Spreadsheet Generator")

st.write("Enter the base URL for academic programs and a comma-separated list of title tags (or CSS selectors).")
base_url = st.text_input("Enter base URL", value="https://www.ithaca.edu/academics")

st.markdown("**Title Tag Flexibility:** Specify a comma-separated list of HTML tags or CSS selectors to locate the program title. For example: `h1,h2,div.program-title`")
title_tags_input = st.text_input("Title tags to search", value="h1,h2")

if st.button("Create Spreadsheet"):
    if not base_url:
        st.error("Please enter a valid base URL.")
    else:
        st.write("Crawling the website—this may take a few moments...")

        # Convert the comma-separated string into a list of tags/selectors.
        title_tags = [tag.strip() for tag in title_tags_input.split(",") if tag.strip()]

        def crawl_website(base_url, max_depth=2):
            """
            Crawl pages under the base URL up to a specified depth while skipping URLs
            that contain forbidden keywords like 'faculty', 'catalog', or 'directory'.
            """
            forbidden_keywords = ["faculty", "catalog", "directory"]
            visited = set()
            to_crawl = [(base_url, 0)]
            while to_crawl:
                url, depth = to_crawl.pop(0)
                if any(keyword in url.lower() for keyword in forbidden_keywords):
                    continue
                if url in visited:
                    continue
                visited.add(url)
                if depth < max_depth:
                    try:
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")
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
        st.write(f"Found {len(all_urls)} pages. Extracting program information...")

        results = []
        for url in all_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    # Try each provided tag until a valid title is found
                    program_title = None
                    for tag in title_tags:
                        candidate = soup.select_one(tag)
                        if candidate and candidate.get_text(strip=True):
                            program_title = candidate.get_text(strip=True)
                            break

                    if program_title:
                        # Compute the URL suffix (the part after the base URL)
                        suffix = url.replace(base_url, "").lstrip("/")
                        parts = suffix.split("/")
                        # Process only pages with a suffix that has two segments (e.g. "majors-minors/acting-bfa")
                        if suffix and "-" in suffix and len(parts) == 2:
                            directory = parts[0]
                            program_slug = parts[1]
                            # Create the regex pattern from the text after the last dash of the program slug.
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
