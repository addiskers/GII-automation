from flask import Blueprint, render_template

main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/')
def index():
    return render_template('index.html')
from flask import Blueprint, Response


@main_routes.route('/robots.txt', methods=['GET'])
def robots():
    robots_txt = """User-agent: *
    Sitemap: https://www.skyquesttreports.com/sitemap.xml
    """
    response = Response(robots_txt, mimetype='text/plain')
    return response
