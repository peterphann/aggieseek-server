from bs4 import BeautifulSoup
from typing import Literal
import requests
import pickle
import json


def parse_soup(soup: BeautifulSoup, term, crn) -> dict:
    all_fields = soup.find_all("td", class_="dddefault")

    if len(all_fields) == 0:
        return {"crn": int(crn), "status": 400}

    static_headers = soup.find("div", class_="staticheaders").text
    term_and_campus = static_headers.split("\n")[1]
    full_term = " ".join(term_and_campus.split()[:2])
    full_course_name = soup.find("th", class_="ddlabel").text
    split_name = full_course_name.split(" - ")

    course = split_name[2]

    professor = scrape_instructor(split_name[2], term, crn)
    return {
        "seats": {
            "actual": int(all_fields[2].text),
            "capacity": int(all_fields[1].text),
            "remaining": int(all_fields[3].text),
        },
        "crn": int(split_name[1]),
        "title": split_name[0],
        "course": course,
        "section": int(split_name[3]),
        "term": full_term,
        "professor": professor,
        "status": 200,
    }


def scrape_instructor(course, term, crn) -> str:
    subject = course.split()[0]
    number = course.split()[1]
    instructor_url = f"https://compass-ssb.tamu.edu/pls/PROD/bwykschd.p_disp_listcrse?term_in={
        term}&subj_in={subject}&crse_in={number}&crn_in={crn}"

    request = requests.get(instructor_url)
    if request.status_code != 200:
        return ""
    instructor_soup = BeautifulSoup(request.text, "html.parser")

    instructor_name = instructor_soup.find_all("td", class_="dddefault")[7].text
    instructor_name = instructor_name.removesuffix(" (P)")
    return instructor_name


def scrape_section(term, crn) -> dict:
    url = f"https://compass-ssb.tamu.edu/pls/PROD/bwykschd.p_disp_detail_sched?term_in={
        term}&crn_in={crn}"

    try:
        print(url)
        page = requests.get(url)
        page.raise_for_status()

    except requests.HTTPError as e:
        return {"crn": crn}

    if page.status_code != 200:
        return {"crn": crn}

    soup = BeautifulSoup(page.text, "html.parser")
    course_info = parse_soup(soup, term, crn)

    return course_info


def log_response_and_raise(response, error_message):
    with open("fail_response.pkl", "w") as f:
        pickle.dump(response, f)

    raise Exception(f"{error_message} - Response saved to fail_response.log")


def save(json_content, filename):
    with open(f"{filename}.json", "w") as f:
        f.write(json.dumps(json_content, indent=4))


def load(filename):
    with open(f"{filename}.json", "r") as f:
        return json.loads(f.read())


def parse_response(response_json):
    # parse response is meant to convert the nasty keys from
    # the response into something palatable to our requirements

    # create a lookup table to convert the original response keys to
    # something more palatable for our use

    key_convert = {
        "SWV_CLASS_SEARCH_TERM": "",
        "SWV_CLASS_SEARCH_CRN": "crn",
        "SWV_CLASS_SEARCH_TITLE": "title",
        "SWV_CLASS_SEARCH_SUBJECT": "subject",
        "SWV_CLASS_SEARCH_SUBJECT_DESC": "",
        "SWV_CLASS_SEARCH_COURSE": "course",
        "SWV_CLASS_SEARCH_SECTION": "section",
        "SWV_CLASS_SEARCH_SSBSECT_HOURS": "",
        "SWV_CLASS_SEARCH_HOURS_LOW": "",
        "SWV_CLASS_SEARCH_HOURS_IND": "",
        "SWV_CLASS_SEARCH_HOURS_HIGH": "",
        "SWV_CLASS_SEARCH_SITE": "site",
        "SWV_CLASS_SEARCH_PTRM": "partOfTerm",
        "SWV_CLASS_SEARCH_HAS_SYL_IND": "",
        "STUSEAT_OPEN": "",
        "SWV_CLASS_SEARCH_MAX_ENRL": "",
        "SWV_CLASS_SEARCH_ENRL": "",
        "SWV_CLASS_SEARCH_SEATS_AVAIL": "",
        "SWV_WAIT_CAPACITY": "",
        "SWV_WAIT_COUNT": "",
        "SWV_WAIT_AVAIL": "",
        "SWV_CLASS_SEARCH_SCHD": "type",
        "SWV_CLASS_SEARCH_INST_TYPE": "instructorType",
        "SWV_CLASS_SEARCH_INSTRCTR_JSON": "instructors",
        "SWV_CLASS_SEARCH_JSON_CLOB": "datetime",
        "SWV_CLASS_SEARCH_ATTRIBUTES": "attributes",
        "SWV_CLASS_SEARCH_SESSION": "duration",
        "HRS_COLUMN_FIELD": "hours",
    }

    # NOTE: if the value of a given key is "", then key_convert
    # acts like a filter and supresses this key in the output
    # NOTE: Notable Response Information/format
    #   - SWV_CLASS_SEARCH_HAS_SYL_IND key holds a "Y"/"N"
    #       boolean value, but I don't know what SYL_IND mean, so
    #       I'm not saving the value
    #   - SWV_CLASS_SEARCH_PTRM/partOfTerm indicates that the
    #       course doesn't last for the entirety of the standard
    #       term, like FYEX 101 courses
    #   - SWV_CLASS_SEARCH_HOURS_LOW/IND/HIGH probably represents
    #       the minimum/maximum # of hours you can get from a
    #       given class (although I assumed all classes have a
    #       set hour amount) but since there's also a HRS_COLUMN_FIELD
    #       key, I'm going to use that as the hour amount
    #   - SWV_CLASS_SEARCH_INSTRCTR_JSON/instructors gives a json
    #       about all of the professors in a course. the information is
    #       used by the website to generate a auto-generated CV with
    #       their achievements with a post request.

    parsed = [
        {key_convert[k]: v for k, v in course_info.items() if key_convert[k] != ""}
        for course_info in response_json
    ]

    # key specific conversion
    for i in parsed:
        # datetime
        if "datetime" in i and i["datetime"] != None:
            i["datetime"] = json.loads(i["datetime"])

        # instructors
        if "instructors" in i and i["instructors"] != None:
            i["instructors"] = json.loads(i["instructors"])

        # attributes
        if "attributes" in i and i["attributes"] != None:
            i["attributes"] = list(map(str.strip, i["attributes"].split("|")))

    return parsed


