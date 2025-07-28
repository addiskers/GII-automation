import requests
import os
import zipfile
import shutil
import time
from urllib.parse import urlparse

def download_image(image_url, name=None, save_dir="images"):
    """Download image with better error handling and unique naming"""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    try:
        parsed_url = urlparse(image_url)
        url_path = parsed_url.path
        extension = os.path.splitext(url_path)[-1] or '.jpg'
        
        if name:
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = os.path.join(save_dir, f"{safe_name}{extension}")
        else:
            filename = os.path.join(save_dir, f"image_{int(time.time())}{extension}")

        print(f"Downloading image from: {image_url}")
        print(f"Saving to: {filename}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(image_url, stream=True, headers=headers, timeout=30)
        response.raise_for_status()  
        
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"Successfully downloaded: {filename} ({os.path.getsize(filename)} bytes)")
                return filename
            else:
                print(f"Downloaded file is empty or doesn't exist: {filename}")
                return None
        else:
            print(f"Failed to download {image_url} - Status: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request error downloading image {image_url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error downloading image {image_url}: {str(e)}")
        return None

def create_image_zip(image_files, zip_name=None):
    """Create zip file with unique naming"""
    if zip_name is None:
        zip_name = f"images_{int(time.time())}.zip"
    
    if os.path.exists(zip_name):
        os.remove(zip_name)
        print(f"Removed existing zip file: {zip_name}")
    
    if not image_files:
        print("No images to zip")
        return None
    
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for image_file in image_files:
                if image_file and os.path.exists(image_file):
                    arcname = os.path.basename(image_file)
                    zipf.write(image_file, arcname)
                    print(f"Added to zip: {image_file} as {arcname}")
                else:
                    print(f"Skipping missing file: {image_file}")
        
        if os.path.exists(zip_name):
            print(f"Created zip file: {zip_name} ({os.path.getsize(zip_name)} bytes)")
            return zip_name
        else:
            print(f"Failed to create zip file: {zip_name}")
            return None
            
    except Exception as e:
        print(f"Error creating zip file: {str(e)}")
        return None

def cleanup_directory(directory):
    """Clean up directory more thoroughly"""
    try:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
            
            os.rmdir(directory)
            print(f"Removed directory: {directory}")
        else:
            print(f"Directory {directory} does not exist")
            
    except Exception as e:
        print(f"Error cleaning up directory {directory}: {str(e)}")

def cleanup_all_image_files():
    """Clean up all image-related files and directories"""
    try:
        for item in os.listdir('.'):
            if os.path.isdir(item) and item.startswith('images'):
                shutil.rmtree(item)
                print(f"Removed directory: {item}")
        
        for file in os.listdir('.'):
            if file.startswith('images_') and file.endswith('.zip'):
                os.remove(file)
                print(f"Removed zip file: {file}")
                
    except Exception as e:
        print(f"Error in cleanup_all_image_files: {str(e)}")

def verify_image_file(filepath):
    """Verify that an image file is valid"""
    try:
        if not os.path.exists(filepath):
            return False
        
        if os.path.getsize(filepath) == 0:
            return False       
        with open(filepath, 'rb') as f:
            header = f.read(10)
            
        if header.startswith(b'\xff\xd8'): 
            return True
        elif header.startswith(b'\x89PNG'):
            return True
        elif header.startswith(b'GIF'): 
            return True
        elif header.startswith(b'\x00\x00\x01\x00'):  
            return True
        else:
            print(f"Unknown image format for file: {filepath}")
            return True 
            
    except Exception as e:
        print(f"Error verifying image file {filepath}: {str(e)}")
        return False