from flask import Blueprint, Response, url_for
import datetime

sitemap_routes = Blueprint('sitemap_routes', __name__)

@sitemap_routes.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = []
    base_url = "https://www.skyquesttreports.com"  

    static_routes = ['/', '/qc', '/generate']
    for route in static_routes:
        pages.append({
            'loc': f"{base_url}{route}",
            'lastmod': datetime.datetime.now().strftime("%Y-%m-%d"),
        })

    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap_xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in pages:
        sitemap_xml.append('<url>')
        sitemap_xml.append(f"<loc>{page['loc']}</loc>")
        sitemap_xml.append(f"<lastmod>{page['lastmod']}</lastmod>")
        sitemap_xml.append('</url>')

    sitemap_xml.append('</urlset>')

    response = Response("\n".join(sitemap_xml), mimetype='application/xml')
    return response
