from typing import Optional
import requests
import feedparser
from typing import Optional
from openai import OpenAI
import streamlit as st
import json
import pandas as pd
import http.client
from typing import List
from agents import function_tool
from bs4 import BeautifulSoup
import os
from agents import Agent, Runner, function_tool
from typing import Dict, Any, Union
import json
import pandas as pd
#from openai import function_tool




@function_tool
def get_links(
    rapidapi_key: str,
    keywords: str = "data scientist",
    location_id: str = "103644278",
    date_posted: str = "pastMonth",
    salary: str = "100k+",
    job_type: str = "fullTime",
    experience_level: str = "not senior",
    onsite_remote: str = "remote",
    sort: str = "mostRecent"
) -> List[str]:
    """
    Fetch recent LinkedIn job posting URLs using the RapidAPI LinkedIn Jobs API.

    Args:
        rapidapi_key (str): RapidAPI key.
        keywords (str): Job keywords.
        location_id (str): LinkedIn location ID.
        date_posted (str): Time window for job posting.
        salary (str): Salary filter.
        job_type (str): Job type filter.
        experience_level (str): Experience level filter.
        onsite_remote (str): Onsite/remote filter.
        sort (str): Sort order.

    Returns:
        List[str]: List of job posting URLs.
    """
    conn = http.client.HTTPSConnection("rapid-linkedin-jobs-api.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "83c395b880msh82bf5deb12cfa99p1a5ae6jsn24353af524b6",
        'x-rapidapi-host': "rapid-linkedin-jobs-api.p.rapidapi.com"
    }


    path = (
        f"/search-jobs-v2?"
        f"keywords={keywords.replace(' ', '%20')}"
        f"&locationId={location_id}" #102095887 greater LA
        f"&datePosted={date_posted}"
        f"&salary={salary.replace('+', '%2B')}"
        f"&jobType={job_type}"
        f"&experienceLevel={experience_level.replace(' ', '%20')}"
        f"&onsiteRemote={onsite_remote}"
        f"&sort={sort}"
    )

    try:
        #conn.request("GET", path, headers=headers)
        conn.request("GET",
                     "/search-jobs-v2?keywords=data%20scientist&locationId=102095887&datePosted=pastMonth&salary=100k%2B&jobType=fullTime&experienceLevel=not%20senior&onsiteRemote=remote&sort=mostRecent",
                     headers=headers)

        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        payload = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch job links: {e}") from e

    if "data" not in payload or not isinstance(payload["data"], list):
        return []

    return [
        item["url"]
        for item in payload["data"]
        if isinstance(item, dict) and "url" in item
    ]

'''
def get_links():
    conn = http.client.HTTPSConnection("rapid-linkedin-jobs-api.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': "rapid api key",
        'x-rapidapi-host': "rapid-linkedin-jobs-api.p.rapidapi.com"
    }
    conn.request("GET",
                 "/search-jobs-v2?keywords=data%20scientist&locationId=103644278&datePosted=pastMonth&salary=100k%2B&jobType=fullTime&experienceLevel=not%20senior&onsiteRemote=remote&sort=mostRecent",
                 headers=headers)
    res = conn.getresponse()
    # Reading the data from the API, decoding and parsing the response, getting the job URLs.
    data = res.read()
    data_decoded = data.decode("utf-8")
    data_dict = json.loads(data_decoded)
    # Finding the right tag to extract the job URLs:
    data_list = data_dict["data"]
    df = pd.DataFrame(data_list)
    links = df.url
    return links
'''

#def _client():
#    return OpenAI(api_key=st.session_state["openai_api_key"])

MAX_CHARS = 4000 #12000  # ~8–9k tokens, safe

@function_tool
def scrape_text(url: str) -> str:  #html_parser
    req = requests.get(url, timeout=18)
    req.raise_for_status()
    soup = BeautifulSoup(req.text, "html.parser")
    text = soup.get_text(separator=" ", strip=True) # or just soup.get_text()
    return text[:MAX_CHARS]




from pydantic import BaseModel
from typing import List


class TableInput(BaseModel):
    columns: List[str]
    rows: List[List[str]]


from typing import Dict


@function_tool
def concise_table(data: TableInput) -> Dict[str, object]:
    """
    Build a markdown table from structured columns and rows.
    The agent must pass:
        columns: List[str]
        rows: List[List[str]]
    """

    columns = data.columns
    rows = data.rows

    def md_row(cells):
        return "| " + " | ".join(str(c or "") for c in cells) + " |"

    md_lines = [
        md_row(columns),
        "| " + " | ".join("---" for _ in columns) + " |"
    ]

    for row in rows:
        md_lines.append(md_row(row))

    markdown_table = "\n".join(md_lines)

    return {
        #"markdown": markdown_table,
        "columns": columns,
        "rows": rows
    }




#extra:
'''
def ai(
    query: str,
    text: str,
    model: str = "gpt-4o",
    max_chars: int = 12000
) -> str:
    """
    Use an LLM to answer a query using only the provided text.

    Args:
        query (str): The question or instruction.
        text (str): Source document text to reason over.
        model (str): LLM model name.
        max_chars (int): Maximum number of characters from `text`
                         passed to the model to control context size.

    Returns:
        str: Model-generated response constrained to the provided text.
    """
    #client = OpenAI(api_key=st.session_state["openai_api_key"])
    global client
    if not query or not isinstance(query, str):
        raise ValueError("query must be a non-empty string")

    if not text or not isinstance(text, str):
        raise ValueError("text must be a non-empty string")

    # Guard against runaway context
    if len(text) > max_chars:
        text = text[:max_chars]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data analyst. "
                        "Answer the user's query using ONLY the information "
                        "contained in the provided document. "
                        "If the answer is not present, say so explicitly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"DOCUMENT:\n{text}",
                },
                {
                    "role": "user",
                    "content": f"QUERY:\n{query}",
                },
            ],
        )
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}") from e

    try:
        return completion.choices[0].message.content.strip()
    except (IndexError, AttributeError) as e:
        raise RuntimeError("Invalid LLM response format") from e

'''

