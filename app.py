from flask import Flask, request, render_template, redirect, url_for, send_file
import os
from services.spec_compare import compare_project_spec_with_standard
from services.pos_pdf_writer import apply_differences_to_pos_pdf
from database import get_pos_items, get_pos_filenames_by_shiptype
from database import POS_FOLDER  # ✅ POS_FOLDER는 사용되므로 유지

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ✅ 선종 코드와 이름 매핑
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

    proj_filename = proj_spec_file.filename
    proj_path = os.path.join(UPLOAD_FOLDER, proj_filename)
    proj_spec_file.save(proj_path)

    differences = compare_project_spec_with_standard(ship_type, proj_path)
    pos_items = get_pos_items(ship_type)
    pos_filenames = get_pos_filenames_by_shiptype(ship_type)

    return render_template(
        "compare_result.html",
        ship_type=ship_type,
        differences=differences,
        pos_items=pos_items,
        pos_filenames=pos_filenames,
        project_number=project_number
    )

@app.route("/reflect", methods=["POST"])
def reflect():
    ship_type = request.form.get("ship_type")
    project_number = request.form.get("project_number") or "1234"

    differences = []
    pos_filename = None
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
            pos_filename = selected_pos_text

    if not differences or not pos_filename:
        return "POS에 반영할 항목이 선택되지 않았습니다.", 400

    pdf_path = get_pos_pdf_path_by_filename(pos_filename)  # ✅ 이 함수는 아래에 정의됨
    if not pdf_path or not os.path.exists(pdf_path):
        return f"POS PDF 경로가 유효하지 않음: {pdf_path}", 500

    result_path = apply_differences_to_pos_pdf(ship_type, differences, project_number, pos_filename)
    if not result_path or not os.path.exists(result_path):
        return "POS PDF 반영 실패 또는 생성되지 않았습니다.", 500

    return render_template("reflect_result.html", pdf_path=result_path)

@app.route("/download")
def download():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "파일이 존재하지 않습니다.", 404
    return send_file(path, as_attachment=True)

# ✅ POS 파일명을 기반으로 전체 경로 반환
def get_pos_pdf_path_by_filename(filename):
    return os.path.join(POS_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5004)