import requests
from bs4 import BeautifulSoup
import csv
import os

# Wespac https://www.westpac.com.au/security/latest-scams/
# ANZ https://www.anz.com.au/security/latest-scams-australia/
# NAB https://www.nab.com.au/about-us/security/latest-fraud-scam-alerts
# Macquarie https://www.macquarie.com.au/security-and-fraud/scams/latest-scams-alerts.html
# CommBank https://www.commbank.com.au/support/security/latest-scams-and-security-alerts.html
# ScamWatch https://www.scamwatch.gov.au/about-us/news-and-alerts
# Moneysmart https://moneysmart.gov.au/check-and-report-scams/investor-alert-list

def scrape_macquarie():
    url = "https://www.macquarie.com.au/security-and-fraud/scams/latest-scams-alerts.html"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    scam_alerts = []
    seen_titles = set()

    # Locate all containers with the scam alerts
    containers = soup.find_all('div', class_='container-flex')
    print(f"Found {len(containers)} container-flex elements in Macquarie Bank")
    
    for container in containers:
        # Find all sections within each container
        sections = container.find_all('div', class_='richtext')
        for section in sections:
            # Extract the title
            title_tag = section.find('h3')
            title = title_tag.get_text(strip=True) if title_tag else 'No Title'
            
            # Skip if title doesn't contain a year (20XX or 19XX) or if we've seen this title before
            if not any(str(year) in title for year in range(1900, 2100)) or title in seen_titles:
                continue
                
            seen_titles.add(title)  # Add title to seen set

            # Extract the content paragraphs
            content_paragraphs = section.find_all('p')
            content = ' '.join(p.get_text(strip=True) for p in content_paragraphs)

            # Append the extracted information to the list with bank source
            scam_alerts.append([title, content, "Macquarie Bank"])
    
    return scam_alerts

def scrape_commbank():
    url = "https://www.commbank.com.au/support/security/latest-scams-and-security-alerts.html"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    scam_alerts = []
    seen_titles = set()

    # Find the main container with scam alerts
    main_container = soup.select_one('#latest > div > div:nth-child(2) > div > div > div.group-module > div > div')
    if main_container:
        # Find all sections with class 'column', 'column-control', 'fifty-split', or 'fifty-split-module'
        sections = main_container.find_all(class_=['column-module', 'column-control', 'fifty-split', 'fifty-split-module'])
        print(f"Found {len(sections)} sections in CommBank")
        
        for section in sections:
            # Find the header section containing the title (could be in header-section or directly as h2)
            header = section.find(class_='header-section')
            title_tag = header.find('h2') if header else section.find('h2')
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            
            # Skip if title doesn't contain a year or if we've seen this title before
            if not any(str(year) in title for year in range(1900, 2100)) or title in seen_titles:
                continue
                
            seen_titles.add(title)
            
            # Find the content section (could be in content-section or item class)
            content_section = section.find(class_=['content-section', 'item'])
            if not content_section:
                continue
                
            # Extract all paragraphs from the content
            paragraphs = content_section.find_all(['p', 'li','ul'])  # Include list items
            content = ' '.join(p.get_text(strip=True) for p in paragraphs)
            
            scam_alerts.append([title, content, "CommBank"])
    
    return scam_alerts

def scrape_westpac():
    url = "https://www.westpac.com.au/security/latest-scams/"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    scam_alerts = []
    seen_titles = set()

    # Find all column containers
    column_containers = soup.find_all('div', class_='column-container')
    print(f"Found {len(column_containers)} column containers in Westpac")
    
    for container in column_containers:
        # Find columns within this container - note the changed class
        columns = container.find_all('div', class_='col-xs-12 col-sm-8')
        
        for column in columns:
            current_alert = {}
            
            # Find the bodycopy div that contains the content
            bodycopy = column.find('div', class_='bodycopy')
            if not bodycopy:
                continue
                
            # Find title/date from h2
            title_tag = bodycopy.find('h2')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Check if title contains a date
                if any(str(year) in title_text for year in range(1900, 2100)):
                    if title_text not in seen_titles:
                        current_alert['title'] = title_text
                        seen_titles.add(title_text)
                    else:
                        continue
            
            # If we found a valid title, extract content
            if 'title' in current_alert:
                # Get all paragraphs
                paragraphs = bodycopy.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs)
                
                if content:
                    current_alert['content'] = content
                    
                    # Add to scam_alerts if we have both title and content
                    scam_alerts.append([
                        current_alert['title'],
                        current_alert['content'],
                        "Westpac"
                    ])
    
    return scam_alerts

