from flask import Flask, Response
from flask_cors import CORS, cross_origin
from section import scrape_section
import concurrent.futures
app = Flask(__name__, static_folder='')


@app.route('/')
@cross_origin(origin='*')
def index():
    return 'Hello World!'


@app.route('/sections/<term>/<crns>/', methods=['GET'])
@cross_origin(origin='*')
def sections(term, crns):
    crn_list = crns.split(',')

    course_info = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for crn in crn_list:
            future = executor.submit(scrape_section, term, crn)
            course_info.append(future.result())

    if course_info:
        return course_info
    else:
        return Response(f'{{"error": "Course not found", "crn": "2", "status": 400}}', status=400,
                        mimetype='application/json')


if __name__ == "__main__":
    app.run(debug=True, port=8080)
