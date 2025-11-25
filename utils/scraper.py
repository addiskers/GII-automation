from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import os, re, time, threading
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

thread_local = threading.local()

def get_driver():
    """Get or create a driver for the current thread"""
    if not hasattr(thread_local, 'driver'):
        thread_local.driver = setup_selenium_driver()
    return thread_local.driver

def cleanup_driver():
    """Clean up driver for current thread"""
    if hasattr(thread_local, 'driver'):
        try:
            thread_local.driver.quit()
        except:
            pass
        finally:
            delattr(thread_local, 'driver')

def setup_selenium_driver():
    """Setup Chrome driver with optimized options for concurrent processing"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-first-run')
    options.add_argument('--disable-default-apps')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    
    import threading
    import tempfile
    thread_id = threading.current_thread().ident
    temp_dir = tempfile.gettempdir()
    user_data_dir = f"{temp_dir}/chrome_user_data_{thread_id}_{int(time.time())}"
    options.add_argument(f'--user-data-dir={user_data_dir}')
    
    options.add_argument('--memory-pressure-off')
    options.add_argument('--max_old_space_size=4096')
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)  
    driver.implicitly_wait(10)
    
    return driver

def AI(text, instruct):
    """AI processing with error handling"""
    try:
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
    except Exception as e:
        print(f"AI processing error: {str(e)}")
        return "Error in AI processing"

def extract_bullet_points(ul_element, level=0):
    """Extract bullet points with error handling"""
    try:
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
    except Exception as e:
        print(f"Error extracting bullet points: {str(e)}")
        return ["Error extracting bullet points"]

def extract_report_details(soup):
    """Extract report details with comprehensive error handling"""
    try:          
        description = soup.find("div", class_="report-details-description")
        if not description:
            return "Report details not available."
            
        first_para_elem = description.find("p")
        if not first_para_elem:
            return "Report details not available."
            
        first_para = first_para_elem.text.strip()
        market_name = re.split(r'market', first_para, flags=re.IGNORECASE, maxsplit=1)[0].strip()
        
        all_paragraphs = description.find_all("p")
        remaining_paragraphs = []
        skip_phrase = "is poised to grow at a sustainable CAGR for the next forecast year"

        for para in all_paragraphs[1:]:
            if para.find("strong"):
                break
            if skip_phrase in para.get_text():
                continue
            remaining_paragraphs.append(para.get_text())

        if not remaining_paragraphs:
            first_strong_encountered = False
            
            for para in all_paragraphs[1:]:
                if para.find("strong"):
                    if not first_strong_encountered:
                        first_strong_encountered = True
                        if skip_phrase not in para.get_text():
                            remaining_paragraphs.append(para.get_text())
                        continue
                    else:
                        break

                if skip_phrase in para.get_text():
                    continue

                remaining_paragraphs.append(para.get_text())
                
        remaining_text = "\n".join(remaining_paragraphs)
        remaining_text_instruction = f"Rephrase the following content as market insights {market_name} in exactly 120 words in one paragraph without referencing specific dates or timeframes."
        
        second_para = AI(remaining_text, remaining_text_instruction).strip() if remaining_text else f"Market insights for {market_name} market."
        
        third_para = f"""
        Top-down and bottom-up approaches were used to estimate and validate the size of the {market_name} market and to estimate the size of various other dependent submarkets. The research methodology used to estimate the market size includes the following details: The key players in the market were identified through secondary research, and their market shares in the respective regions were determined through primary and secondary research. This entire procedure includes the study of the annual and financial reports of the top market players and extensive interviews for key insights from industry leaders such as CEOs, VPs, directors, and marketing executives. All percentage shares split, and breakdowns were determined using secondary sources and verified through Primary sources. All possible parameters that affect the markets covered in this research study have been accounted for, viewed in extensive detail, verified through primary research, and analyzed to get the final quantitative and qualitative data.
        """.strip()
        
        forth_para = f"{market_name} Market Segments Analysis".strip()
        
        h2_elements = soup.find_all("h2", class_="report-title")
        if not h2_elements: 
            h2_elements = soup.find_all("div", class_="report-title")
            
        fifth_para = f"The {market_name} market is segmented into various categories for comprehensive analysis."
        
        # Segments analysis
        for h2 in h2_elements:
            if "segments" in h2.get_text(strip=True).replace('\xa0', ' ').lower() or "segmental" in h2.get_text(strip=True).replace('\xa0', ' ').lower():
                next_element = h2.find_next_sibling() 
                
                while next_element:
                    if next_element.name == "p": 
                        fifth_para = next_element.get_text(strip=True)
                        break
                    elif next_element.name == "div": 
                        first_p = next_element.find("p") 
                        if first_p:
                            fifth_para = first_p.get_text(strip=True)
                        break
                    next_element = next_element.find_next_sibling()  
                
                break

        sixth_para = f"Driver of the {market_name} Market".strip()
        ninth_para = None
        seventh_para = None
        
        driver_inst = f"rephrase this market is {market_name} market driver i need 100 words in one paragraph without referencing specific dates or timeframes."
        restraint_inst = f"rephrase this market is {market_name} market restraint i need 100 words in one paragraph without referencing specific dates or timeframes."
        
        # Market dynamics processing with fallbacks
        for h2 in h2_elements:
            if "market dynamics" in h2.get_text(strip=True).replace('\xa0', ' ').lower():
                next_div = h2.find_next_sibling("div")
                if next_div:
                    h3_elements = next_div.find_all("h3")
                    
                    driver_processed = False
                    restraint_processed = False
                    
                    for h3 in h3_elements:
                        if not driver_processed and "driver" in h3.text.lower():
                            diverlist = []
                            first_li_text = None
                            sibling = h3.find_next_sibling()
                            while sibling and not first_li_text:
                                if sibling.name == "ul":
                                    li_tag = sibling.find("li")
                                    if li_tag:
                                        first_li_text = li_tag.get_text(strip=True)
                                        diverlist.append(first_li_text)
                                sibling = sibling.find_next_sibling()

                            if diverlist:
                                seventh_para = AI(diverlist, driver_inst).strip()
                                driver_processed = True

                        elif not restraint_processed and "restraint" in h3.text.lower():
                            restraintlist = []
                            first_li_text = None

                            sibling = h3.find_next_sibling()
                            while sibling and not first_li_text:
                                if sibling.name == "ul":
                                    li_tag = sibling.find("li")
                                    if li_tag:
                                        first_li_text = li_tag.get_text(strip=True)
                                        restraintlist.append(first_li_text)
                                sibling = sibling.find_next_sibling()

                            if restraintlist:
                                ninth_para = AI(restraintlist, restraint_inst).strip()
                                restraint_processed = True
                                
                        if driver_processed and restraint_processed:
                            break
                break
                      
        # Fallback for drivers and restraints
        if not seventh_para:
            fallback_driver_prompt = f"Write a Key Market Driver for the Global {market_name} Market in one paragraph (100 words only). without referencing specific dates or timeframes."
            seventh_para = AI([], fallback_driver_prompt).strip()

        if not ninth_para:
            fallback_restraint_prompt = f"Write a Key Market Restraint for the Global {market_name} Market in one paragraph (100 words only). without referencing specific dates or timeframes."
            ninth_para = AI([], fallback_restraint_prompt).strip()
                   
        eighth_para = f"Restraints in the {market_name} Market".strip()
        tenth_para = f"Market Trends of the {market_name} Market".strip()
        eleven_para = None
        eleven_inst = f"Elaborate it as a market trend for {market_name} market in 100 words in one paragraph without referencing specific dates or timeframes."
        
        for h2 in h2_elements:
            if "trend" in h2.get_text(strip=True).replace('\xa0', ' ').lower():
                next_div1 = h2.find_next_sibling("div")
                if next_div1:
                    first_li = next_div1.find("li")
                    if first_li:
                        eleven_para = AI(first_li.get_text(strip=True), eleven_inst).strip()
                    else:
                        trendspara = soup.find("div", class_="key_market_trends")
                        if trendspara:
                            paragraphs = trendspara.find_all("p")
                            found_strong = False
                            for p in paragraphs:
                                if found_strong and not p.find("strong"):
                                   eleven_para = AI(p.get_text(strip=True), eleven_inst).strip()                                        
                                   break
                                if p.find("strong"):
                                    found_strong = True
                break
                    
        if not eleven_para:
            fallback_trend_prompt = f"Write a Key Market Trend for the Global {market_name} Market in one paragraph (100 words only). without referencing specific dates or timeframes."
            eleven_para = AI([], fallback_trend_prompt).strip()

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
    """Format URL with error handling"""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        return url
    except:
        return url

def format_market_title(title):
    """Format market title with error handling"""
    try:
        if "Growth Analysis," not in title:
            return title
            
        pre_growth, post_growth = title.split("Growth Analysis,", 1)
        
        def smart_split(text):
            segments = []
            current_segment = []
            paren_count = 0
            
            for char in text:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                
                if char == ',' and paren_count == 0:
                    segments.append(''.join(current_segment).strip())
                    current_segment = []
                else:
                    current_segment.append(char)
                    
            if current_segment:
                segments.append(''.join(current_segment).strip())
                
            return segments
        
        segments = smart_split(post_growth)
        
        processed_segments = []
        for i, segment in enumerate(segments):
            if i < 2:  
                processed_segments.append(segment)
            else:
                base_segment = segment.split('(')[0].strip()
                processed_segments.append(base_segment)
        
        return f"{pre_growth}Growth Analysis, {', '.join(processed_segments)}"
    except Exception as e:
        print(f"Error formatting title: {str(e)}")
        return title

def format_segments(input_string):
    """Format segments with error handling"""
    try:
        if not input_string.strip().startswith("By"):
            input_string = "By " + input_string
        
        if " - " in input_string:
            input_string = input_string.split(" - ")[0].strip()
        
        raw_segments = []
        parts = input_string.split(", By ")
        for i, part in enumerate(parts):
            if i == 0:  
                raw_segments.append(part)
            else: 
                raw_segments.append("By " + part)
        
        formatted_segments = []
        for i, segment in enumerate(raw_segments):
            segment = segment.strip()
            
            if "(" in segment:
                segment_name = segment.split("(")[0].strip()
                if segment_name.startswith("By "):
                    segment_name = segment_name[3:].strip()
                
                paren_level = 0
                subsegment_text = ""
                in_parentheses = False
                
                for char in segment:
                    if char == '(':
                        paren_level += 1
                        if paren_level == 1:  
                            in_parentheses = True
                        else: 
                            subsegment_text += char
                    elif char == ')':
                        paren_level -= 1
                        if paren_level == 0: 
                            in_parentheses = False
                        else:  
                            subsegment_text += char
                    elif in_parentheses:
                        subsegment_text += char
                
                if subsegment_text and i < 2: 
                    subsegments = subsegment_text.split(", ")
                    first_two = ", ".join(subsegments[:2])
                    formatted_segments.append(f"By {segment_name} ({first_two})")
                else:  
                    formatted_segments.append(f"By {segment_name}")
            else:
                segment_name = segment
                if segment_name.startswith("By "):
                    segment_name = segment_name[3:].strip()
                formatted_segments.append(f"By {segment_name}")
        
        return ", ".join(formatted_segments)
    except Exception as e:
        print(f"Error formatting segments: {str(e)}")
        return input_string

def scrape_report(url, driver=None):
    """Main scraping function with comprehensive error handling"""
    if driver is None:
        driver = get_driver()
        
    try:
        formatted_url = format_url(url)
        driver.get(formatted_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "tabs-bar")))
        page_source1 = driver.page_source
        soup = BeautifulSoup(page_source1, "html.parser")
        
        toc_content = "Error"
        try:
            toc_tab = driver.find_element(By.CSS_SELECTOR, "a[href='#tab_default_3']")
            driver.execute_script("arguments[0].scrollIntoView(true);", toc_tab)
            time.sleep(1)
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
                        "• Key Company Profiles",
                      
                    ]
                    print(f"Extracted TOC Content for URL {url}:\n{toc_content}")
                    if not all(keyword in toc_content for keyword in required_keywords):
                        toc_content = "Error"
        except Exception as e:  
            print(f"Error extracting table of contents for URL {url}: {str(e)}")
            toc_content = "Error"
       
        summary = extract_report_details(soup)
        
        # Extract title
        title = "Error"
        try:
            head_div2 = soup.find("div", class_="d-sm-flex flex-sm-row-reverse align-items-center title report-second-header")
            head_div1 = soup.find("div", class_="report-main-header")
            
            if head_div2 and head_div1:
                title2 = head_div2.find("h2").text.strip().split("By",1)[1]
                result = format_segments(title2)
                title1 = " ".join(head_div1.find("h1").get_text().split())
                titles = title1 + ", " + result
                title = format_market_title(titles) 
                normalized_title = title.lower().replace("–", "-")
                if "industry forecast 2025-2032" not in normalized_title:
                    title += " - Industry Forecast 2025-2032"

                if "market name" in normalized_title or "market name," in normalized_title:
                    title = "Error"
                print(title)
        except Exception as e:
            print(f"Error extracting title: {str(e)}")
            title = "Error"
        print(f"Title extracted: {title}")
        # Extract basic info
        product_code = "N/A"
        length = "N/A"
        region = "Global"
        
        try:
            code = soup.find("div", class_="report-segment-data max-width-640")
            if code:
                report_id_tag = code.find("b", string="Report ID:")
                if report_id_tag and report_id_tag.next_sibling:
                    product_code = re.sub(r"\W+", "", report_id_tag.next_sibling.strip())
                
                report_len_tag = code.find("b", string="Pages:")
                if report_len_tag and report_len_tag.next_sibling:
                    length = re.sub(r"\D+", "", report_len_tag.next_sibling.strip())
                
                region_len_tag = code.find("b", string="Region:")
                if region_len_tag and region_len_tag.next_sibling:
                    region = re.sub(r"\W+", "", region_len_tag.next_sibling.strip())
        except Exception as e:
            print(f"Error extracting basic info: {str(e)}")

        # Extract sector
        sector = ""
        try:
            breadcrumb = soup.find("ol", class_="MuiBreadcrumbs-ol css-nhb8h9")
            if breadcrumb:
                breadcrumb_items = breadcrumb.find_all("li", class_="MuiBreadcrumbs-li")
                if len(breadcrumb_items) > 1:
                    sector = breadcrumb_items[1].text.strip()
        except Exception as e:
            print(f"Error extracting sector: {str(e)}")
        
        # Extract companies
        cell_companies = "Error"
        try:
            h2_comp = soup.find_all("h2")
            companies_list = []

            for h2 in h2_comp:
                header_text = " ".join(h2.stripped_strings).lower()
                if "top player" in header_text:
                    for sib in h2.find_next_siblings():
                        if sib.name != "ul":
                            break
                        for li in sib.find_all("li"):
                            text = li.get_text(strip=True)
                            if text and text != "&nbsp;":
                                companies_list.append(f"◦ {text}")
                    break  

            cell_companies = "\n".join(companies_list) if companies_list else "Error"
        except Exception as e:
            print(f"Error extracting companies: {e}")

        # Extract segments
        products = "Error"
        try:
            seg = soup.find("td", class_="fw-bold", string="Segments covered")
            segments_list = []
            
            if seg:
                next_td = seg.find_next_sibling()
                if next_td:
                    next_td_ul = next_td.find("ul")
                    if next_td_ul:
                        next_td_li = next_td_ul.find_all("li", recursive=False)
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
                        
            products = ", ".join(segments_list) if segments_list else "Error"
        except Exception as e:
            print(f"Error extracting segments for URL {url}: {str(e)}")
            products = "Error"

        image_url = None
        try:
            image_div = soup.find("div", class_="report-img")
            if image_div:
                img_tag = image_div.find("img")
                if img_tag and 'src' in img_tag.attrs:
                    image_url = img_tag['src']
        except Exception as e:
            print(f"Error extracting image URL: {str(e)}")

        # Extract market data
        data_2022 = data_2023 = data_2031 = currency = cagr_value = "N/A"
        
        try:
            first_para = soup.find("div", class_="report-details-description").find("p").text.strip()
            value_pattern = re.compile(r"USD (\d+\.?\d*)\s*(Billion|Million|Trillion|billion|million|trillion)")
            cagr_pattern = re.compile(r"CAGR of (\d+\.?\d*)\s*%")
            
            currency_values = value_pattern.findall(first_para)
            cagr = cagr_pattern.search(first_para)
            
            data_2022 = currency_values[0][0] if currency_values else "N/A"
            data_2023 = currency_values[1][0] if len(currency_values) > 1 else "N/A"
            data_2031 = currency_values[2][0] if len(currency_values) > 2 else "N/A"
            currency = "USD " + currency_values[0][1].title() if currency_values else "N/A"
            cagr_value = cagr.group(1) + "%" if cagr else "N/A"
        except Exception as e:
            print(f"Error extracting market data: {str(e)}")
        
        countries_list = [
            "USA", "Canada", "Germany", "Spain", "Italy", "France", "UK", 
            "China", "India", "Japan", "South Korea", "Brazil", "Mexico",
            "GCC Countries", "South Africa"
        ]
        formatted_countries = [f"◦ {country}" for country in countries_list]
        cell_countries = "\n".join(formatted_countries)
        
        if region == "Global":
            price_single = "5300"
            price_sitelesense = "6200"
            price_enterprise = "7100"
        else:
            price_single = "3500"
            price_sitelesense = "4400"
            price_enterprise = "5300"
        
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
        
    except TimeoutException:
        print(f"Timeout for URL: {url}")
        return None
    except WebDriverException as e:
        print(f"WebDriver error for URL {url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error processing URL {url}: {str(e)}")
        return None
    finally:
        pass