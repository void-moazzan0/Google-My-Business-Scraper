"""This script serves as an example on how to use Python
   & Playwright to scrape/extract data from Google Maps"""

from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import requests
import re
import time

from bs4 import BeautifulSoup, SoupStrainer
from tkinter import messagebox
import tkinter as tk
from threading import Thread




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

def scraper(search_for, total):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"https://www.google.com/maps/search/{search_for.replace(' ','+')}", timeout=60000)
        # wait is added for dev phase. can remove it in production



        # scrolling
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

        # this variable is used to detect if the bot
        # scraped the same number of listings in the previous iteration
        previously_counted = 0
        while True:
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(5000)

            if (
                page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).count()
                >= total
            ):
                listings = page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                print(f"Total Scraped: {len(listings)}")
                break
            else:
                # logic to break from loop to not run infinitely
                # in case arrived at all available listings
                if (
                    page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    == previously_counted
                ):
                    listings = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()
                    print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                    break
                else:
                    previously_counted = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    print(
                        f"Currently Scraped: ",
                        page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count(),
                    )

        business_list = BusinessList()
        rand_count=0
        # scraping
        for listing in listings:
            listing.click()
            page.wait_for_timeout(2000)

            name_xpath = '//div[contains(@class, "fontHeadlineSmall")]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            reviews_span_xpath = '//span[@role="img"]'

            business = Business()

            if listing.locator(name_xpath).count() > 0:
                business.name = listing.locator(name_xpath).inner_text()
            else:
                business.name = "None"
            if page.locator(address_xpath).count() > 0:
                business.address = page.locator(address_xpath).inner_text()
            else:
                business.address = "None"
            if page.locator(website_xpath).count() > 0:
                business.website = page.locator(website_xpath).inner_text()

                try:
                    business.mail=extract_emails(f'https://{business.website}')
                except:
                    business.mail='None'
            else:
                business.website = "None"
            if page.locator(phone_number_xpath).count() > 0:
                business.phone_number = page.locator(phone_number_xpath).inner_text()
            else:
                business.phone_number = "None"
            if listing.locator(reviews_span_xpath).count() > 0:
                business.reviews_average = 1
                business.reviews_count = 1
            else:
                business.reviews_average = ""
                business.reviews_count = ""

            business_list.business_list.append(business)
            update_progress_label(str(rand_count))
            rand_count=rand_count+1
        # saving to both excel and csv just to showcase the features.
        business_list.save_to_excel("google_maps_data")
        business_list.save_to_csv("google_maps_data")

        browser.close()


def start_scraping(search_for, total, scrape_button, quit_button):
    try:
        scraper(search_for,total)
        print(f"Scraping started with search_for: {search_for} and total: {total}")
        # Dummy wait time to simulate scraping
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
# Quit button
quit_button = tk.Button(root, text="Quit", command=root.destroy)
quit_button.pack()

root.mainloop()