import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import openai

# Get OpenAI key from environment or secrets
try:
    openai_api_key = st.secrets["openai"]["api_key"]
except Exception:
    openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("❌ OpenAI API key missing.")
    st.stop()

openai.api_key = openai_api_key

st.title("🎓 Academic Program Scraper")
st.caption("Find program pages using your own filters — no browser needed.")

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

# Step 3: Desired program filters
elif st.session_state.step == 3:
    filters = st.text_area("What programs, levels, or departments are you looking for?")
    if filters:
        st.session_state.user_filters = filters
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl site for matching URLs
elif st.session_state.step == 4:
    st.subheader("Step 4: Crawl homepage for links")

    if st.button("Crawl and Find Academic Pages"):
        homepage = st.session_state.homepage_url
        try:
            r = requests.get(homepage, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            found = set()

            for a in soup.find_all("a", href=True):
                href = a["href"]
                full = urljoin(homepage, href)
                parsed = urlparse(full)
                if homepage in full and parsed.scheme.startswith("http"):
                    found.add(full)

            # Filter based on user filters
            filters = st.session_state.user_filters.lower().split(",")
            filtered_links = [link for link in found if any(f.strip() in link.lower() for f in filters)]

            if filtered_links:
                st.session_state.filtered_links = filtered_links
                st.success(f"Found {len(filtered_links)} links based on your filter:")
                for link in filtered_links:
                    st.markdown(f"- [{link}]({link})")
                st.session_state.step = 5
                st.rerun()
            else:
                st.warning("No matching links found. Try broadening your keywords.")
        except Exception as e:
            st.error(f"Failed to crawl homepage: {e}")

# Step 5: Use GPT to extract program names
elif st.session_state.step == 5:
    st.subheader("Step 5: Use GPT to extract program names from matching pages")

    if st.button("Extract Programs"):
        output = []
        base_url = st.session_state.homepage_url.rstrip("/")
        filters = st.session_state.user_filters

        for url in st.session_state.filtered_links:
            try:
                res = requests.get(url, timeout=10)
                html_text = BeautifulSoup(res.text, "html.parser").prettify()

                system_msg = "You are a helpful assistant extracting academic program titles from web pages."
                user_msg = (
                    f"Here is the HTML content of a page from a university website. "
                    f"The user is looking for programs related to: {filters}. "
                    f"Please return ONLY the program name or title(s) that this page represents. "
                    f"Use the exact text found in <h1> or similar heading tags if possible.\n\n"
                    f"{html_text[:3000]}..."  # truncate to avoid token limits
                )

                completion = openai.ChatCompletion.create(
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
                st.warning(f"Skipped {url}: {e}")

        if output:
            st.session_state.program_output = output
            st.session_state.step = 6
            st.rerun()
        else:
            st.warning("No programs could be extracted.")

# Step 6: Display final table
elif st.session_state.step == 6:
    st.subheader("✅ Final Program Table")

    st.markdown("| Program | Full URL | Relative Path | Col D | Col E | Col F | Pattern |")
    st.markdown("|---------|----------|---------------|--------|--------|--------|---------|")

    for row in st.session_state.program_output:
        st.markdown(f"| {row[0]} | {row[1]} | {row[2]} |  |  |  | {row[6]} |")

    st.balloons()
