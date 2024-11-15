import scrapy
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

class GiiSpiderSpider(scrapy.Spider):
    name = "gii_spider"
    allowed_domains = ["giiresearch.com"]
    start_urls = ["https://giiresearch.com"]

    def start_requests(self):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  
        file_path = base_dir / "scraped_reports.xlsx"

        if file_path.exists():
            self.df = pd.read_excel(file_path)
            urls = self.df['Link'].tolist()
            for url in urls:
                yield scrapy.Request(url=url, callback=self.parse)
        else:
            self.logger.error(f"File '{file_path}' not found.")
            self.df = None  

    def parse(self, response):
        if self.df is not None:
            soup = BeautifulSoup(response.body, "html.parser")
            product_code_section = soup.find("div", class_="one-tab", attrs={"data-tab": "2"})
            product_code_div = product_code_section.find("div", class_="one-tab-content").find("div") if product_code_section else None
            product_code = product_code_div.get_text(strip=True).split(":")[1].strip() if product_code_div else "N/A"
            self.df.loc[self.df['Link'] == response.url, 'Product Code'] = product_code

    def closed(self, reason):
        if self.df is not None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            file_path = base_dir / "scraped_reports.xlsx"
            self.df.to_excel(file_path, index=False)
            print(f"Excel file updated with product codes at {file_path}.")
        else:
            print("No dataframe to save. Check if 'scraped_reports.xlsx' exists before running the spider.")
