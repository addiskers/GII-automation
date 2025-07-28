from flask import Flask
from routes.main_routes import main_routes
from routes.sitemap_routes import sitemap_routes
from routes.generate_routes import generate_routes
from routes.qc_routes import qc_routes 
from utils.image_utils import cleanup_all_image_files
import os

app = Flask(__name__)

def startup_cleanup():
    """Clean up old image files and zip files on application startup"""
    print("Performing startup cleanup...")
    try:
        cleanup_all_image_files()
        for file in os.listdir('.'):
            if file.startswith('GII_') and file.endswith('.xlsx'):
                try:
                    os.remove(file)
                    print(f"Removed old Excel file: {file}")
                except:
                    pass
        
        print("Startup cleanup completed")
    except Exception as e:
        print(f"Error during startup cleanup: {str(e)}")

app.register_blueprint(main_routes)
app.register_blueprint(generate_routes)
app.register_blueprint(qc_routes) 
app.register_blueprint(sitemap_routes)

if __name__ == "__main__":
    startup_cleanup()
    app.run(host="0.0.0.0", port=5000, debug=False)