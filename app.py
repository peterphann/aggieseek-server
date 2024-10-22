from flask import Flask, Response
from flask_cors import CORS
from section import get_section, get_all_terms, get_all_classes, get_term, get_section_seats, get_departments, get_department
import time


app = Flask(__name__, static_folder='')
CORS(app, origins=["http://localhost:5173", "https://aggieseek.net/"])

@app.route('/')
def index():
    return ""

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
    response = {}
    start = time.time()
    response['CLASSES'] = get_all_classes(term)
    response['QUERY_TIME'] = time.time() - start
    return response

@app.route('/departments/<term>/', methods=['GET'])
def departments(term):
    response = {}
    start = time.time()
    response['DEPARTMENTS'] = get_departments(term)
    response['QUERY_TIME'] = time.time() - start
    
    return response

@app.route('/departments/<term>/<department>', methods=['GET'])
def department(term, department):
    response = {}
    start = time.time()
    response['COURSES'] = get_department(term, department)
    response['QUERY_TIME'] = time.time() - start
    
    return response


if __name__ == "__main__":
    app.run(debug=True, port=8080)
