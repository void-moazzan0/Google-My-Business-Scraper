"""This script serves as an example on how to use Python
   & Playwright to scrape/extract data from Google Maps"""

from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import requests
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from     bs4 import BeautifulSoup, SoupStrainer
from tkinter import messagebox
import tkinter as tk
from threading import Thread

from tkinter import filedialog





session = requests.Session()

session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'})


def extract_emails(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    parse_only = SoupStrainer(['a', 'span', 'h1', 'h2', 'h3', 'p','div'])
    soup = BeautifulSoup(response.content, 'html.parser', parse_only=parse_only)

    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    emails = []

    for element in soup.select('a, span, h1, h2, h3, p, div'):
        emails.extend(EMAIL_REGEX.findall(element.text))

    return emails[0] if emails else 'None'

def get_links(url):

    response = session.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')
    links = set()
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            links.add(href)
    return links




@dataclass
class Business:
    """holds business data"""

    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    mail: str = None


@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """

    business_list: list[Business] = field(default_factory=list)

    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """
        self.dataframe().to_excel(f"{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file

        Args:
            filename (str): filename
        """
        self.dataframe().to_csv(f"{filename}.csv", index=False)

def update_progress_label(text):
    progress_label.config(text=text)
    root.update_idletasks()

def selenium_scraper(search_for, total):
    driver = webdriver.Chrome()  # Ensure you have the chromedriver executable in your PATH
    wait = WebDriverWait(driver, 10)

    driver.get(f"https://www.google.com/maps/search/{search_for.replace(' ', '+')}")

    # Implicit wait for the page to load
    time.sleep(5)  # You might want to use explicit waits instead for production code

    # scrolling
    scrollable_div = driver.find_element(By.XPATH, '//a[contains(@href, "https://www.google.com/maps/place")]')

    previously_counted = 0
    while True:
        # Scroll down
        for i in range(5):
            scrollable_div.send_keys(Keys.PAGE_DOWN)
        time.sleep(5)
        listings = driver.find_elements(By.CLASS_NAME, 'Nv2PK')
        if len(listings) >= total:
            listings = listings[:total]
            print(f"Total Scraped: {len(listings)}")
            break
        else:
            # Logic to break from loop to not run infinitely
            if len(listings) == previously_counted:
                print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                break
            else:
                previously_counted = len(listings)
                print(f"Currently Scraped: {len(listings)}")

    name_xpath = '//div[contains(@class, "fontHeadlineSmall")]'
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
    business_list = BusinessList()
    # Scraping
    rand_count=0
    for listing in listings:
        try:
            rand_count=rand_count+1
            listing.click()
            time.sleep(2)  # Waiting for the listing details to load

            business = Business()

            # Getting details using XPATH
            name_element = driver.find_element(By.CLASS_NAME, 'DUwDvf')
            business.name = name_element.text if name_element else "None"

            address_element = driver.find_element(By.XPATH, address_xpath)
            business.address = address_element.text if address_element else "None"

            web_element = listing.find_element(By.XPATH, website_xpath)
            business.website = web_element.text if web_element else "None"

            phone_element = driver.find_element(By.XPATH, phone_number_xpath)
            business.phone_number = phone_element.text if phone_element else "None"

            try:
                business.mail=extract_emails(f'https://{business.website}')
            except:
                business.mail='None'


            business_list.business_list.append(business)
            update_progress_label('Progress: '+str((rand_count/total)*100))
        except:
            print('error')
            continue

    # Save to files, these methods need to be implemented according to your needs
    business_list.save_to_excel("google_maps_data")
    business_list.save_to_csv("google_maps_data")

    driver.quit()


def open_file_browser():
    # Open the file browser at the user's home directory
    file_path = filedialog.askdirectory(initialdir='~', title='Select Folder')
    if file_path:
        # Here you can handle the file saving process using the file_path
        print(f'The file will be saved to: {file_path}')
    else:
        print('No file selected.')

    return file_path if file_path else './'


def start_scraping(search_for, total, scrape_button, quit_button):
    try:
        selenium_scraper(search_for,total)
        print(f"Scraping started with search_for: {search_for} and total: {total}")
        # Dummy wait time to simulate scraping
        browse_button.config(state=tk.NORMAL)
        root.after(5000, lambda: messagebox.showinfo("Complete", "Scraping complete!"))
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        # Re-enable the scrape and quit buttons after scraping is done or if an error occurs
        scrape_button.config(state=tk.NORMAL)
        quit_button.config(state=tk.NORMAL)

# Function to run the scraping in a separate thread
def scrape_thread(search_for, total, scrape_button, quit_button):
    scrape_button.config(state=tk.DISABLED)  # Disable the button to prevent multiple clicks

    thread = Thread(target=start_scraping, args=(search_for, total, scrape_button, quit_button))
    thread.start()


# Main GUI code
root = tk.Tk()
root.title("Google Maps Scraper")
root.geometry("500x500")

# Search term entry
tk.Label(root, text="Search for:").pack()
search_entry = tk.Entry(root)
search_entry.pack()

# Total results entry
tk.Label(root, text="Total results:").pack()
total_entry = tk.Entry(root)
total_entry.pack()

# Scrape button
scrape_button = tk.Button(root, text="Scrape", command=lambda: scrape_thread(search_entry.get(), int(total_entry.get()), scrape_button, quit_button))
scrape_button.pack()

progress_label = tk.Label(root, text="Progress: 0%")
progress_label.pack()
browse_button = tk.Button(root, text='Save File', command=open_file_browser,state=tk.DISABLED)
browse_button.pack()
# Quit button
quit_button = tk.Button(root, text="Quit", command=root.destroy)
quit_button.pack()

root.mainloop()