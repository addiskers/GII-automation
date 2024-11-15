from flask import Flask
from routes.main_routes import main_routes
from routes.generate_routes import generate_routes
from routes.qc_routes import qc_routes 
app = Flask(__name__)
app.register_blueprint(main_routes)
app.register_blueprint(generate_routes)
app.register_blueprint(qc_routes) 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
