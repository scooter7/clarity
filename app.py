import streamlit as st
from scrapegraphai.graphs import SmartScraperGraph
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

# ✅ Secure OpenAI API key
try:
    openai_api_key = st.secrets["openai"]["api_key"]
except Exception:
    openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("⚠️ OpenAI API key not found. Please set it as an environment variable on Railway.")
    st.stop()

st.title("Web Scraping AI Agent 🕵️‍♂️")
st.caption("Crawls institution websites like a human and extracts academic programs using GPT-4o-mini.")

graph_config = {
    "llm": {
        "api_key": openai_api_key,
        "model": "gpt-4o-mini",
    },
}

if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Institution name
if st.session_state.step == 1:
    name = st.text_input("Enter the institution name:")
    if name:
        st.session_state.institution_name = name
        st.session_state.step = 2
        st.rerun()

# Step 2: Homepage URL
elif st.session_state.step == 2:
    homepage = st.text_input("Enter the institution’s homepage URL (include https://):")
    if homepage:
        st.session_state.homepage_url = homepage
        st.session_state.step = 3
        st.rerun()

# Step 3: Program targets
elif st.session_state.step == 3:
    info = st.text_area("Enter programs, levels (UG, MS, PhD), and departments (e.g., College of Business):")
    if info:
        st.session_state.program_info = info
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl + Filter URLs
elif st.session_state.step == 4:
    st.subheader("Step 4: Crawl Website for Academic Pages")

    if st.button("Crawl Homepage"):
        base_url = st.session_state.homepage_url
        try:
            response = requests.get(base_url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            links = set()

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if base_url in full_url and not parsed.fragment and parsed.scheme.startswith("http"):
                    links.add(full_url)

            # Filter URLs likely to contain academic programs
            academic_links = [url for url in links if re.search(r"(program|major|minors|academics|degree)", url, re.IGNORECASE)]

            st.session_state.academic_links = list(academic_links)
            if academic_links:
                st.success(f"Found {len(academic_links)} academic-looking URLs:")
                for url in academic_links:
                    st.markdown(f"- [{url}]({url})")
                st.session_state.step = 5
                st.rerun()
            else:
                st.warning("No academic-related URLs found. Try a broader homepage.")
        except Exception as e:
            st.error(f"Failed to crawl homepage: {e}")

# Step 5: Extract Program Names with GPT
elif st.session_state.step == 5:
    st.subheader("Step 5: Extract Program Titles")

    if st.button("Run GPT Extraction"):
        programs = []
        for url in st.session_state.academic_links:
            prompt = (
                f"You are analyzing a university website. Extract the academic program name from this page. "
                f"Only return the text of the main academic program title (usually in an h1 or strong heading). "
                f"If multiple programs appear, return a list. URL: {url}"
            )

            try:
                scraper = SmartScraperGraph(prompt=prompt, source=url, config=graph_config)
                result = scraper.run()
                answer_text = result.get("answer", "") if isinstance(result, dict) else str(result)

                # Parse results
                for line in answer_text.splitlines():
                    line = line.strip()
                    if line:
                        programs.append((line, url))
            except Exception as e:
                st.warning(f"Skipping {url}: {e}")

        if programs:
            st.session_state.programs = programs
            st.session_state.step = 6
            st.rerun()
        else:
            st.warning("No programs were extracted. Try checking links manually.")

# Step 6: Show Table
elif st.session_state.step == 6:
    st.subheader("Final Output Table")

    if "programs" in st.session_state:
        base_url = st.session_state.homepage_url.rstrip("/")
        st.markdown("| Program | Full URL | Relative Path | Col D | Col E | Col F | Pattern |")
        st.markdown("|--------|----------|---------------|--------|--------|--------|---------|")
        for name, full_url in st.session_state.programs:
            relative = full_url.replace(base_url, "").lstrip("/")
            pattern = "/" + re.sub(r"-[^/]+$", "/.*", relative)
            st.markdown(f"| {name} | {full_url} | {relative} |  |  |  | {pattern} |")

    st.success("✅ Complete!")
    st.balloons()
