# routes/qc_routes.py
from pathlib import Path
from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for
from utils.gii_utils import scrape_gii_reports
import subprocess
import os
import pandas as pd 
qc_routes = Blueprint('qc_routes', __name__)


@qc_routes.route('/qc', methods=['GET'])
def qc():
    base_dir = Path(__file__).resolve().parent.parent
    excel_path = base_dir / "scraped_reports.xlsx"

    total_count = None
    if excel_path.exists():
        df = pd.read_excel(excel_path)
        total_count = len(df)

    return render_template('qc.html', total_count=total_count)


@qc_routes.route('/qc/Refresh', methods=['POST'])
def qc_refresh():
    total_count = scrape_gii_reports()

    scrapy_project_path = os.path.join(os.path.dirname(__file__), '..', 'gii_scraper')
    scrapy_command = ["scrapy", "crawl", "gii_spider"]
    result = subprocess.run(scrapy_command, cwd=scrapy_project_path, capture_output=True, text=True)

    if result.returncode != 0:
        return jsonify({"error": "Scrapy spider failed", "details": result.stderr}), 500

    return redirect(url_for('qc_routes.qc'))



@qc_routes.route("/qc/check", methods=["POST"])
def qc_check():
    from pathlib import Path

    links = request.form.get("qc_link", "").strip().split("\n")
    links = [link.strip() for link in links if link.strip()]

    if not links:
        return jsonify({"error": "No links provided"}), 400

    base_dir = Path(__file__).resolve().parent.parent
    excel_path = base_dir / "scraped_reports.xlsx"
    output_path = base_dir / "matched_reports.xlsx"
    scraped_codes_path = base_dir / "scraped_codes.xlsx"

    if not excel_path.exists():
        return jsonify({"error": "scraped_reports.xlsx not found"}), 404

    result = subprocess.run(
        [
            "scrapy",
            "crawl",
            "qc_check_spider",
            "-a",
            f"links={','.join(links)}",
            "-a",
            f"output_path={str(scraped_codes_path)}",
        ],
        cwd=str(base_dir / "gii_scraper"),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not scraped_codes_path.exists():
        return jsonify({"error": "Failed to scrape links", "details": result.stderr}), 500

    scraped_codes_df = pd.read_excel(scraped_codes_path)
    scraped_reports_df = pd.read_excel(excel_path)

    scraped_codes_df["Product Code_scraped"] = scraped_codes_df["Product Code_scraped"].str.strip().str.replace(r"\W+", "", regex=True)
    scraped_reports_df["Product Code"] = scraped_reports_df["Product Code"].str.strip().str.replace(r"\W+", "", regex=True)

    comparison_results = scraped_codes_df[["Link","Product Code_scraped"]].copy()

    comparison_results["Match Status"] = comparison_results["Product Code_scraped"].apply(
        lambda scraped_code: "Yes" if scraped_code in scraped_reports_df["Product Code"].values else "No"
    )

    comparison_results = comparison_results.merge(
    scraped_reports_df[["Product Code", "Published Date"]],
    how="left", 
    left_on="Product Code_scraped", 
    right_on="Product Code"
    ).drop(columns="Product Code") 

    comparison_results.to_excel(output_path, index=False)
    print(f"Matched reports saved to {output_path}")

    return send_file(output_path, as_attachment=True, download_name="matched_reports.xlsx")



@qc_routes.route("/qc/add", methods=["POST"])
def qc_add():
    base_dir = Path(__file__).resolve().parent.parent
    master_path = base_dir / "master_reports.xlsx"
    scraped_path = base_dir / "scraped_reports.xlsx"
    missing_path = base_dir / "missing_reports.xlsx"

    if not scraped_path.exists():
        return jsonify({"error": "scraped_reports.xlsx not found"}), 404
    scraped_df = pd.read_excel(scraped_path)

    if not master_path.exists():
        scraped_df.to_excel(master_path, index=False)
        return jsonify({"message": "Master report created as it didn't exist."})

    master_df = pd.read_excel(master_path)

    master_df["Product Code"] = master_df["Product Code"].str.strip().str.replace(r"\W+", "", regex=True)
    scraped_df["Product Code"] = scraped_df["Product Code"].str.strip().str.replace(r"\W+", "", regex=True)

    missing_codes = set(master_df["Product Code"]) - set(scraped_df["Product Code"])
    missing_df = master_df[master_df["Product Code"].isin(missing_codes)]
    
    missing_df.to_excel(missing_path, index=False)

    new_reports = scraped_df[~scraped_df["Product Code"].isin(master_df["Product Code"])]
    updated_master_df = pd.concat([master_df, new_reports], ignore_index=True)
    updated_master_df.to_excel(master_path, index=False)

    print(f"Master report updated at {master_path}")
    print(f"Missing reports saved to {missing_path}")

    return send_file(missing_path, as_attachment=True, download_name="missing_reports.xlsx")
