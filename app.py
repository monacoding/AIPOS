from flask import Flask, request, render_template
import os
from services.word_pos_writer import update_pos_word_with_differences
from services.spec_compare import compare_project_spec_with_standard
from database import get_pos_items, POS_FOLDER

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

ship_types = {
    "1": "174K LNGC",
    "2": "180K LNGC",
    "3": "200K LNGC",
    "4": "88K LPGC",
    "5": "91K LPGC"
}

@app.route("/")
def index():
    return render_template("index.html", ship_types=ship_types)

@app.route("/compare", methods=["POST"])
def compare():
    ship_type_code = request.form.get("ship_type")
    ship_type = ship_types.get(ship_type_code)
    project_number = request.form.get("project_number") or "1234"
    proj_spec_file = request.files.get("proj_spec")

    if not ship_type or not proj_spec_file:
        return "선종과 프로젝트 사양서를 모두 업로드해주세요.", 400

    proj_path = os.path.join(UPLOAD_FOLDER, proj_spec_file.filename)
    proj_spec_file.save(proj_path)

    differences = compare_project_spec_with_standard(ship_type, proj_path)
    pos_filenames = get_pos_docx_filenames_by_shiptype(ship_type)
    pos_items = get_pos_items(ship_type)

    return render_template(
        "compare_result.html",
        ship_type=ship_type,
        differences=differences,
        pos_filenames=pos_filenames,
        pos_items=pos_items,
        project_number=project_number
    )

@app.route("/reflect", methods=["POST"])
def reflect():
    ship_type = request.form.get("ship_type")
    project_number = request.form.get("project_number") or "1234"
    differences = []

    total = int(request.form.get("diff_total"))
    for i in range(total):
        selected_pos_text = request.form.get(f"pos_target_{i}")
        if selected_pos_text:
            std_text = request.form.get(f"std_{i}")
            proj_text = request.form.get(f"proj_{i}")
            differences.append({
                "표준 사양서": std_text,
                "프로젝트 사양서": proj_text,
                "POS 대상": selected_pos_text
            })

    if not differences:
        return "POS에 반영할 항목이 선택되지 않았습니다.", 400

    # 모든 POS 파일에 대해 반복 작업을 수행하도록 수정
    all_change_logs = []
    result_path = None  # 초기화
    for diff in differences:
        pos_filename = diff["POS 대상"]
        result_path, change_log = update_pos_word_with_differences(
            ship_type,
            [diff],  # 현재 diff만 전달
            project_number,
            pos_filename
        )
        if change_log:
            all_change_logs.extend(change_log)  # 결과를 누적
        
    # 결과를 템플릿에 전달
    return render_template("reflect_result.html", change_log=all_change_logs, file_path=result_path)

def get_pos_docx_filenames_by_shiptype(ship_type):
    folder_path = os.path.join(POS_FOLDER, ship_type)
    if not os.path.exists(folder_path):
        return []

    filenames = [
        f for f in os.listdir(folder_path)
        if f.endswith(".docx")
    ]
    return filenames

if __name__ == "__main__":
    app.run(debug=True, port=5005)