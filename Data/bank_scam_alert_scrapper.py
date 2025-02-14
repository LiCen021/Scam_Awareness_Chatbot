import requests
from bs4 import BeautifulSoup
import csv
import os

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

            # Extract contact details
            contact_details = []
            contact_list = section.find('ul')
            if contact_list:
                contact_details = [li.get_text(strip=True) for li in contact_list.find_all('li')]
            contact_details_str = ', '.join(contact_details)

            # Append the extracted information to the list with bank source
            scam_alerts.append([title, content, contact_details_str, "Macquarie Bank"])
    
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
            
            # Extract contact details if any
            contact_details_str = ''
            
            scam_alerts.append([title, content, contact_details_str, "CommBank"])
    
    return scam_alerts

def main():
    all_scam_alerts = []
    
    # Scrape Macquarie Bank
    print("Scraping Macquarie Bank alerts...")
    macquarie_alerts = scrape_macquarie()
    # Add IDs for Macquarie alerts
    macquarie_alerts = [[f"MAC_{str(i+1).zfill(4)}", *alert] for i, alert in enumerate(macquarie_alerts)]
    all_scam_alerts.extend(macquarie_alerts)
    print(f"Found {len(macquarie_alerts)} unique scam alerts from Macquarie Bank")
    
    # Scrape CommBank
    print("\nScraping CommBank alerts...")
    commbank_alerts = scrape_commbank()
    # Add IDs for CommBank alerts, continuing the numbering
    start_idx = len(macquarie_alerts)
    commbank_alerts = [[f"CBA_{str(i+1).zfill(4)}", *alert] for i, alert in enumerate(commbank_alerts)]
    all_scam_alerts.extend(commbank_alerts)
    print(f"Found {len(commbank_alerts)} unique scam alerts from CommBank")
    
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = os.path.join(current_dir, 'scam_alerts.csv')
    
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Intel_ID', 'Title', 'Content', 'Contact Details', 'Source'])
        writer.writerows(all_scam_alerts)
    
    print(f"\nTotal {len(all_scam_alerts)} scam alerts have been saved to '{csv_filename}'")

if __name__ == "__main__":
    main() 