def scrape_nab():
    url = "https://www.nab.com.au/about-us/security/latest-fraud-scam-alerts"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    scam_alerts = []
    seen_titles = set()

    # Find all column containers
    text_sections = soup.find_all('div', class_=lambda x: x and x.startswith('text parbase'))
    print(f"Found {len(text_sections)} column containers in NAB")
    
    for container in text_sections:
        # Find columns within this container - note the changed class
        columns = container.find_all('div', class_='nab-text')
 
        for column in columns:
            current_alert = {}
            # # Find the bodycopy div that contains the content
            # bodycopy = column.find('div', class_='bodycopy')
            # if not bodycopy:
            #     continue
            
            # Find title/date from h2
            title_tag = column.find('h3')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Check if title contains a date
                if any(str(year) in title_text for year in range(1900, 2100)):
                    if title_text not in seen_titles:
                        current_alert['title'] = title_text
                        seen_titles.add(title_text)
                    else:
                        continue
            
            # If we found a valid title, extract content
            if 'title' in current_alert:
                # Get all paragraphs
                paragraphs = column.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs)
                
                if content:
                    current_alert['content'] = content
                    
                    # Add to scam_alerts if we have both title and content
                    scam_alerts.append([
                        current_alert['title'],
                        current_alert['content'],
                        "NAB"
                    ])
    return scam_alerts


def main():
    all_scam_alerts = []
    
    # Scrape Macquarie Bank
    print("Scraping Macquarie Bank alerts...")
    macquarie_alerts = scrape_macquarie()
    macquarie_alerts = [[f"MAC_{str(i+1).zfill(4)}", *alert] for i, alert in enumerate(macquarie_alerts)]
    all_scam_alerts.extend(macquarie_alerts)
    print(f"Found {len(macquarie_alerts)} unique scam alerts from Macquarie Bank")
    
    # Scrape CommBank
    print("\nScraping CommBank alerts...")
    commbank_alerts = scrape_commbank()
    commbank_alerts = [[f"CBA_{str(i+1).zfill(4)}", *alert] for i, alert in enumerate(commbank_alerts)]
    all_scam_alerts.extend(commbank_alerts)
    print(f"Found {len(commbank_alerts)} unique scam alerts from CommBank")
    
    # Scrape Westpac
    print("\nScraping Westpac alerts...")
    westpac_alerts = scrape_westpac()
    westpac_alerts = [[f"WPC_{str(i+1).zfill(4)}", *alert] for i, alert in enumerate(westpac_alerts)]
    all_scam_alerts.extend(westpac_alerts)
    print(f"Found {len(westpac_alerts)} unique scam alerts from Westpac")
    
    # Scrape NAB
    print("\nScraping NAB alerts...")
    nab_alerts = scrape_nab()
    nab_alerts = [[f"NAB_{str(i+1).zfill(4)}", *alert] for i, alert in enumerate(nab_alerts)]
    all_scam_alerts.extend(nab_alerts)
    print(f"Found {len(nab_alerts)} unique scam alerts from NAB")
    
    # Save to CSV
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = os.path.join(current_dir, 'scam_alerts.csv')
    
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Intel_ID', 'Title', 'Content', 'Source'])
        writer.writerows(all_scam_alerts)
    
    print(f"\nTotal {len(all_scam_alerts)} scam alerts have been saved to '{csv_filename}'")

if __name__ == "__main__":
    main() 