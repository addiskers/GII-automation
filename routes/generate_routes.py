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
from utils.image_utils import download_image, create_image_zip, cleanup_directory, cleanup_all_image_files
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

generate_routes = Blueprint('generate_routes', __name__)

progress_store = {}
progress_lock = Lock()

red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")

def setup_gii_driver():
    """Setup driver for GII scraping with unique user data directory"""
    from selenium import webdriver
    import tempfile
    import threading
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    
    thread_id = threading.current_thread().ident
    temp_dir = tempfile.gettempdir()
    user_data_dir = f"{temp_dir}/chrome_gii_{thread_id}_{int(time.time())}"
    options.add_argument(f'--user-data-dir={user_data_dir}')
    
    driver = webdriver.Chrome(options=options)
    return driver

def cleanup_old_zip_files():
    """Remove old zip files to prevent serving stale files"""
    try:
        for file in os.listdir('.'):
            if file.startswith('images_') and file.endswith('.zip'):
                os.remove(file)
                print(f"Removed old zip file: {file}")
    except Exception as e:
        print(f"Error cleaning up old zip files: {str(e)}")

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
        with progress_lock:
            if progress_store.get(job_id, {}).get('should_stop', False):
                return None, url, "stopped"
        
        time.sleep(0.1) 
        
        if task_type == "excel":
            driver = setup_selenium_driver()
            try:
                report_data = scrape_report(url, driver)
                if report_data:
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
                print(f"Processing image URL: {formatted_url}")
                driver.get(formatted_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                image_div = soup.find("div", class_="report-img")
                if image_div:
                    img_tag = image_div.find("img")
                    if img_tag and 'src' in img_tag.attrs:
                        img_src = img_tag['src']
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif img_src.startswith('/'):
                            img_src = urljoin(formatted_url, img_src)
                        
                        market_name = get_market_name_from_url(url)
                        print(f"Found image: {img_src} for market: {market_name}")
                        update_progress(job_id, current_url=url)
                        return (img_src, market_name), None, "success"
                    else:
                        print(f"No img tag or src attribute found in report-img div for {url}")
                else:
                    print(f"No report-img div found for {url}")
                
                return None, url, "failed"
            except TimeoutException:
                print(f"Timeout processing image URL {url}")
                return None, url, "failed"
            except WebDriverException as e:
                print(f"WebDriver error processing image URL {url}: {str(e)}")
                return None, url, "failed"
            except Exception as e:
                print(f"Error processing image URL {url}: {str(e)}")
                return None, url, "failed"
            finally:
                try:
                    driver.quit()
                except:
                    pass
                
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return None, url, "failed"

def process_urls_threaded(urls, job_id, task_type="excel", max_workers=5):
    """Process URLs using ThreadPoolExecutor with better stop functionality"""
    scraped_data = []
    failed_urls = []
    
    if len(urls) > 1000:
        max_workers = min(max_workers, 3) 
        print(f"Large batch detected ({len(urls)} URLs), reducing workers to {max_workers}")
    elif len(urls) > 5000:
        max_workers = min(max_workers, 2) 
        print(f"Very large batch detected ({len(urls)} URLs), reducing workers to {max_workers}")
    
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
    
    submitted_futures = set()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url in urls:
            with progress_lock:
                if progress_store.get(job_id, {}).get('should_stop', False):
                    break
            
            future = executor.submit(process_single_url, url, job_id, task_type)
            submitted_futures.add(future)
        
        for future in as_completed(submitted_futures):
            with progress_lock:
                should_stop = progress_store.get(job_id, {}).get('should_stop', False)
            
            if should_stop:
                for remaining_future in submitted_futures:
                    remaining_future.cancel()
                print(f"Job {job_id} stopped by user")
                break
            
            try:
                result, failed_url, status = future.result(timeout=30)  
                
                if status == "success" and result:
                    scraped_data.append(result)
                elif status == "failed" and failed_url:
                    failed_urls.append(failed_url)
                elif status == "stopped":
                    print(f"URL processing stopped: {failed_url}")
                
                with progress_lock:
                    if job_id in progress_store:
                        progress_store[job_id]['completed'] += 1
                        if failed_url:
                            progress_store[job_id]['failed'] += 1
                            
            except Exception as e:
                print(f"Error processing future: {str(e)}")
                with progress_lock:
                    if job_id in progress_store:
                        progress_store[job_id]['completed'] += 1
                        progress_store[job_id]['failed'] += 1
    
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
    
    job_id = str(uuid.uuid4())
    
    if len(urls) > 5000:
        max_workers = 2  
    elif len(urls) > 1000:
        max_workers = 3  
    else:
        max_workers = 3  
    
    print(f"Starting Excel generation for {len(urls)} URLs with {max_workers} workers")
    
    def background_task():
        scraped_data, failed_urls = process_urls_threaded(urls, job_id, "excel", max_workers)
        
        file_path = create_excel_report(scraped_data, failed_urls, job_id)
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
    
    job_id = str(uuid.uuid4())
    
    if len(urls) > 5000:
        max_workers = 3  
    elif len(urls) > 1000:
        max_workers = 4  
    else:
        max_workers = 4  
    
    print(f"Starting image generation for {len(urls)} URLs with {max_workers} workers")
    
    def background_task():
        try:
            cleanup_directory("images")
            cleanup_old_zip_files()
            
            image_data, failed_urls = process_urls_threaded(urls, job_id, "images", max_workers)
            
            downloaded_images = []
            

            image_dir = f"images_{job_id}"
            os.makedirs(image_dir, exist_ok=True)
            
            print(f"Processing {len(image_data)} image downloads...")
            
            for img_url, market_name in image_data:
                try:
                    result = download_image(img_url, name=market_name, save_dir=image_dir)
                    if result:
                        downloaded_images.append(result)
                        print(f"Downloaded: {result}")
                    else:
                        failed_urls.append(market_name)
                        print(f"Failed to download image for: {market_name}")
                except Exception as e:
                    print(f"Error downloading image for {market_name}: {str(e)}")
                    failed_urls.append(market_name)
            
            image_zip_path = None
            if downloaded_images:
                zip_filename = f"images_{job_id}_{int(time.time())}.zip"
                image_zip_path = create_image_zip(downloaded_images, zip_filename)
                print(f"Created zip file: {image_zip_path} with {len(downloaded_images)} images")
            else:
                print("No images were downloaded successfully") 
            with progress_lock:
                if job_id in progress_store:
                    progress_store[job_id].update({
                        'image_zip': image_zip_path,
                        'failed_urls': failed_urls,
                        'downloaded_count': len(downloaded_images),
                        'status': 'completed',
                        'total_images': len(image_data),
                        'current_url': 'Completed'
                    })
                    print(f"Updated progress store for job {job_id}: status=completed, images={len(downloaded_images)}")
                    
        except Exception as e:
            print(f"Error in background task for job {job_id}: {str(e)}")
            with progress_lock:
                if job_id in progress_store:
                    progress_store[job_id].update({
                        'status': 'error',
                        'error': str(e)
                    })
    
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

@generate_routes.route('/force-complete/<job_id>', methods=['POST'])
def force_complete_job(job_id):
    """Force a job to complete status for debugging"""
    try:
        with progress_lock:
            if job_id in progress_store:
                progress_store[job_id]['status'] = 'completed'
                print(f"Forced job {job_id} to completed status")
                return jsonify({'success': True, 'message': f'Job {job_id} forced to completed'})
            else:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@generate_routes.route('/cleanup', methods=['POST'])
def manual_cleanup():
    """Manual cleanup endpoint for testing"""
    try:
        from utils.image_utils import cleanup_all_image_files
        cleanup_all_image_files()
        for file in os.listdir('.'):
            if file.startswith('GII_') and file.endswith('.xlsx'):
                try:
                    os.remove(file)
                    print(f"Manually removed Excel file: {file}")
                except:
                    pass
        
        return jsonify({'success': True, 'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})