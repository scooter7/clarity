import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import openai
import pandas as pd

# ✅ Get OpenAI API key from Railway environment variable or secrets
openai.api_key = (
    st.secrets["openai"]["api_key"]
    if "openai" in st.secrets and "api_key" in st.secrets["openai"]
    else os.getenv("OPENAI_API_KEY")
)

if not openai.api_key:
    st.error("⚠️ OpenAI API key not found. Add it to Railway environment variables or Streamlit secrets.")
    st.stop()

# ✅ UI Setup
st.title("🎯 Granular Program Page Finder")
st.caption("Find Master's and PhD program pages from specified schools and departments.")

# Step-by-step input flow
if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Institution Name
if st.session_state.step == 1:
    inst = st.text_input("Enter the institution name:")
    if inst:
        st.session_state.institution_name = inst
        st.session_state.step = 2
        st.rerun()

# Step 2: Homepage URL
elif st.session_state.step == 2:
    homepage = st.text_input("Enter the homepage URL of the institution:")
    if homepage:
        st.session_state.homepage = homepage
        st.session_state.step = 3
        st.rerun()

# Step 3: Program levels and departments
elif st.session_state.step == 3:
    criteria = st.text_area(
        "Enter what you're looking for (e.g., Master's and PhD programs from the School of Engineering, School of Medicine...)"
    )
    if criteria:
        st.session_state.criteria = criteria
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl and analyze
elif st.session_state.step == 4:
    st.info("🔍 Crawling and analyzing the site...")

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

    with st.spinner("Crawling the site for pages..."):
        all_links = get_links(st.session_state.homepage)

    st.success(f"🔗 Found {len(all_links)} URLs")
    st.session_state.crawled_links = all_links
    st.session_state.step = 5
    st.rerun()

# Step 5: Use OpenAI to filter & extract actual program pages
elif st.session_state.step == 5:
    st.info("🔎 Filtering program-level pages using OpenAI...")

    links = st.session_state.crawled_links
    criteria = st.session_state.criteria
    base_url = st.session_state.homepage

    valid_programs = []

    with st.spinner("Querying OpenAI to find matching programs..."):
        for link in links:
            try:
                res = requests.get(link, timeout=10)
                if res.status_code != 200 or not res.text.strip():
                    continue

                prompt = f"""
You are a university website analysis agent.

Please extract the names of individual **Master's or PhD programs** only if the page corresponds to the user's instruction below:

--- USER REQUEST ---
{criteria}
---------------------

Do not include general pages, only pages that list or describe individual programs. Use only H1, H2, or meaningful headings/titles. Format each result as:

Program Name 1
Program Name 2
...
                
Return only valid program names that match the user request, or return "NONE" if the page is irrelevant.
"""

                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You extract academic program names from university pages."},
                        {"role": "user", "content": prompt + "\n\nPage HTML:\n" + res.text[:7000]},
                    ],
                    temperature=0.3,
                )

                result_text = response.choices[0].message.content.strip()

                if result_text.lower().startswith("none"):
                    continue

                programs = [line.strip("-• ") for line in result_text.split("\n") if line.strip()]
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
        st.warning("❌ No valid programs found. Try adjusting your criteria.")
    else:
        df = pd.DataFrame(valid_programs)
        st.session_state.final_df = df
        st.session_state.step = 6
        st.rerun()

# Step 6: Final Table Output
elif st.session_state.step == 6:
    df = st.session_state.final_df
    st.success("✅ Final Program Table")
    st.dataframe(df)

    csv = df.to_csv(index=False)
    st.download_button("📥 Download CSV", csv, "program_table.csv", "text/csv")

    st.balloons()
