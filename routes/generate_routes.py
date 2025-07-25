from flask import Blueprint, request, render_template, send_file, jsonify
from utils.scraper import setup_selenium_driver, scrape_report, format_url
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import json
from utils.image_utils import download_image, create_image_zip, cleanup_directory
from urllib.parse import urlparse
from bs4 import BeautifulSoup

generate_routes = Blueprint('generate_routes', __name__)

# Global progress tracking
progress_store = {}
progress_lock = Lock()

red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")

def get_market_name_from_url(url):
    parsed_url = urlparse(url)
    return os.path.basename(parsed_url.path)

def update_progress(job_id, **kwargs):
    """Thread-safe progress update"""
    with progress_lock:
        if job_id in progress_store:
            progress_store[job_id].update(kwargs)

def process_single_url(url, job_id, task_type="excel"):
    """Process a single URL and update progress"""
    try:
        # Check if job should stop
        with progress_lock:
            if progress_store.get(job_id, {}).get('should_stop', False):
                return None, url, "stopped"
        
        if task_type == "excel":
            driver = setup_selenium_driver()
            try:
                report_data = scrape_report(url, driver)
                if report_data:
                    # Update current URL being processed
                    update_progress(job_id, current_url=url)
                    return report_data, None, "success"
                else:
                    return None, url, "failed"
            finally:
                driver.quit()
        
        elif task_type == "images":
            formatted_url = format_url(url)
            driver = setup_selenium_driver()
            try:
                driver.get(formatted_url)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                image_div = soup.find("div", class_="report-img")
                if image_div:
                    img_tag = image_div.find("img")
                    if img_tag and 'src' in img_tag.attrs:
                        market_name = get_market_name_from_url(url)
                        return (img_tag['src'], market_name), None, "success"
                return None, url, "failed"
            finally:
                driver.quit()
                
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return None, url, "failed"

def process_urls_threaded(urls, job_id, task_type="excel", max_workers=5):
    """Process URLs using ThreadPoolExecutor"""
    scraped_data = []
    failed_urls = []
    
    # Initialize progress
    with progress_lock:
        progress_store[job_id] = {
            'total': len(urls),
            'completed': 0,
            'failed': 0,
            'status': 'running',
            'current_url': '',
            'should_stop': False,
            'task_type': task_type
        }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(process_single_url, url, job_id, task_type): url 
            for url in urls
        }
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            
            # Check if should stop
            with progress_lock:
                if progress_store.get(job_id, {}).get('should_stop', False):
                    break
            
            try:
                result, failed_url, status = future.result()
                
                if status == "success" and result:
                    scraped_data.append(result)
                elif status == "failed" and failed_url:
                    failed_urls.append(failed_url)
                
                # Update progress
                with progress_lock:
                    if job_id in progress_store:
                        progress_store[job_id]['completed'] += 1
                        if failed_url:
                            progress_store[job_id]['failed'] += 1
                            
            except Exception as e:
                failed_urls.append(url)
                with progress_lock:
                    if job_id in progress_store:
                        progress_store[job_id]['completed'] += 1
                        progress_store[job_id]['failed'] += 1
    
    # Mark as completed
    with progress_lock:
        if job_id in progress_store:
            if progress_store[job_id].get('should_stop', False):
                progress_store[job_id]['status'] = 'stopped'
            else:
                progress_store[job_id]['status'] = 'completed'
    
    return scraped_data, failed_urls

@generate_routes.route('/generate', methods=['POST'])
def generate_excel():
    urls = request.form.get('urls').strip().split('\n')
    urls = [url.strip() for url in urls if url.strip()]
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Start processing in background thread
    def background_task():
        scraped_data, failed_urls = process_urls_threaded(urls, job_id, "excel", max_workers=8)
        
        # Create Excel file
        file_path = create_excel_report(scraped_data, failed_urls, job_id)
        
        # Update progress with file path
        with progress_lock:
            if job_id in progress_store:
                progress_store[job_id]['file_path'] = file_path
                progress_store[job_id]['failed_urls'] = failed_urls
    
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    return render_template('index.html', job_id=job_id, task_type='excel')

