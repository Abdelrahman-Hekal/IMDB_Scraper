from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
import pandas as pd
import time
import sys
import numpy as np
import re
import warnings
warnings.filterwarnings('ignore')

def set_driver_options(headless):

    # Setting up chrome driver for the bot
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--start-maximized")
    if headless:
        chrome_options.add_argument('--headless=new')
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.page_load_strategy = 'normal'

    return chrome_options

def initialize_bot(headless):

    # Setting up chrome driver for the bot
    chrome_options = set_driver_options(headless)

    try:
        driver = uc.Chrome(options=chrome_options) 
    except:
        # Setting up chrome driver for the bot
        options = set_driver_options(headless)
        # installing the chrome driver
        chrome_service = ChromeService()
        # configuring the driver
        driver = webdriver.Chrome(options=options, service=chrome_service)
        ver = int(driver.capabilities['chrome']['chromedriverVersion'].split('.')[0])
        driver.quit()

        undetected = False
        try:
            driver = uc.Chrome(version_main = ver, options=chrome_options) 
            undetected = True
        except:
            try:
                print('Failed to locate the Chrome driver online, searching for the driver locally in: C:\Chromedriver')
                chrome_options = set_driver_options()
                chrome_options.add_argument('--disable-dev-shm-usage') 
                driver = uc.Chrome(driver_executable_path="C:\\Chromedriver\\chromedriver.exe", options=chrome_options) 
                undetected = True
            except Exception as err:
                pass

        if not undetected:
            print('Failed to initialize undetected-chromedriver, using the basic driver version instead')
            chrome_options = set_driver_options()
            driver = webdriver.Chrome(options=chrome_options, service=chrome_service) 

    driver.set_window_size(1920, 1080)
    driver.maximize_window()
    driver.set_page_load_timeout(120)

    return driver


def search_IMDB(path):

    start = time.time()
    print('-'*75)
    print('Searching IMDB ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot(False)
    headless = False

    # initializing the dataframe
    data = pd.DataFrame()

    # for running the scraper through parallel batches
    if path != '':
        df = pd.read_excel(path)
        filename =  'IMDB_Search'+ path[-7:-5] + '.xlsx'
    else:
        df = pd.read_excel('Titles.xlsx')
        filename = 'IMDB_Search.xlsx'

    # resuming feature
    scraped = []
    try:
        data = pd.read_excel(filename)
        scraped = data['Title'].values.tolist()
    except:
        pass

    df['Title'] = df['Title'].astype(str)
    df['Title'] = df['Title'].str.replace('nan', '')
    n = len(df['Title'])
    for i, title in enumerate(df['Title']):
        exported = False
        print(f'Searching Title {i+1}\{n}')
        try:
            if title in scraped: continue
            #for _ in range(3):
            try:
                url = f'https://www.imdb.com/search/title/?title={title}&title_type=feature,tv_series,short,tv_episode,tv_miniseries,tv_movie,tv_special,video_game,tv_short,video,music_video,podcast_series'
                driver.get(url) 
                time.sleep(3)
                #break
            except:
                
                #driver = initialize_bot(headless)
                #if headless:
                #    headless = False
                #else:
                #    headless = True           
                print(f'No search results for title: {title}')
                driver.quit()
                sys.exit()

            # scrolling across the page 
            try:
                total_height = driver.execute_script("return document.body.scrollHeight")
                height = total_height/10
                new_height = 0
                for _ in range(10):
                    prev_hight = new_height
                    new_height += height             
                    driver.execute_script(f"window.scrollTo({prev_hight}, {new_height})")
                    time.sleep(0.1)
            except:
                pass
  
            results = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[class='ipc-metadata-list-summary-item']")))

            for j, res in enumerate(results):
                print(f'Scraping result {j+1}')
                row = {}
                row['Title'] = title
                try:
                    # title and title link
                    title_link, name = '', ''              
                    try:
                        a = wait(res, 0.01).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[class='ipc-title-link-wrapper']")))
                        text = a.get_attribute('textContent')
                        if text.count('.') == 1:
                            name = text.split('.')[-1].strip()
                        elif text.count('.') > 1:
                            name = text[text.index('.'):].strip()
                        else:
                            name = text.strip()

                        title_link = a.get_attribute('href')
                    except:
                        continue
              
                    row['IMDB_Title'] = name
                    row['IMDB_Link'] = title_link   
                    
                    # category
                    cat = 'Movie'
                    try:
                        cat = wait(res, 0.01).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[class*='title-type']"))).get_attribute('textContent').replace('\n', '').strip()
                    except:
                        pass

                    row['Category'] = cat  

                    # rating
                    rating = ''
                    try:
                        rating = wait(res, 0.01).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[class*='imdb-rating']"))).text.split('\n')[0].strip()
                    except:
                        pass

                    row['IMDB_Rating'] = rating

                    # number of ratings
                    nratings = ''
                    try:
                         nratings = wait(res, 0.01).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class='sc-21df249b-0 jmcDPS']"))).get_attribute('textContent').replace('\n', '').replace('Votes', '').replace(',', '')
                    except:
                        pass

                    row['#Ratings'] = nratings                    

                    # other info
                    date, duration, parental = '', '', ''
                    try:
                        div = wait(res, 0.01).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='title-metadata']")))
                        spans = wait(div, 0.01).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span[class='sc-479faa3c-8 bNrEFi dli-title-metadata-item']")))
                        for span in spans:
                            text = span.text
                            try:
                                text = int(text.split('–')[0])
                                if text > 1800 and not date:
                                    date = text
                                    continue
                            except:
                                pass

                            if ('h' in text or 'm' in text) and not duration:
                                duration = text
                                continue

                            if len(spans) > 1:
                                parental = text
                    except:
                        pass

                    row['Release_Date'] = date
                    row['Duration'] = duration
                    row['Parental_Guide'] = parental
                 
                    # appending the output to the datafame        
                    data = pd.concat([data, pd.DataFrame([row.copy()])], ignore_index=True)
                    exported = True
                except:
                    pass

            # saving data to csv file each 100 links
            if np.mod(i+1, 20) == 0:
                print('Outputting scraped data ...')
                writer = pd.ExcelWriter(filename, engine_kwargs={'options':{'strings_to_urls': False}})
                data.to_excel(writer, index=False)
                writer.close()
            if not exported:
                data = pd.concat([data, pd.DataFrame([row.copy()])], ignore_index=True)
        except:
            pass

    writer = pd.ExcelWriter(filename, engine_kwargs={'options':{'strings_to_urls': False}})
    data.to_excel(writer, index=False)
    writer.close()
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'IMDB searching process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":

    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = search_IMDB(path)

