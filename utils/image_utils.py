import requests
import os
import zipfile

def download_image(image_url, name=None, save_dir="images"):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    if name:
        extension = os.path.splitext(image_url)[-1] 
        filename = os.path.join(save_dir, f"{name}{extension}")
    else:
        filename = os.path.join(save_dir, os.path.basename(image_url))

    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filename
        else:
            print(f"Failed to download {image_url}")
            return None
    except Exception as e:
        print(f"Error downloading image {image_url}: {str(e)}")
        return None

def create_image_zip(image_files, zip_name="images.zip"):
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for image_file in image_files:
            if image_file:
                zipf.write(image_file, os.path.basename(image_file))
    return zip_name

def cleanup_directory(directory):
    if os.path.exists(directory):
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(directory)