def scrape_all_courses(
    year,
    semester: Literal["spring", "summer", "fall"],
    location: Literal["cs", "gv", "un"] = "cs",
    save_raw=False,
):
    # NOTE: location codes: College Station, Galveston, Unknown
    # the order of the location codes determines the number given to
    # the post request so don't change them

    # first we need to get cookies required for post request by sending dummy request

    dummy_url = "https://howdy.tamu.edu/uPortal/favicon.ico"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    }

    session = requests.Session()
    dummy_response = session.get(dummy_url, headers=headers)
    cookies = "".join([f"{c.name}={c.value};" for c in session.cookies])

    # now we make the post request
    url = "https://howdy.tamu.edu/api/course-sections"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json; charset=utf-8",
        "Origin": "https://howdy.tamu.edu",
        "Referer": "https://howdy.tamu.edu/uPortal/p/public-class-search-ui.ctf1/max/render.uP",
        "Connection": "keep-alive",
        "Cookie": cookies,
    }

    # create termCode value
    semesterIndex = ("spring", "summer", "fall").index(semester) + 1
    locationIndex = ("cs", "gv", "un").index(location) + 1
    termCode = f"{year}{semesterIndex}{locationIndex}"

    # NOTE: termCode breakdown:
    # '202411' = [year][semester][location?]
    # semester :
    #   - 1: spring semester
    #   - 2: summer 10 week semester
    #   - 3: fall semester
    # location:
    #   - 1: college station (all courses have "College Station" attribute)
    #   - 2: galveston (all courses in response has "Galveston" attribute)
    #   - 3: mislabelled? not completely sure, seems like only returns courses
    #       without any location attribute

    # define json payload for post request
    # TODO: find out what startRow, endRow, publicSearch do to response
    data = {
        # "startRow": 1,
        # "endRow": 2,
        "termCode": termCode,
        # "publicSearch": "Y",
    }

    # send the post request
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # validate response and throw relevant errors
    if response.status_code != 200:
        log_response_and_raise(f"Invalid response status: {
                               response.status_code}")

    if len(response.json()) == 0:
        log_response_and_raise("Response was empty.")

    # if save_raw, then save the original json response with original
    # formatting
    if save_raw:
        save(response.json(), "output")
        return

    # otherwise, save json response with palatable keys relevant to our
    # goal
    parsed = parse_response(response.json())

    # TODO: DO NOT USE THE COMMENTED CODE BELOW. IT TECHNICALLY WORKS BUT IS OBVIOUSLY SLOW.
    # your todo, if you choose to accept it, is to find another endpoint to
    # pull seat availability at once, preferrably with all of the information from
    # this one as well, so that we don't have to run two calls.

    # for i in range(len(parsed)):
    #     parsed[i]["seats"] = scrape_section(termCode, parsed[i]["crn"])["seats"]

    save(parsed, "output")


def filter_courses(subject=None, course=None):  # developement code to filter courses
    with open("output.json", "r") as f:
        c = json.loads(f.read())

    results = [i for i in c if i["subject"] == subject and i["course"] == course]
    return results


def display_course(course):  # development code to see what the response got
    print(f"{course['subject']}{course['course']} : crn = {course['crn']}, {
          len(course['instructors'])} professors (Ex: {course['instructors'][0]['NAME']})")


if __name__ == "__main__":
    pass

    # scrape_all_courses(2024, "fall", "cs", save_raw=False)
    # save(filter_courses("ENGR", "102"), "filtered")
