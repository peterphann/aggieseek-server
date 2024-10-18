from flask import Flask, Response
from flask_cors import CORS, cross_origin
from section import scrape_section, get_all_terms, get_all_classes
import time


app = Flask(__name__, static_folder='')


@app.route('/')
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def index():
    return 'Hello World!'


@app.route('/sections/<term>/<crn>/', methods=['GET'])
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def sections(term, crn):
    start_time = time.time()  

    section = scrape_section(term, crn)

    if section['status'] == 200:
        section['time'] = time.time() - start_time
        return section
    else:
        return Response(f'{{"error": "Course not found", "crn": {crn}, "status": 400}}', status=400,
                        mimetype='application/json')

@app.route('/terms/', methods=['GET'])
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def terms():
    start = time.time()
    terms = [{'Query Time': time.time() - start}]
    terms += get_all_terms()
    return terms

@app.route('/classes/<term>/', methods=['GET'])
@cross_origin(origin=['http://aggieseek.net, http://localhost:8080'])
def classes(term):
    start = time.time()
    classes = [{'Query Time': time.time() - start}]
    classes += get_all_classes(term)
    return classes


if __name__ == "__main__":
    app.run(debug=True, port=8080)
