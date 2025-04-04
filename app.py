import streamlit as st
from scrapegraphai.graphs import SmartScraperGraph
import os
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
st.caption("Scrape academic program info from institution websites using GPT-4o-mini.")

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
    homepage = st.text_input("Enter the institution’s homepage URL:")
    if homepage:
        st.session_state.homepage_url = homepage
        st.session_state.step = 3
        st.rerun()

# Step 3: Programs, levels, departments
elif st.session_state.step == 3:
    info = st.text_area("Enter program names, levels (UG, MS, PhD), and departments (e.g. College of Business):")
    if info:
        st.session_state.program_info = info
        st.session_state.step = 4
        st.rerun()

# Step 4: Scrape for links
elif st.session_state.step == 4:
    st.subheader("Validate URLs")
    st.write("Click below to list discovered academic program URLs. Then manually test to ensure none are 404s.")
    
    if st.button("List URLs"):
        prompt = (
            f"Scrape {st.session_state.homepage_url} for program pages related to: "
            f"{st.session_state.program_info}. Return valid academic program URLs (no 404s)."
        )
        scraper = SmartScraperGraph(
            prompt=prompt,
            source=st.session_state.homepage_url,
            config=graph_config
        )

        try:
            result = scraper.run()
            answer_text = result.get("answer", "") if isinstance(result, dict) else str(result)

            st.markdown("### 🔍 Raw Output from Scraper")
            st.code(answer_text)

            # Extract all valid-looking URLs
            urls = re.findall(r'https?://[^\s\)\]]+', answer_text)

            if urls:
                st.session_state.urls = urls
                st.success("✅ Test these URLs before proceeding:")
                for url in urls:
                    st.markdown(f"- [{url}]({url})")
                st.session_state.step = 5
                st.rerun()
            else:
                st.warning("No URLs matched. Check the raw output above.")
        except Exception as e:
            st.error(f"Scraping failed: {e}")

# Step 5: Generate table
elif st.session_state.step == 5:
    st.subheader("Generate Tabular Output")
    st.write("Creates a table with program names, URLs, and structured patterns.")

    if st.button("Create Tabular Output"):
        prompt = (
            f"From {st.session_state.homepage_url}, return a Markdown table with:\n"
            f"Column A: Program name (h1 tag or similar)\n"
            f"Column B: Full valid URL\n"
            f"Column C: Relative path after base URL\n"
            f"Columns D–F: Leave blank\n"
            f"Column G: Pattern based on C (e.g., /majors/.*bs)"
        )
        scraper = SmartScraperGraph(
            prompt=prompt,
            source=st.session_state.homepage_url,
            config=graph_config
        )

        try:
            result = scraper.run()
            answer_text = result.get("answer", "") if isinstance(result, dict) else str(result)

            st.markdown("### 📋 Raw Tabular Output")
            st.code(answer_text)

            if "|" in answer_text and "---" in answer_text:
                st.markdown("### ✅ Parsed Markdown Table")
                st.markdown(answer_text)
                st.session_state.step = 6
                st.rerun()
            else:
                st.warning("No valid Markdown table format detected. Check the output above.")
        except Exception as e:
            st.error(f"Tabular output failed: {e}")

# Step 6: Done
elif st.session_state.step == 6:
    st.success("✅ Scraping and table complete!")
    st.balloons()
