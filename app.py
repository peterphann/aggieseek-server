from flask import Flask, Response
from flask_cors import CORS
from cache import cache
from section import *
import time

app = Flask(__name__, static_folder='')
app.config.from_mapping({
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
})
CORS(app, origins=["http://localhost:5173", "https://aggieseek.net/"])
cache.init_app(app)

@app.route('/')
def index():
    return "<h1>AggieSeek</h1>"

@app.route('/classes/<term>/<crn>/seats/', methods=['GET'])
def seats(term, crn):
    start_time = time.time()  

    section = get_section_seats(term, crn)
    section['CRN'] = crn
    section['QUERY_TIME'] = time.time() - start_time
    return section

@app.route('/classes/<term>/<crn>/', methods=['GET'])
def sections(term, crn):
    start_time = time.time()  

    section = get_section(term, crn)
    section['QUERY_TIME'] = time.time() - start_time
    status = int(section['STATUS'])
    return section, status

@app.route('/terms/', methods=['GET'])
def terms():
    start = time.time()
    terms = get_all_terms()
    response = {
            'QUERY_TIME': time.time() - start,
            'TERMS': terms
    }
    if not terms:
        response.update({'ERROR': 'Failed to fetch term data from Howdy'})
    
    return response

@app.route('/terms/<term>', methods=['GET'])
def term(term):
    start = time.time()
    term_info = get_term(term)

    response = {
        'QUERY_TIME': time.time() - start,
        'TERMS': term_info
    }
    if not term_info:
        response.update({'ERROR': 'Failed to fetch term data from Howdy'})

    return response

@app.route('/classes/<term>/', methods=['GET'])
def classes(term):
    print('memoizing')
    response = {}
    start = time.time()
    response['CLASSES'] = get_all_classes(term)
    response['QUERY_TIME'] = time.time() - start
    print(f'classes took {time.time() - start}')
    return response

@app.route('/subjects/<term>/', methods=['GET'])
def subjects(term):
    response = {}
    start = time.time()
    response['DEPARTMENTS'] = get_subjects(term)
    response['QUERY_TIME'] = time.time() - start
    
    return response

@app.route('/subjects/<term>/<subject>', methods=['GET'])
def subject(term, subject):
    response = {}
    start = time.time()
    response['COURSES'] = get_subject(term, subject)
    response['QUERY_TIME'] = time.time() - start
    
    return response

@app.route('/subjects/<term>/<subject>/<course>', methods=['GET'])
def course(term, subject, course):
    response = {}
    start = time.time()
    response['SECTIONS'] = get_course_sections(term, subject, course)
    response['QUERY_TIME'] = time.time() - start
    
    return response


if __name__ == "__main__":
    app.run(debug=True, port=8000)
