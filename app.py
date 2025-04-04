import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import openai

# Securely load OpenAI key
try:
    openai_api_key = st.secrets["openai"]["api_key"]
except Exception:
    openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("❌ OpenAI API key missing.")
    st.stop()

openai.api_key = openai_api_key

st.title("🎓 Academic Program Scraper")
st.caption("Find real program pages by crawling university sites intelligently.")

# Allow/Deny filters
ALLOW_PATTERNS = ["program", "academic", "major", "minor", "undergrad", "graduate", "degree", "school-of"]
DENY_PATTERNS = ["privacy", "contact", "career", "give", "equity", "library", "news", "event", "login", "policy", "map", "campus-life", "terms", "directory"]

def is_relevant_link(href: str, text: str):
    href_l = href.lower()
    text_l = text.lower()

    if any(p in href_l for p in DENY_PATTERNS):
        return False
    return any(p in href_l or p in text_l for p in ALLOW_PATTERNS)

# Step manager
if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Institution name
if st.session_state.step == 1:
    name = st.text_input("Institution name:")
    if name:
        st.session_state.institution_name = name
        st.session_state.step = 2
        st.rerun()

# Step 2: Homepage URL
elif st.session_state.step == 2:
    url = st.text_input("Homepage URL (include https://):")
    if url:
        st.session_state.homepage_url = url
        st.session_state.step = 3
        st.rerun()

# Step 3: Filters
elif st.session_state.step == 3:
    filters = st.text_area("What programs, levels, or departments are you looking for?\nExample: Engineering, Business, Computer Science, Undergraduate")
    if filters:
        st.session_state.user_filters = filters
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl homepage + filter links
elif st.session_state.step == 4:
    st.subheader("Step 4: Crawl homepage for relevant links")

    if st.button("Find Academic Pages"):
        homepage = st.session_state.homepage_url
        try:
            r = requests.get(homepage, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            base = homepage.rstrip("/")
            found = set()

            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text().strip()
                full_url = urljoin(homepage, href)
                parsed = urlparse(full_url)

                if base in full_url and parsed.scheme.startswith("http"):
                    if is_relevant_link(href, text):
                        found.add(full_url)

            if found:
                st.session_state.filtered_links = list(found)
                st.success(f"✅ {len(found)} likely academic links found:")
                for url in st.session_state.filtered_links:
                    st.markdown(f"- [{url}]({url})")
                st.session_state.step = 5
                st.rerun()
            else:
                st.warning("⚠️ No academic pages found. Try adjusting the homepage or keywords.")
        except Exception as e:
            st.error(f"Crawling failed: {e}")

# Step 5: GPT analysis
elif st.session_state.step == 5:
    st.subheader("Step 5: Extract program titles with GPT")

    if st.button("Extract Programs"):
        output = []
        base_url = st.session_state.homepage_url.rstrip("/")
        filters = st.session_state.user_filters

        for url in st.session_state.filtered_links:
            try:
                res = requests.get(url, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")
                h1s = soup.find_all("h1")
                if not h1s or len(soup.get_text()) < 300:
                    continue

                html_text = soup.prettify()

                system_msg = "You are a helpful assistant extracting academic program titles from university websites."
                user_msg = (
                    f"Here is the HTML content of a page. "
                    f"The user is interested in programs related to: {filters}. "
                    f"Extract the program name(s) listed on this page using <h1> or similar heading tags.\n\n"
                    f"{html_text[:3000]}..."
                )

                completion = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.2
                )

                result = completion.choices[0].message.content.strip()
                relative_path = url.replace(base_url, "").lstrip("/")
                pattern = "/" + re.sub(r"-[^/]+$", "/.*", relative_path)

                output.append((result, url, relative_path, "", "", "", pattern))

            except Exception as e:
                st.warning(f"⚠️ Skipped {url}: {e}")

        if output:
            st.session_state.program_output = output
            st.session_state.step = 6
            st.rerun()
        else:
            st.warning("No valid programs extracted. Try with more relevant links.")

# Step 6: Display final table
elif st.session_state.step == 6:
    st.subheader("✅ Final Program Table")

    st.markdown("| Program | Full URL | Relative Path | Col D | Col E | Col F | Pattern |")
    st.markdown("|---------|----------|---------------|--------|--------|--------|---------|")

    for row in st.session_state.program_output:
        st.markdown(f"| {row[0]} | {row[1]} | {row[2]} |  |  |  | {row[6]} |")

    st.balloons()
