import streamlit as st
from scrapegraphai.graphs import SmartScraperGraph

# Debug: Display Streamlit version
st.write("Streamlit version:", st.__version__)

# Safe rerun for compatibility with different Streamlit versions
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.warning("Please refresh the page manually to proceed.")

# Title and intro
st.title("Web Scraping AI Agent 🕵️‍♂️")
st.caption("Scrape institution websites using GPT-4o-mini on Streamlit Cloud.")

# Load OpenAI API key from Streamlit secrets
openai_api_key = st.secrets["openai"]["api_key"]

# Set up config for SmartScraperGraph using GPT-4o-mini
graph_config = {
    "llm": {
        "api_key": openai_api_key,
        "model": "gpt-4o-mini",
    },
}

# Initialize app state
if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Institution Name
if st.session_state.step == 1:
    institution_name = st.text_input("Enter the Institution Name:")
    if institution_name:
        st.session_state.institution_name = institution_name
        st.session_state.step = 2
        safe_rerun()

# Step 2: Institution Homepage URL
elif st.session_state.step == 2:
    homepage_url = st.text_input("Enter the Institution's Homepage URL:")
    if homepage_url:
        st.session_state.homepage_url = homepage_url
        st.session_state.step = 3
        safe_rerun()

# Step 3: Desired Programs/Departments
elif st.session_state.step == 3:
    program_info = st.text_area(
        "Enter program names, desired levels (Undergrad, Master's, PhD), and departments (e.g., College of Education):"
    )
    if program_info:
        st.session_state.program_info = program_info
        st.session_state.step = 4
        safe_rerun()

# Step 4: Scrape & Show URLs for Manual Validation
elif st.session_state.step == 4:
    st.subheader("Step 4: Validate Discovered URLs")
    st.write(
        "Click 'List URLs' to scrape related program pages. Then test each link to make sure they don’t lead to 404 errors. "
        "Once you're done testing, click 'Create Tabular Output'."
    )

    if st.button("List URLs"):
        prompt = (
            f"Scrape the website for '{st.session_state.institution_name}' with homepage {st.session_state.homepage_url} "
            f"to find pages related to: {st.session_state.program_info}. "
            "Return a list of valid academic program URLs that do not lead to 404 errors."
        )

        smart_scraper_graph = SmartScraperGraph(
            prompt=prompt,
            source=st.session_state.homepage_url,
            config=graph_config
        )

        result = smart_scraper_graph.run()
        urls = []

        if isinstance(result, list):
            urls = result
        elif isinstance(result, str):
            urls = [line.strip() for line in result.splitlines() if line.strip()]

        if urls:
            st.session_state.urls = urls
            st.success("Click links below to test:")
            for url in urls:
                st.markdown(f"- [{url}]({url})")
            st.session_state.step = 5
            safe_rerun()
        else:
            st.error("No URLs found. Please check your inputs or try again.")

# Step 5: Create Tabular Output
elif st.session_state.step == 5:
    st.subheader("Step 5: Create Tabular Output")
    st.write(
        """
        Click the button below to generate a program table with:

        - Column A: Program name (from h1 or similar tag)
        - Column B: Full valid program URL
        - Column C: URL path after base (e.g., "majors/accounting-bs")
        - Columns D, E, F: Blank
        - Column G: Pattern from Column C (e.g., "/majors/.*bs")
        """
    )

    if st.button("Create Tabular Output"):
        prompt_table = (
            f"From the homepage {st.session_state.homepage_url} and the following program pages, "
            "generate a Markdown table:\n\n"
            "A: Program name from h1 or similar tag\n"
            "B: Full program URL\n"
            "C: URL path after homepage\n"
            "D, E, F: Leave blank\n"
            "G: Regex pattern based on Column C\n\n"
            "Only include valid (non-404) pages. Return Markdown table only."
        )

        smart_scraper_graph_table = SmartScraperGraph(
            prompt=prompt_table,
            source=st.session_state.homepage_url,
            config=graph_config
        )

        table_result = smart_scraper_graph_table.run()
        st.write("### Tabular Output")
        st.markdown(table_result)
        st.session_state.step = 6
        safe_rerun()

# Step 6: Completion
elif st.session_state.step == 6:
    st.success("🎉 Scraping and table creation complete.")
    st.balloons()
