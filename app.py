from flask import Flask, request, render_template, redirect, url_for, send_file, send_from_directory
import os
import unicodedata
import glob
from PyPDF2 import PdfReader

from services.spec_compare import compare_project_spec_with_standard
from services.pos_pdf_writer import apply_differences_to_pos_pdf
from database import get_pos_items, get_pos_filenames_by_shiptype, POS_FOLDER

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download")

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

    pos_pdf_path = get_pos_pdf_path_by_filename(ship_type, pos_filename)
    print("📦 디버그 - POS PDF 경로:", pos_pdf_path)

    if not os.path.exists(pos_pdf_path):
        print("❌ os.path.exists() = False")
        print("🔍 glob으로 POS 폴더 내용 스캔:")
        for f in glob.glob(f"{POS_FOLDER}/**/*.pdf", recursive=True):
            print("📄 ", f)
        return f"❌ POS PDF 경로가 유효하지 않음: {pos_pdf_path}", 500

    result_path, change_log = apply_differences_to_pos_pdf(ship_type, differences, project_number, pos_filename)
    if not result_path or not os.path.exists(result_path):
        return "POS PDF 반영 실패 또는 생성되지 않았습니다.", 500

    # ✅ PDF 미리보기용 텍스트 추출
    def extract_pdf_text(path):
        try:
            reader = PdfReader(path)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception as e:
            print("❌ PDF 텍스트 추출 실패:", e)
            return ""

    pdf_text = extract_pdf_text(result_path)
    pdf_url = "/static_downloads/" + os.path.basename(result_path)

    return render_template(
        "reflect_result.html",
        pdf_path=result_path,
        change_log=change_log,
        pdf_url=pdf_url,
        pdf_text=pdf_text
    )

@app.route("/static_downloads/<filename>")
def static_downloads(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

@app.route("/download")
def download():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "파일이 존재하지 않습니다.", 404
    return send_file(path, as_attachment=True)

# ✅ POS 파일명을 기반으로 전체 경로 반환
def get_pos_pdf_path_by_filename(ship_type, filename):
    full_path = os.path.join(POS_FOLDER, ship_type, filename)
    print(f"📄 계산된 경로: {full_path}")
    print(f"✅ 존재 여부: {os.path.exists(full_path)}")
    return full_path

if __name__ == "__main__":
    app.run(debug=True, port=5004)