import streamlit as st
from scrapegraphai.graphs import SmartScraperGraph

# Debug: Display Streamlit version
st.write("Streamlit version:", st.__version__)

# Modified safe_rerun using try/except
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception as e:
        st.warning("Please refresh the page manually to proceed. (Rerun failed with error: {})".format(e))

# Set up the app title and description.
st.title("Web Scraping AI Agent 🕵️‍♂️")
st.caption("Scrape institution websites using GPT-4o-mini on Streamlit Cloud.")

# Retrieve the OpenAI API key from Streamlit secrets.
# Ensure your .streamlit/secrets.toml file has:
# [openai]
# api_key = "your_openai_api_key_here"
openai_api_key = st.secrets["openai"]["api_key"]

# Define the configuration to use GPT-4o-mini.
graph_config = {
    "llm": {
        "api_key": openai_api_key,
        "model": "gpt-4o-mini",
    },
}

# Initialize session state to manage the multi-step process.
if "step" not in st.session_state:
    st.session_state.step = 1

# Step 1: Ask for the institution name.
if st.session_state.step == 1:
    institution_name = st.text_input("Enter the Institution Name:")
    if institution_name:
        st.session_state.institution_name = institution_name
        st.session_state.step = 2
        safe_rerun()

# Step 2: Ask for the institution's homepage URL.
elif st.session_state.step == 2:
    homepage_url = st.text_input("Enter the Institution's Homepage URL:")
    if homepage_url:
        st.session_state.homepage_url = homepage_url
        st.session_state.step = 3
        safe_rerun()

# Step 3: Ask for details about programs, program levels, and departments.
elif st.session_state.step == 3:
    program_info = st.text_area(
        "Enter details about the programs you want scraped. "
        "Include program names, desired levels (Undergraduate, Master's, PhD), "
        "and specific schools/colleges/departments (e.g., College of Education):"
    )
    if program_info:
        st.session_state.program_info = program_info
        st.session_state.step = 4
        safe_rerun()

# Step 4: List all discovered URLs for manual validation.
elif st.session_state.step == 4:
    st.subheader("Step 4: Validate Discovered URLs")
    st.write(
        "The app will now scrape the homepage for pages related to your input. "
        "Below is a list of URLs that the scraper found. Please click each link to test "
        "that they are valid and do not lead to 404 errors. When you are satisfied with "
        "the results, click the 'Create Tabular Output' button."
    )
    # Build a prompt for the scraper to list valid URLs.
    prompt = (
        f"Scrape the website for '{st.session_state.institution_name}' with homepage {st.session_state.homepage_url} "
        f"to find pages related to the following criteria: {st.session_state.program_info}. "
        "Return a list of valid URLs that do not lead to 404 errors."
    )
    smart_scraper_graph = SmartScraperGraph(
        prompt=prompt,
        source=st.session_state.homepage_url,
        config=graph_config
    )
    
    if st.button("List URLs"):
        result = smart_scraper_graph.run()
        # Assume result is a string containing URLs (one per line) or a list.
        urls = []
        if isinstance(result, list):
            urls = result
        elif isinstance(result, str):
            urls = [line.strip() for line in result.splitlines() if line.strip()]
        
        if urls:
            st.write("Discovered URLs:")
            for url in urls:
                st.markdown(f"[{url}]({url})")
            st.session_state.urls = urls
            st.session_state.step = 5
            safe_rerun()
        else:
            st.error("No URLs found. Please check your inputs or try again.")

# Step 5: Create the tabular output based on validated URLs.
elif st.session_state.step == 5:
    st.subheader("Step 5: Create Tabular Output")
    st.write(
        "Once you have validated the above links, click the button below to generate the table. "
        "The table will have the following columns:\n\n"
        "- **Column A:** Program name (extracted from an h1 tag or similar element on the page)\n"
        "- **Column B:** The corresponding valid URL of the academic program page\n"
        "- **Column C:** The part of the URL after the base URL (e.g., for 'https://www.example.edu/academics/majors/accounting', output 'academics/majors/accounting')\n"
        "- **Columns D, E, F:** (Leave these blank)\n"
        "- **Column G:** A regex pattern for Column C (for example, '/academics/majors/.*accounting')"
    )
    
    if st.button("Create Tabular Output"):
        prompt_table = (
            f"Using the institution homepage {st.session_state.homepage_url} and the validated program pages, "
            "create a table with the following columns:\n\n"
            "A: Program name (extracted from an h1 tag or similar element on the page).\n"
            "B: The corresponding program page URL (ensure the URL is valid and does not return a 404 error).\n"
            "C: The part of the URL after the base URL (for example, for 'https://www.example.edu/academics/majors/accounting', output 'academics/majors/accounting').\n"
            "D, E, F: Leave blank.\n"
            "G: A regex pattern representing the structure of Column C (for example, for 'academics/majors/accounting', output '/academics/majors/.*accounting').\n\n"
            "Return the table in Markdown format."
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

# Final Step: Completion message.
elif st.session_state.step == 6:
    st.success("Scraping and table creation complete.")
