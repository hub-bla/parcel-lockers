from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys


from collections import deque
import re
import pandas as pd



class ParcelLockersScarper:


    def __init__(self, starting_postcode="60-001"):
        chrome_options = Options()
        chrome_options.add_argument("--disable-notifications")
        # chrome_options.add_argument("--headless=new") # for Chrome >= 109
        self.base_url = 'https://inpost.pl/znajdz-paczkomat'
        self.browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        self.starting_postcode = starting_postcode


    def launch_and_prepare(self):

        self.browser.get(self.base_url)

        # accept cookies
        try:
            WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.ID , f"onetrust-accept-btn-handler"))
                )
            self.browser.find_element(By.ID , f"onetrust-accept-btn-handler").click()
        except:
            print("Getting url error")

        self.browser.find_element(By.CSS_SELECTOR, f"[data-filter-value=\"1\"]").click() # pick parcel lockers category

        self.searchbar = self.browser.find_element(By.CLASS_NAME, "tt-input")# get searchbar

        self.searchbar.click()


    def get_parcel_lockers(self):

        lockers_dict = {}

        self.searchbar.send_keys(self.starting_postcode)
        
        visited = set()
        to_visit = deque()

        menu = self.browser.find_element(By.CLASS_NAME, "tt-menu")

        WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME , f"pl-0"))
                )
        

        def preprocess(containers):
            
            for container in containers:
                location = container.find_element(By.CLASS_NAME, "goToLocatorTrigger")
                locker_name = container.find_element(By.CLASS_NAME, "text")
                locker_html = locker_name.get_attribute("innerHTML")

                code_re = r'\b(6[012]-)'
                re_id = r'\<\/span\>([A-Z0-9]+)\<span'
                re_adress = r'\<b\>(.*?)\<\/b\>'
                re_description = r'\<br\>(.*)'

                try:
                    locker_id = re.findall(re_id, locker_html)[0]
                    address = re.findall(re_adress, locker_html)[0]
                    description = re.findall(re_description, locker_html)[0]
                    correct_code = re.findall(code_re, address)
                except:
                    print("regex operations went wrong")
                    return None
                
                longitude, latitude = location.get_attribute("data-lng"), location.get_attribute("data-lat")

                if locker_id in visited or not correct_code:
                    continue

                if locker_id not in lockers_dict:
                     lockers_dict[locker_id] = {
                        "address": address,
                        "description": description,
                        "longitude": longitude,
                        "latitude": latitude
                    }
                     
                if locker_id not in to_visit:
                   
                    to_visit.append(locker_id)
                    print(f"LNG: {longitude}, LAT: {latitude}, ID: {locker_id}, ADDRES: {address}")


        menu.find_element(By.CLASS_NAME, "pl-0").click() # pick first location

        WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME , f"locatorsListContainer"))
                )
        
        list_lockers_container = self.browser.find_element(By.CLASS_NAME, "locatorsListContainer")

        locker_conatiners = list_lockers_container.find_elements(By.CLASS_NAME, "locatorContainer")
        
        preprocess(locker_conatiners)
        
        #bfs-like traversing
        while to_visit:
            locker_id = to_visit.popleft()
            visited.add(locker_id)
            self.searchbar.click()
            self.searchbar.send_keys(Keys.CONTROL + "a")  # clear searchbar
            self.searchbar.send_keys(Keys.DELETE)       # clear searchbar
            self.searchbar.send_keys(locker_id)
            print(locker_id)
            WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME , f"pl-0"))  
                )
            
            menu.find_element(By.CLASS_NAME, "pl-0").click() # pick first location

            WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME , f"locatorsListContainer"))
                )
            
            list_lockers_container = self.browser.find_element(By.CLASS_NAME, "locatorsListContainer")

            locker_conatiners = list_lockers_container.find_elements(By.CLASS_NAME, "locatorContainer")
            
            preprocess(locker_conatiners)


        return lockers_dict


if __name__ == '__main__':
    scraper = ParcelLockersScarper()

    scraper.launch_and_prepare()
    lockers = scraper.get_parcel_lockers()
    df = pd.concat({k: pd.DataFrame([v]) for k, v in lockers.items()}, axis=0)
    df = df.reset_index(level=1, drop=True)
    df.index.rename("id", inplace=True)
    df.to_csv("lockers_data.csv")