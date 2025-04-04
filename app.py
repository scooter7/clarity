import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import openai
import pandas as pd

# ✅ Load API key
try:
    openai.api_key = st.secrets["openai"]["api_key"]
except Exception:
    openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    st.error("⚠️ OpenAI API key not found. Set it in Railway ENV or Streamlit secrets.")
    st.stop()

st.title("🎓 Academic Program Scraper (Manual)")
st.caption("Crawls academic pages, extracts program names, and outputs structured spreadsheet.")

# Store session state
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
    homepage = st.text_input("Enter the institution homepage URL:")
    if homepage:
        st.session_state.homepage_url = homepage
        st.session_state.step = 3
        st.rerun()

# Step 3: Desired programs/departments
elif st.session_state.step == 3:
    info = st.text_area("Enter program names, levels (UG/MS/PhD), and departments (e.g. College of Engineering):")
    if info:
        st.session_state.program_info = info
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl and collect candidate URLs
elif st.session_state.step == 4:
    st.subheader("🔍 Step 1: Crawl Homepage for Academic URLs")
    if st.button("Crawl Site"):
        base = st.session_state.homepage_url
        visited = set()
        found_urls = []

        try:
            response = requests.get(base, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.startswith("http"):
                    href = urljoin(base, href)

                if base in href and href not in visited:
                    visited.add(href)

                    # Filter for likely academic pages
                    if any(keyword in href.lower() for keyword in ["program", "major", "degree", "academ", "study"]):
                        found_urls.append(href)

            st.session_state.found_urls = list(set(found_urls))
            if found_urls:
                st.success(f"✅ {len(found_urls)} URLs found!")
                for url in st.session_state.found_urls:
                    st.markdown(f"- [{url}]({url})")
                st.session_state.step = 5
                st.rerun()
            else:
                st.warning("No matching academic URLs found.")
        except Exception as e:
            st.error(f"Error while crawling: {e}")

# Step 5: Scrape pages and extract program names
elif st.session_state.step == 5:
    st.subheader("📄 Step 2: Extract Programs with GPT-4o-mini")

    if st.button("Extract Programs"):
        rows = []
        base_url = st.session_state.homepage_url

        for url in st.session_state.found_urls:
            try:
                html = requests.get(url, timeout=10).text
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n", strip=True)

                # Send to OpenAI for structured extraction
                prompt = (
                    f"You are analyzing a university page.\n"
                    f"Here is the text content:\n\n{text[:5000]}\n\n"  # limit tokens
                    f"From the above, extract a clean list of academic program names (UG/MS/PhD only).\n"
                    f"Output as a comma-separated list of just the program names."
                )

                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                answer = response.choices[0].message.content.strip()
                programs = re.split(r",|\n|•|-", answer)

                for prog in programs:
                    prog = prog.strip()
                    if prog:
                        relative = url.replace(base_url, "").lstrip("/")
                        pattern = "/" + relative.split("/")[0] + "/.*" if "/" in relative else "/" + relative
                        rows.append({
                            "Program": prog,
                            "Full URL": url,
                            "Relative Path": relative,
                            "Col D": "",
                            "Col E": "",
                            "Col F": "",
                            "Pattern": pattern
                        })

            except Exception as e:
                st.warning(f"❌ Failed to process {url}: {e}")

        if rows:
            df = pd.DataFrame(rows)
            st.session_state.result_df = df
            st.session_state.step = 6
            st.rerun()
        else:
            st.warning("No program data was extracted from any pages.")

# Step 6: Display and Download
elif st.session_state.step == 6:
    st.subheader("✅ Final Program Table")
    st.dataframe(st.session_state.result_df, use_container_width=True)

    csv = st.session_state.result_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, "programs.csv", "text/csv")
    st.balloons()