@generate_routes.route('/generate-images', methods=['POST'])
def generate_images():
    urls = request.form.get('urls').strip().split('\n')
    urls = [url.strip() for url in urls if url.strip()]
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Start processing in background thread
    def background_task():
        image_data, failed_urls = process_urls_threaded(urls, job_id, "images", max_workers=6)
        
        # Clean up and download images
        cleanup_directory("images")
        
        downloaded_images = []
        for img_url, market_name in image_data:
            result = download_image(img_url, name=market_name)
            if result:
                downloaded_images.append(result)
            else:
                failed_urls.append(market_name)
        
        # Create zip file
        image_zip_path = create_image_zip(downloaded_images)
        
        # Update progress with file path
        with progress_lock:
            if job_id in progress_store:
                progress_store[job_id]['image_zip'] = image_zip_path
                progress_store[job_id]['failed_urls'] = failed_urls
    
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    return render_template('index.html', job_id=job_id, task_type='images')

@generate_routes.route('/progress/<job_id>')
def get_progress(job_id):
    """Get progress for a specific job"""
    with progress_lock:
        progress_data = progress_store.get(job_id, {})
        
        if not progress_data:
            return jsonify({'error': 'Job not found'}), 404
        
        # Calculate percentage
        total = progress_data.get('total', 1)
        completed = progress_data.get('completed', 0)
        percentage = int((completed / total) * 100) if total > 0 else 0
        
        return jsonify({
            'total': total,
            'completed': completed,
            'failed': progress_data.get('failed', 0),
            'percentage': percentage,
            'status': progress_data.get('status', 'unknown'),
            'current_url': progress_data.get('current_url', ''),
            'task_type': progress_data.get('task_type', 'excel'),
            'file_path': progress_data.get('file_path'),
            'image_zip': progress_data.get('image_zip'),
            'failed_urls': progress_data.get('failed_urls', [])
        })

@generate_routes.route('/stop/<job_id>', methods=['POST'])
def stop_job(job_id):
    """Stop a running job"""
    with progress_lock:
        if job_id in progress_store:
            progress_store[job_id]['should_stop'] = True
            progress_store[job_id]['status'] = 'stopping'
            return jsonify({'success': True, 'message': 'Job stop requested'})
        else:
            return jsonify({'error': 'Job not found'}), 404

def create_excel_report(scraped_data, failed_urls, job_id):
    """Generates Excel report from the scraped data and saves it."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Scraped Data"

    headers = ["Title", "Product Code", "URL", "Date", "Length", "Headline",
               "Price: Single User\nFormat: PDF & Excel", "Price: Site License\nFormat: PDF & Excel",
               "Price: Enterprise License\nFormat: PDF & Excel", "Description", "Table of Content",
               "Agenda / Schedule", "Executive Summary", "Sector", "Countries Covered",
               "Companies Mentioned", "Products Mentioned", "2023", "2024", "2032", "CAGR %", "Currency"]
    ws.append(headers)

    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    bold_font = Font(bold=True)
    for cell in ws[1]:
        cell.fill = yellow_fill
        cell.font = bold_font

    for row_idx, item in enumerate(scraped_data, start=2):
        ws.append([
            item.get("title", "N/A"),
            item.get("product_code", "N/A"),
            item.get("url", "N/A"),
            item.get("date", "N/A"),
            item.get("length", "N/A"),
            item.get("headline", "N/A"),
            item.get("price_single_user", "N/A"),
            item.get("price_site_license", "N/A"),
            item.get("price_enterprise_license", "N/A"),
            item.get("description", "N/A"),
            item.get("toc", "N/A"),
            item.get("agenda", "N/A"),
            item.get("executive_summary", "N/A"),
            item.get("sector", "N/A"),
            item.get("countries_covered", "N/A"),
            item.get("companies_mentioned", "N/A"),
            item.get("products_mentioned", "N/A"),
            item.get("data_2022", "N/A"),
            item.get("data_2023", "N/A"),
            item.get("data_2031", "N/A"),
            item.get("cagr", "N/A"),
            item.get("currency", "N/A")
        ])
        apply_error_formatting(ws, row_idx)

    if failed_urls:
        failed_ws = wb.create_sheet(title="Failed URLs")
        failed_ws.append(["Failed URLs"])
        for failed_url in failed_urls:
            failed_ws.append([failed_url])

    file_path = os.path.join(os.getcwd(), f'GII_{job_id}.xlsx')
    wb.save(file_path)
    return file_path

def apply_error_formatting(ws, row_idx):
    for cell in ws[row_idx]:
        if cell.value == "Error" or cell.value == "Report details not available.":
            for row_cell in ws[row_idx]:
                row_cell.fill = red_fill

@generate_routes.route('/download-images', methods=['GET'])
def download_images():
    zip_file_path = request.args.get('image_zip')
    return send_file(zip_file_path, as_attachment=True)

@generate_routes.route('/download')
def download_file():
    file_path = request.args.get('file_path')
    return send_file(file_path, as_attachment=True)