#@function_tool #This should be a sub-agent, not a tool.
def first_query():
    # First query/prompt to send to Openai to get a dictionary of the contents of the job posting.
    query = ('Do the following step by step.'
             'Do not go to a new line. Put all code parts in one line.'
             'Make a table of the job posting. Include as much information as possible.'
             'Summarize using tags and similar to the format of a python dictionary.'
             'Display the python dictionary code.'
             'The code should be runnable in python.'
             'Do not explain anything. Only display a dictionary of the created dictionary in python formatting.'
             'This is not an external link. Use the information given in the prompt. This information is all you need.'
             'Check your written dictionary code and remove all the backslash-n in the dictionary code.'
             )

    # A second query became necessary since Chatgpt does not return a clean dictionary output
    # so have to instruct it to clean the outputted dictionary string.

    # Saving the contents in a list of dictionaries:
    data = []
    for url in links:
        req = requests.get(url)
        soup = BeautifulSoup(req.text, 'html.parser')
        # First and second prompt
        result_ai = ai(query, soup.get_text())
        query2 = (
            "Extract a single JSON object for the job posting from the text below.\n"
            "RULES:\n"
            "• Return ONLY a single-line JSON object. No backticks, no code fences, no language tags, no explanations.\n"
            "• Keys to include if present: Job Title, Company, Location, Posted, URL or links, Applicants, Responsibilities,\n"
            "• Keep lists as JSON arrays. Omit keys that aren’t present.\n"
            "TEXT:\n"
            f"{result_ai}"
        )
        result_ai2 = ai(query2, result_ai)
        # eval creates a dictionary out of the outputted string
        my_dict = eval(result_ai2)
        if isinstance(my_dict, dict):
            data.append(my_dict)


'''
@function_tool
def concise_table (resp):
    payload = json.loads(resp.choices[0].message.content)
    columns = payload["columns"]
    rows = payload["rows"]

    # Markdown table
    def md_row(cells): return "| " + " | ".join(str(c or "") for c in cells) + " |"
    md = [md_row(columns), "| " + " | ".join("---" for _ in columns) + " |"] + [md_row(r) for r in rows]
    print("\n".join(md))

    df = pd.DataFrame(rows, columns=columns)
    return {"columns": columns, "rows": rows, "df": df}
'''



#@function_tool #This should be a sub-agent, not a tool.
def list_to_table_with_openai(records, model="gpt-4o-mini", max_items=25):
    # Keep prompt short to avoid truncation; sample first N items if huge

    SYSTEM_INSTRUCTIONS = (
        "You are a data wrangler. Given a JSON array of heterogeneous records, "
        "infer a normalized set of column names. Merge clear synonyms (e.g., "
        "'Title' ~ 'Job Title'; 'Reports To' ~ 'Reports to'; 'Seniority level' ~ 'Seniority Level'). "
        "Pick up to 15 columns that best cover the data; if needed, put overflow into an 'Other' column. "
        "Flatten nested lists as '; ' joined and dicts as 'key: value' pairs joined by '; '. "
        "Return ONLY valid JSON with this shape: "
        "{columns:[...], rows:[[...],[...],...]} where rows align exactly to the columns and preserve input order."
    )
    sample = records[:max_items]

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": json.dumps(sample, ensure_ascii=False)}
        ],
    )

    payload = json.loads(resp.choices[0].message.content)
    columns = payload["columns"]
    rows = payload["rows"]

    # Markdown table
    def md_row(cells): return "| " + " | ".join(str(c or "") for c in cells) + " |"
    md = [md_row(columns), "| " + " | ".join("---" for _ in columns) + " |"] + [md_row(r) for r in rows]
    print("\n".join(md))

    df = pd.DataFrame(rows, columns=columns)
    return {"columns": columns, "rows": rows, "df": df}


# extra
'''
@function_tool
def scrape_feed(
    url: str,
    max_items: Optional[int] = None,
    timeout: int = 10
) -> str:
    """
    Fetch and parse an RSS/Atom feed and return concatenated titles
    and descriptions as plain text.

    Args:
        url (str): URL of the RSS or Atom feed.
        max_items (Optional[int]): Maximum number of feed entries to process.
                                  If None, processes all entries.
        timeout (int): HTTP request timeout in seconds.

    Returns:
        str: Concatenated text of feed entries in the format:
             "Title - Description"
    """
    if not url or not isinstance(url, str):
        raise ValueError("url must be a non-empty string")

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch feed: {e}") from e

    feed = feedparser.parse(response.text)

    if not feed.entries:
        return ""

    entries = feed.entries[:max_items] if max_items else feed.entries

    parts = []
    for post in entries:
        title = post.get("title", "").strip()
        description = post.get("description", "").strip()

        if title or description:
            parts.append(f"{title} - {description}".strip(" -"))

    return " ".join(parts)
'''