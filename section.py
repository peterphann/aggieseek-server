from bs4 import BeautifulSoup
import requests
import json
from typing import List
import aiohttp
import asyncio

# GPT written helper
def recursive_parse_json(json_str):
    try:
        # Try parsing the string as JSON
        parsed = json.loads(json_str)
        
        # If it's a dictionary, recursively parse its values
        if isinstance(parsed, dict):
            return {k: recursive_parse_json(v) for k, v in parsed.items()}
        # If it's a list, recursively parse each element
        elif isinstance(parsed, list):
            return [recursive_parse_json(element) for element in parsed]
        else:
            return parsed
    except (json.JSONDecodeError, TypeError):
        # If parsing fails, return the original string
        return json_str
    


def parse_soup(soup: BeautifulSoup, term, crn) -> dict:
    all_fields = soup.find_all('td', class_='dddefault')

    if len(all_fields) == 0:
        return {'CRN': crn, 'STATUS': 400}
    
    out = {
        'SEATS': {
        'ACTUAL': int(all_fields[2].text),
        'CAPACITY': int(all_fields[1].text),
        'REMAINING': int(all_fields[3].text)
        },
        'STATUS': 200,
    }
    out.update(get_section_detail(term, crn))

    return out


def scrape_instructor(course, term, crn) -> str:
    subject = course.split()[0]
    number = course.split()[1]
    instructor_url = f'https://compass-ssb.tamu.edu/pls/PROD/bwykschd.p_disp_listcrse?term_in={term}&subj_in={subject}&crse_in={number}&crn_in={crn}'

    request = requests.get(instructor_url)
    if request.status_code != 200: return ""
    instructor_soup = BeautifulSoup(request.text, 'html.parser')

    instructor_name = instructor_soup.find_all('td', class_='dddefault')[7].text
    instructor_name = instructor_name.removesuffix(' (P)')
    return instructor_name


def scrape_section(term, crn) -> dict:
    url = f'https://compass-ssb.tamu.edu/pls/PROD/bwykschd.p_disp_detail_sched?term_in={term}&crn_in={crn}'

    try:
        print(url)
        page = requests.get(url)
        page.raise_for_status()
    except requests.HTTPError as e:
        return {'CRN': crn}

    if page.status_code != 200:
        return {'CRN': crn}

    soup = BeautifulSoup(page.text, 'html.parser')
    seat_info = parse_soup(soup, term, crn)
    section_info = get_section_detail(term, crn)

    section_info.update(seat_info)

    return section_info

def get_all_terms() -> List[dict]:
    link = 'https://howdy.tamu.edu/api/all-terms'
    res = requests.get(link)
    if res.status_code != 200:
        return [{'error': 'Failed to fetch term data from Howdy'}]
    try:
        return res.json()
    except:
        return [{'error': 'Failed to parse term data from Howdy'}]
    

def get_all_classes(term_code: str) -> List[dict]:
    """
    Fetches all classes information for a given term code

    Args:
        term_code (str): The term code to fetch classes for
    Returns:
        dict: The class data in JSON format
    """

    link = f"https://howdy.tamu.edu/api/course-sections"
    res = requests.post(link, json={"startRow":0,"endRow":0,"termCode":term_code,"publicSearch":"Y"})
    if res.status_code != 200:
        return [{'ERROR': 'Failed to fetch class data from Howdy'}]
    
    res = res.json()

    if res == []:
        return [{'ERROR': 'No classes found for the given term'}]
    try:
        return res
    except:
        return [{'ERROR': 'Failed to parse class data from Howdy'}]

def get_section_detail(term_code: str, crn: str) -> dict:
    error = []

    links = {
        "Section attributes": 'https://howdy.tamu.edu/api/section-attributes',
        "Section prereqs": 'https://howdy.tamu.edu/api/section-prereqs',
        "Bookstore links": 'https://howdy.tamu.edu/api/section-bookstore-links',
        "Meeting times with profs": 'https://howdy.tamu.edu/api/section-meeting-times-with-profs',
        "Section program restrictions": 'https://howdy.tamu.edu/api/section-program-restrictions',
        "Section college restrictions": 'https://howdy.tamu.edu/api/section-college-restrictions',
        "Level restrictions": 'https://howdy.tamu.edu/api/section-level-restrictions',
        "Degree restrictions": 'https://howdy.tamu.edu/api/section-degree-restrictions',
        "Major restrictions": 'https://howdy.tamu.edu/api/section-major-restrictions',
        "Minor restrictions": 'https://howdy.tamu.edu/api/section-minor-restrictions',
        "Concentrations restrictions": 'https://howdy.tamu.edu/api/section-concentrations-restrictions',
        "Field of study restrictions": 'https://howdy.tamu.edu/api/section-field-of-study-restrictions',
        "Department restrictions": 'https://howdy.tamu.edu/api/section-department-restrictions',
        "Cohort restrictions": 'https://howdy.tamu.edu/api/section-cohort-restrictions',
        "Student attribute restrictions": 'https://howdy.tamu.edu/api/section-student-attribute-restrictions',
        "Classification restrictions": 'https://howdy.tamu.edu/api/section-classifications-restrictions',
        "Campus restrictions": 'https://howdy.tamu.edu/api/section-campus-restrictions',
    }

    general_info_link = f"https://howdy.tamu.edu/api/course-section-details?term={term_code}&subject=&course=&crn={crn}"

    async def fetch_all():
        out = {}
        async with aiohttp.ClientSession() as session:
            # Fetch general info
            try:
                async with session.get(general_info_link) as response:
                    # Howdy still returns 200 for some reason if the response is invalid kms
                    general_info = await response.json()
                    if not general_info:
                        error.append(f"Failed to fetch general info from {general_info_link}")
                        general_info = {}
                    out.update(general_info)
            except Exception as e:
                error.append(f"Exception when fetching general info: {e}")
                out = {}

            # Define async tasks for each link
            async def fetch_data(key, link):
                try:
                    async with session.post(
                        link,
                        json={
                            "term": term_code,
                            "subject": None,
                            "course": None,
                            "crn": crn,
                        },
                    ) as res:
                        if res.status != 200:
                            error.append(f"Failed to fetch {key} data from {link}")
                            data = {}
                        else:
                            text = await res.text()
                            data = recursive_parse_json(text)
                        out["OTHER_ATTRIBUTES"][key] = data
                except Exception as exc:
                    error.append(f"{key} generated an exception: {exc}")
                    out["OTHER_ATTRIBUTES"][key] = {}

            is_valid_section = len(out) > 0

            if is_valid_section:
                out['OTHER_ATTRIBUTES'] = {}
                tasks = [fetch_data(key, link) for key, link in links.items()]
                await asyncio.gather(*tasks)
                out['SYLLABUS'] = f"https://compass-ssb.tamu.edu/pls/PROD/bwykfupd.p_showdoc?doctype_in=SY&crn_in={crn}&termcode_in={term_code}"
                cv_information = out["OTHER_ATTRIBUTES"]['Meeting times with profs']['SWV_CLASS_SEARCH_INSTRCTR_JSON'][0]
                cv_information['CV'] = f'https://compass-ssb.tamu.edu/pls/PROD/bwykfupd.p_showdoc?doctype_in=CV&pidm_in={cv_information['MORE']}'
                
                
        return out

    # Run the async fetch_all function in the event loop
    out = asyncio.run(fetch_all())
    out['ERRORS'] = error
        
    return out