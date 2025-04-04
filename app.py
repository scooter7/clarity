import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import openai
import pandas as pd

# ✅ Get OpenAI API key from Railway environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY")

if not openai.api_key:
    st.error("⚠️ OpenAI API key not found. Set OPENAI_API_KEY as an environment variable on Railway.")
    st.stop()

# App UI
st.title("🎯 Academic Program Page Finder")
st.caption("Find Master’s and PhD programs from specific schools/departments on university websites using GPT-4o.")

# Step state
if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Institution Name
if st.session_state.step == 1:
    name = st.text_input("Enter the institution name:")
    if name:
        st.session_state.institution_name = name
        st.session_state.step = 2
        st.rerun()

# Step 2: Homepage URL
elif st.session_state.step == 2:
    homepage = st.text_input("Enter the homepage URL of the institution:")
    if homepage:
        st.session_state.homepage = homepage
        st.session_state.step = 3
        st.rerun()

# Step 3: Program Criteria
elif st.session_state.step == 3:
    criteria = st.text_area(
        "What are you looking for?\n\nExample: “I want Master's and PhD programs only from the School of Engineering, School of Medicine, Weatherhead School of Management, and Mandel School of Applied Social Sciences.”"
    )
    if criteria:
        st.session_state.criteria = criteria
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl site
elif st.session_state.step == 4:
    st.info("🔍 Crawling the site...")

    def get_links(base_url):
        visited = set()
        to_visit = [base_url]
        found_urls = set()

        while to_visit:
            url = to_visit.pop()
            if url in visited or not url.startswith(base_url):
                continue
            visited.add(url)

            try:
                res = requests.get(url, timeout=10)
                if res.status_code != 200:
                    continue
                soup = BeautifulSoup(res.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    full_url = urljoin(url, a["href"])
                    parsed = urlparse(full_url)
                    cleaned_url = parsed.scheme + "://" + parsed.netloc + parsed.path
                    if cleaned_url not in visited and base_url in cleaned_url:
                        found_urls.add(cleaned_url)
                        to_visit.append(cleaned_url)
            except Exception:
                continue

        return list(found_urls)

    with st.spinner("Finding all internal URLs..."):
        links = get_links(st.session_state.homepage)

    st.success(f"🔗 Found {len(links)} URLs")
    st.session_state.crawled_links = links
    st.session_state.step = 5
    st.rerun()

# Step 5: Use GPT to filter program pages
elif st.session_state.step == 5:
    st.info("🧠 Filtering program-level pages using OpenAI...")

    criteria = st.session_state.criteria
    base_url = st.session_state.homepage
    valid_programs = []

    with st.spinner("Reviewing each page..."):
        for link in st.session_state.crawled_links:
            try:
                res = requests.get(link, timeout=10)
                if res.status_code != 200 or not res.text.strip():
                    continue

                prompt = f"""
You are helping a university researcher extract specific program pages.

Only return Master's or PhD programs **that match the user's request**. Ignore general landing pages or unrelated programs.

--- USER REQUEST ---
{criteria}
---------------------

Only return matching program titles from the HTML content provided.

Return:
Program Name 1
Program Name 2
...

Or return "NONE" if nothing matches.
"""

                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You extract program names from university webpages."},
                        {"role": "user", "content": prompt + "\n\nHTML Content:\n" + res.text[:6000]},
                    ],
                    temperature=0.2,
                )

                text = response.choices[0].message.content.strip()

                if text.lower().startswith("none"):
                    continue

                programs = [line.strip("-• ").strip() for line in text.split("\n") if line.strip()]
                if not programs:
                    continue

                rel_path = re.sub(r'^https?://[^/]+', '', link)
                pattern = '/' + '/'.join(rel_path.strip('/').split('/')[:-1]) + '/.*'

                for prog in programs:
                    valid_programs.append({
                        "Program": prog,
                        "Full URL": link,
                        "Relative Path": rel_path,
                        "Col D": "",
                        "Col E": "",
                        "Col F": "",
                        "Pattern": pattern
                    })

            except Exception:
                continue

    if not valid_programs:
        st.warning("❌ No matching program pages found. Try broadening your criteria.")
    else:
        df = pd.DataFrame(valid_programs)
        st.session_state.final_df = df
        st.session_state.step = 6
        st.rerun()

# Step 6: Show and export results
elif st.session_state.step == 6:
    st.success("✅ Final Program Table")
    df = st.session_state.final_df
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False)
    st.download_button("📥 Download as CSV", csv, "programs_output.csv", "text/csv")

    st.balloons()
