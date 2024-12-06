from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import os,re
from selenium import webdriver
from time import sleep


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")



def setup_selenium_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    
    return driver


def AI(text, instruct):
    openai_client = OpenAI(api_key=api_key)

    prompt = f"{text}"
    instruction = f"""{instruct}"""

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
        ],
    )
    assistant_response = completion.choices[0].message.content
    return assistant_response

def extract_bullet_points(ul_element, level=0):
    bullet_symbols = ["•", "o", ""]
    bullet_list = []
    for li in ul_element.find_all("li", recursive=False):
        bullet_symbol = bullet_symbols[min(level, len(bullet_symbols) - 1)]
        bullet_text = []
        for content in li.contents:
            if isinstance(content, str):
                text_content = content.strip()
                if text_content:
                    bullet_text.append(text_content)
            elif content.name == "strong":
                bullet_text.append(content.get_text(strip=True))
            elif content.name == "ul":
                if bullet_text:
                    bullet_list.append(
                        f"{bullet_symbol} {' '.join(bullet_text).strip()}"
                    )
                bullet_list.extend(extract_bullet_points(content, level + 1))
                bullet_text = []
        if bullet_text:
            bullet_list.append(f"{bullet_symbol} {' '.join(bullet_text).strip()}")
    return bullet_list



def extract_report_details(soup):
        try:
            description = soup.find("div", class_="report-details-description")
            first_para = description.find("p").text.strip()
            market_name = first_para.lower().split("market", 1)[0].strip().title()
            all_paragraphs = description.find_all("p")
            remaining_paragraphs = [
                para.text for para in all_paragraphs[1:] 
                if "is poised to grow at a sustainable CAGR for the next forecast year" not in para.text
            ]
            remaining_text = "\n".join(remaining_paragraphs)
            remaining_text_instruction = "Rephrase as a market insights in 120 words in one paragraph"
            second_para = AI(remaining_text, remaining_text_instruction).strip()
            third_para = f"""
            Top-down and bottom-up approaches were used to estimate and validate the size of the {market_name} market and to estimate the size of various other dependent submarkets. The research methodology used to estimate the market size includes the following details: The key players in the market were identified through secondary research, and their market shares in the respective regions were determined through primary and secondary research. This entire procedure includes the study of the annual and financial reports of the top market players and extensive interviews for key insights from industry leaders such as CEOs, VPs, directors, and marketing executives. All percentage shares split, and breakdowns were determined using secondary sources and verified through Primary sources. All possible parameters that affect the markets covered in this research study have been accounted for, viewed in extensive detail, verified through primary research, and analyzed to get the final quantitative and qualitative data.
            """.strip()
            forth_para = f"{market_name} Market Segmental Analysis".strip()
            print(market_name)
            fifth_para = None

            p_element = soup.select_one("#tab_default_1 > div:nth-of-type(3) > p")

            if p_element:
                fifth_para = p_element.text.strip()
            else:
                div_element = soup.select_one("#tab_default_1 > div:nth-of-type(3) > div")
                if div_element:
                    fifth_para = div_element.text.strip()

            sixth_para = f"Driver of the {market_name} Market".strip()
            ninth_para=None
            seventh_para=None
            h2_elements = soup.find_all("h2", class_="report-title")
            driver_inst = f"rephrase this market is {market_name} market driver i need 100 words in one paragraph"
            restraint_inst = f"rephrase this market is {market_name} market restraint i need 100 words in one paragraph"
            h2_elements = soup.find_all("h2", class_="report-title")
            for h2 in h2_elements:
                if "market dynamics" in h2.text.lower():
                    next_div = h2.find_next_sibling("div")
                    if next_div:
                        paragraphs = next_div.find_all("p")
                        driver_processed = False
                        restraint_processed = False
                        for i, p in enumerate(paragraphs):
                            if not driver_processed and "driver" in p.text.lower():
                                diverlist = [p.get_text(strip=True)]
                                next_elements = p.find_next_siblings(limit=2)
                                for elem in next_elements:
                                    diverlist.append(elem.get_text(strip=True))
                                
                                print("Driver Content:")
                                diverlist_text = "\n".join(diverlist)
                                seventh_para = AI(diverlist_text, driver_inst).strip()
                                driver_processed = True 
                            
                            elif not restraint_processed and "restraint" in p.text.lower():
                                restraintlist = [p.get_text(strip=True)]
                                next_elements = p.find_next_siblings(limit=2)
                                for elem in next_elements:
                                    restraintlist.append(elem.get_text(strip=True))
                                
                                print("Restraint Content:")
                                restraintlist_text = "\n".join(restraintlist)
                                ninth_para = AI(restraintlist_text, restraint_inst).strip()
                                restraint_processed = True
                            if driver_processed and restraint_processed:
                                break
            if not seventh_para:
                        ins_seventh = f"Write a driver for {market_name} in 100 words in one paragraph only."
                        seventh_para = AI('',ins_seventh).strip()

            if not ninth_para:
                        ins_ninth = f"Write a restraint for {market_name} in 100 words in one paragraph only."
                        ninth_para = AI('',ins_ninth).strip()

            eighth_para = f"Restraints in the {market_name} Market".strip()
            tenth_para = f"Market Trends of the {market_name} Market".strip()
            eleven_inst = f"Elaborate it as a market trend for {market_name} market in 100 words in one paragraph "
            for h2 in h2_elements:
                if "market trend" in h2.text.lower():
                    next_div1 = h2.find_next_sibling("div")
                    if next_div1:
                        first_li = next_div1.find("li")
                        if first_li:
                            eleven_para = AI(first_li.get_text(strip=True), eleven_inst).strip()

                        else:
                            print("No <li> found in the div.")
            

            description_content = "\n\n".join(
                [
                    first_para,
                    second_para,
                    third_para,
                    forth_para,
                    fifth_para,
                    sixth_para,
                    seventh_para,
                    eighth_para,
                    ninth_para,
                    tenth_para,
                    eleven_para,
                ]
            )  
            return description_content
        except Exception as e:
            print(f"Error extracting report details: {str(e)}")
            return "Report details not available."
    

