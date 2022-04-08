#-*-coding:utf-8-*- 
# author lyl
from flask import Flask, render_template, request, jsonify, send_file, make_response
from mongo_util import MongoDB, MongoPipline
from search_util import SearchEngine
import json
from data_util import DataProcess, Page
from analysis.analysis_util import Analysis

app = Flask(__name__)

mongo = MongoDB(database="RUNewsData", host="localhost", port=27019, user="admin", password="Liyulin6749901!")
mongo_pipline = MongoPipline(mongo)
search_engine = SearchEngine(mongo_pipline)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/api", methods=["GET", "POST"])
def get_data():
    params = request.args.to_dict()
    conditions = {'time': {"from_time": params.get("from_time",""), "to_time": params.get("to_time","")}, "search_keyword": params.get("search_keyword", ""), "search_content": params.get("search_content", "")}
    res = search_engine.find(collection_key=params.get("collection_key"), conditions=conditions, sort={"time":-1}, do_filter=True)
    page_number = int(params.get("offset", 0)) + 1
    page_size = int(params.get("page_size", 20))
    page = Page(res, page_number, page_size)
    post_res = page.get_data()
    return jsonify({
        'data': post_res,
        'success': 1,
        'params': {
            "page_size": page_size,
            "page_number": page_number,
            "total_page": page.getTotalPage(),
            "data_size": len(res[params.get("collection_key")])
        }
    })

@app.route("/download", methods=["GET", "POST"])
def download_data():
    params = json.loads(request.get_data(as_text=True))
    db_data = params.get("data")
    file_type = params.get("file_type")
    conditions = {'time': {"from_time": db_data.get("from_time",""), "to_time": db_data.get("to_time","")}, "search_keyword": db_data.get("search_keyword", ""), "search_content": db_data.get("search_content", "")}
    res = search_engine.find(collection_key=db_data.get("collection_key"), conditions=conditions, sort={"time":-1}, do_filter=True)
    if file_type == "json":
        path = DataProcess(res).to_json()
    elif file_type == "xlsx":
        path = DataProcess(res).to_xlsx()
    else:
        raise ValueError("")
    response = make_response(send_file(path))
    response.headers["code"] = 0
    response.headers["content-disposition"] = "attachment; filename={}.json".format(
        db_data.get("collection_key").encode().decode('latin-1')
    )
    return response

@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    params = json.loads(request.get_data(as_text=True))
    ana = Analysis(params)
    ner_collection = ana.ner()
    print(ner_collection)
    return render_template('analysis.html', data=ner_collection)



if __name__ == '__main__':
    app.run(host="0.0.0.0")