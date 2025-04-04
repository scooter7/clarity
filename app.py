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
st.caption("Crawls and extracts academic program pages using your filters.")

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

# Step 4: Crawl and match links
elif st.session_state.step == 4:
    st.subheader("Step 4: Crawl homepage for matching links")

    if st.button("Crawl and Find Academic Pages"):
        homepage = st.session_state.homepage_url
        try:
            r = requests.get(homepage, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            found = set()
            matched = set()

            filters = [f.strip().lower() for f in st.session_state.user_filters.split(",")]

            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text().strip().lower()
                full = urljoin(homepage, href)
                parsed = urlparse(full)

                if homepage in full and parsed.scheme.startswith("http"):
                    found.add(full)

                    if any(f in text or f in href.lower() for f in filters):
                        matched.add(full)

            # Decide what to show
            if matched:
                st.session_state.filtered_links = list(matched)
                st.success(f"✅ Found {len(matched)} matching links:")
            else:
                st.warning("⚠️ No links matched your filters. Showing all links instead.")
                st.session_state.filtered_links = list(found)

            for url in st.session_state.filtered_links:
                st.markdown(f"- [{url}]({url})")

            st.session_state.step = 5
            st.rerun()

        except Exception as e:
            st.error(f"Failed to crawl homepage: {e}")

# Step 5: Extract program names using GPT
elif st.session_state.step == 5:
    st.subheader("Step 5: Use GPT to extract program names")

    if st.button("Extract Program Names"):
        output = []
        base_url = st.session_state.homepage_url.rstrip("/")
        filters = st.session_state.user_filters

        for url in st.session_state.filtered_links:
            try:
                res = requests.get(url, timeout=10)
                html_text = BeautifulSoup(res.text, "html.parser").prettify()

                system_msg = "You are a helpful assistant extracting academic program titles from web pages."
                user_msg = (
                    f"Here is the HTML of a university page. "
                    f"The user is interested in: {filters}. "
                    f"Return only the name(s) of the academic program(s) listed on the page. "
                    f"Use text from <h1> or similar prominent heading tags if available.\n\n"
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
            st.warning("No programs were extracted.")

# Step 6: Final table
elif st.session_state.step == 6:
    st.subheader("✅ Final Program Table")

    st.markdown("| Program | Full URL | Relative Path | Col D | Col E | Col F | Pattern |")
    st.markdown("|---------|----------|---------------|--------|--------|--------|---------|")

    for row in st.session_state.program_output:
        st.markdown(f"| {row[0]} | {row[1]} | {row[2]} |  |  |  | {row[6]} |")

    st.balloons()