def format_url(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def scrape_report(url,driver):
    try:
        driver = driver
        formatted_url = format_url(url)
        driver.get(formatted_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "tabs-bar")))
        
        page_source1 = driver.page_source
        soup = BeautifulSoup(page_source1, "html.parser")
        toc_tab = driver.find_element(By.CSS_SELECTOR, "a[href='#tab_default_3']")
        driver.execute_script("arguments[0].scrollIntoView(true);", toc_tab)
        
        sleep(1)
        driver.execute_script("arguments[0].click();", toc_tab)
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "tab_default_3")))
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "special-toc-class")))
        page_source = driver.page_source
        soup_toc = BeautifulSoup(page_source, "html.parser")
        toc_section = soup_toc.find("div", {"class": "special-toc-class"})
        if toc_section:
            ul_element = toc_section.find("ul")
            if ul_element:
                bullet_points = extract_bullet_points(ul_element)

        bullet_points_str = "\n".join(bullet_points)
        lines = bullet_points_str.strip().split("\n")
        toc_content = "\n".join(lines)
        required_keywords = [
                "• Introduction",
                "o Objectives of the Study",
                "• Market Dynamics & Outlook",
                "o Market Dynamics",
                "o Degree of Competition",
                " US",
                " Canada",
                "• Key Company Profiles",
                " Company Overview",
                " Business Segment Overview",
                " Financial Updates",
                " Key Developments"
            ]
        if not all(keyword in toc_content for keyword in required_keywords):
            toc_content = "Error"
    except Exception as e:  
            print(f"Error extracting table of contents for URL {url}: {str(e)}")
            
   
    summary = extract_report_details(soup)
    
    head_div = soup.find("div", class_="d-sm-flex flex-sm-row-reverse align-items-center title")
    title = head_div.find("h1").text.strip() if head_div else ""
    print(title)
    if "market name" in title.lower() or "market name," in title.lower():
        title = "Error"


    
    code = soup.find("div", class_="report-segment-data max-width-640")
    report_id_tag = code.find("b", string="Report ID:") if code else None
    product_code = (
        report_id_tag.next_sibling.strip() if report_id_tag and report_id_tag.next_sibling else ""
    )
    product_code = re.sub(r"\W+", "", product_code)
    
    report_len_tag = code.find("b", string="Pages:") if code else None
    length = (
        report_len_tag.next_sibling.strip() if report_len_tag and report_len_tag.next_sibling else ""
    )
    length = re.sub(r"\D+", "", length)
    sector = soup.find("ol", class_="MuiBreadcrumbs-ol css-nhb8h9").find_all("li", class_="MuiBreadcrumbs-li")[1].text.strip() if soup.find("ol", class_="MuiBreadcrumbs-ol css-nhb8h9") else ""
    
   
    try:
        h2_elements = soup.find_all("h2", class_="report-title")  
        companies_list = []

        for h2 in h2_elements:
            if "competitive landscape" in h2.text.lower():  
                next_div1 = h2.find_next_sibling("div")  
                if next_div1:
                    first_ul = next_div1.find("ul")  
                    if first_ul:
                        for li in first_ul.find_all("li"): 
                            company = li.text.strip()
                            if company and company != '&nbsp;':  
                                companies_list.append(f"◦ {company}")
                    break 

        cell_companies = "\n".join(companies_list)
        companies_count = len(companies_list)
        if not cell_companies or companies_count< 5:
            cell_companies = "Error"  

    except Exception as e:
        print(f"Error extracting companies: {str(e)}")
    print(cell_companies)

        
    seg = soup.find("td", class_="fw-bold", string="Segments covered")
    segments_list = []
    try:
        if seg:
            next_td = seg.find_next_sibling()
            next_td_ul = next_td.find("ul")
            next_td_li = next_td_ul.find_all("li", recursive=False) if next_td_ul else []
            for li in next_td_li:
                main_category = li.contents[0].strip()
                subcategory = li.find("ul")
                if subcategory:
                    subcategory_items = [item.strip() for item in subcategory.stripped_strings]
                    subcategory_text = ", ".join(subcategory_items)
                    formatted_output = f"By {main_category} ({subcategory_text})"
                else:
                    formatted_output = f"By {main_category}"
                segments_list.append(formatted_output)
        products = ", ".join(segments_list)
    except Exception as e:
            segments_list = "Error"
            print(f"Error extracting segments for URL {url}: {str(e)}")


    image_div = soup.find("div", class_="report-img")
    image_url = None
    if image_div:
        img_tag = image_div.find("img")
        if img_tag and 'src' in img_tag.attrs:
            image_url = img_tag['src']



    first_para = soup.find("div", class_="report-details-description").find("p").text.strip()
    value_pattern = re.compile(r"USD (\d+\.?\d*)\s*(Billion|Million|Trillion|billion|million|trillion)")
    year_pattern = re.compile(r"\b(2022|2023|2031)\b")
    cagr_pattern = re.compile(r"CAGR of (\d+\.?\d*)\s*%")
    
    currency_values = value_pattern.findall(first_para)
    cagr = cagr_pattern.search(first_para)
    
    data_2022 = currency_values[0][0] if currency_values else None
    data_2023 = currency_values[1][0] if len(currency_values) > 1 else None
    data_2031 = currency_values[2][0] if len(currency_values) > 2 else None
    currency = "USD " + currency_values[0][1].title() if currency_values else None
    cagr_value = cagr.group(1) + "%" if cagr else ""
    
    countries_list = [
        "USA", "Canada", "Germany", "Spain", "Italy", "France", "UK", 
        "China", "India", "Japan", "South Korea", "Brazil", 
        "GCC Countries", "South Africa"
    ]
    formatted_countries = [f"◦ {country}" for country in countries_list]
    cell_countries = "\n".join(formatted_countries)
    
    
    price_single = "5300"
    price_sitelesense = "6200"
    price_enterprise = "7100"
    
    return {
            "title": title,
            "product_code": product_code,
            "url": url,
            "date": "",  
            "length": length,
            "headline": "",  
            "price_single_user": price_single,
            "price_site_license": price_sitelesense,
            "price_enterprise_license": price_enterprise,
            "description": summary,
            "toc": toc_content,
            "agenda": "",  
            "executive_summary": "",  
            "sector": sector,
            "countries_covered": cell_countries,
            "companies_mentioned": cell_companies,
            "products_mentioned": products,
            "data_2022": data_2022,
            "data_2023": data_2023,
            "data_2031": data_2031,
            "cagr": cagr_value,
            "currency": currency,
            "image_url": image_url
        }
   

