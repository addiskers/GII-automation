import scrapy
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import re

class QcCheckSpider(scrapy.Spider):
    name = "qc_check_spider"
    allowed_domains = ["skyquestt.com"]

    def __init__(self, links, output_path, *args, **kwargs):
        super(QcCheckSpider, self).__init__(*args, **kwargs)
        self.links = links.split(",")
        self.output_path = output_path
        self.scraped_data = []  
    def start_requests(self):
        for link in self.links:
            yield scrapy.Request(url=link, callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body, "html.parser")
        report_info = soup.find("div", class_="report-segment-data")
        product_code = (
            report_info.find("b", string="Report ID:").next_sibling.strip()
            if report_info and report_info.find("b", string="Report ID:")
            else "N/A"
        )
        product_code = re.sub(r"\W+", "", product_code) if product_code != "N/A" else "N/A"
        self.scraped_data.append({
            "Link": response.url,
            "Product Code_scraped": product_code,
        })

    def closed(self, reason):
        if self.scraped_data:
            df = pd.DataFrame(self.scraped_data)
            output_path = Path(self.output_path)
            df.to_excel(output_path, index=False)
            self.log(f"Scraped product codes saved to {output_path}")
        else:
            self.log("No data scraped. Ensure the links are correct.")
