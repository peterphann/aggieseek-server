from flask import Flask, Response
from flask_cors import CORS, cross_origin
from section import scrape_section, get_all_terms, get_all_classes
import time


app = Flask(__name__, static_folder='')


@app.route('/')
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def index():
    return 'Hello World!'


@app.route('/classes/<term>/<crn>/', methods=['GET'])
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def sections(term, crn):
    start_time = time.time()  

    section = scrape_section(term, crn)
    section['QUERY_TIME'] = time.time() - start_time
    return section

@app.route('/terms/', methods=['GET'])
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def terms():
    start = time.time()
    response = {
        'query_time': time.time() - start,
        'terms': get_all_terms()
    }
    return response

@app.route('/classes/<term>/', methods=['GET'])
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def classes(term):
    start = time.time()
    classes = [{'Query Time': time.time() - start}]
    classes += get_all_classes(term)
    return classes


if __name__ == "__main__":
    app.run(debug=True, port=8080)
