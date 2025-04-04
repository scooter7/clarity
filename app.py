import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import pandas as pd

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup Streamlit UI
st.set_page_config(page_title="Academic Program Scraper", layout="wide")
st.title("🎓 Academic Program Scraper")
st.caption("Find Masters and PhD programs from specific departments using real-time web crawling.")

# Step tracker
if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Institution name
if st.session_state.step == 1:
    name = st.text_input("Enter the institution name:")
    if name:
        st.session_state.institution = name
        st.session_state.step = 2
        st.rerun()

# Step 2: Homepage URL
elif st.session_state.step == 2:
    homepage = st.text_input("Enter the institution’s homepage URL:")
    if homepage:
        st.session_state.homepage = homepage
        st.session_state.step = 3
        st.rerun()

# Step 3: Program request details + crawl depth
elif st.session_state.step == 3:
    criteria = st.text_area("Enter your program search request (e.g. Masters and PhD programs in Engineering, Medicine, etc.):")
    depth = st.selectbox("Crawl depth (max pages to scan):", [50, 100, 200, 300], index=2)
    if criteria:
        st.session_state.criteria = criteria
        st.session_state.depth = depth
        st.session_state.step = 4
        st.rerun()

# Step 4: Crawl function
def get_links(base_url, max_pages=200):
    visited = set()
    to_visit = [base_url]
    found = set()
    status = st.empty()
    counter = 0

    while to_visit and counter < max_pages:
        url = to_visit.pop()
        if url in visited or not url.startswith(base_url):
            continue
        visited.add(url)
        counter += 1
        status.markdown(f"🔍 Crawling ({counter})... `{url}`")
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")
            for tag in soup.find_all("a", href=True):
                full = urljoin(url, tag["href"])
                parsed = urlparse(full)
                clean = parsed.scheme + "://" + parsed.netloc + parsed.path
                if clean not in visited and base_url in clean:
                    found.add(clean)
                    to_visit.append(clean)
        except:
            continue
    status.markdown(f"✅ Done crawling. Found {len(found)} pages.")
    return list(found)

# Step 4: Run the crawl
if st.session_state.step == 4:
    st.subheader("🔍 Crawling site for program pages...")
    with st.spinner("Scanning website..."):
        links = get_links(st.session_state.homepage, max_pages=st.session_state.depth)
    if links:
        st.session_state.links = links
        st.session_state.step = 5
        st.rerun()
    else:
        st.error("No links found. Check your homepage URL.")

# Step 5: Process each link with OpenAI
elif st.session_state.step == 5:
    st.subheader("🎯 Filtering and extracting program information...")
    with st.spinner("Processing links..."):

        results = []
        for link in st.session_state.links:
            try:
                res = requests.get(link, timeout=10)
                if res.status_code != 200:
                    continue
                content = res.text[:3000]

                system_prompt = (
                    "You are a helpful assistant that finds academic programs in web content. "
                    "Your job is to determine if this HTML content describes an academic program that matches the user's request. "
                    "Only include exact program names, each on its own line."
                )

                user_prompt = f"""User's request:
{st.session_state.criteria}

HTML content:
{content}

Return the list of matching program names, one per line. If none found, return "None".
"""

                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )

                answer = response.choices[0].message.content.strip()

                if answer.lower() != "none":
                    for line in answer.split("\n"):
                        program = line.strip("•-– \t")
                        if program:
                            relative = link.replace(st.session_state.homepage, "").lstrip("/")
                            pattern = "/" + "/".join(relative.split("/")[:-1]) + "/.*"
                            results.append([program, link, relative, "", "", "", pattern])
            except Exception:
                continue

        if results:
            df = pd.DataFrame(results, columns=["Program", "Full URL", "Relative Path", "Col D", "Col E", "Col F", "Pattern"])
            st.success("✅ Final Program Table")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", csv, "programs.csv", "text/csv")
        else:
            st.warning("No matching programs were found. Try broadening your request.")
