import datetime
import json
import os
import time

import numpy as np
import pandas as pd
import requests
import requests_cache
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

requests_cache.install_cache('.requests_cache', expire_adter=60 * 60 * 24)

SLEEP_TIME = 10


def remove_tags(soup) -> str:
    # https://www.geeksforgeeks.org/remove-all-style-scripts-and-html-tags-using-beautifulsoup/
    for data in soup(['style', 'script', 'meta', 'link']):
        # Remove tags
        data.decompose()

    # return data by retrieving the tag content
    return soup.prettify()


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, set):
            return list(obj)
        try:
            if np.isnan(obj) or obj is None:
                return None
        except TypeError:
            pass
        try:
            return obj.to_json()
        except AttributeError:
            pass
        return super(NpEncoder, self).default(obj)


def dump_records(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(pd.notnull(df), None)
    records = df.to_dict('records')
    return records


def dump_jsonl(df, filename: str):
    """
    pandas does some weird escaping if you use its built-in method
    """
    records = dump_records(df)
    print(f'writing: {filename}')
    with open(filename, 'w') as fh:
        for record in records:
            try:
                fh.write(json.dumps(record, sort_keys=True, cls=NpEncoder) + '\n')
            except TypeError as err:
                print(f'failed to JSON serialize the following record: {record}')
                raise err


def get_page_source(driver, url: str, **kwargs) -> str:
    driver.get(url, **kwargs)
    time.sleep(SLEEP_TIME)
    return driver.page_source


def process_links(driver, url):
    html = get_page_source(driver, url)
    next_button = 'button.ehq-paginationNextButton'  # keep going till not disabled
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    iframes = list(soup.select('iframe'))
    iframes = [iframe for iframe in iframes if 'shapeyourcity' in iframe.attrs.get('src', '')]
    assert len(iframes) == 1
    rezoning_iframe = iframes[0]
    html = get_page_source(driver, rezoning_iframe.attrs['src'])
    links = []

    for page_index in range(100):  # max 100 iterations
        soup = BeautifulSoup(html, 'html.parser')

        links = [a.attrs['href'] for a in soup.select('a.ehq-projectCoverImg')]
        yield links
        button = soup.select(next_button)[0]
        print(f'getting: {url}?page=({page_index + 1})')
        driver.find_element(By.CSS_SELECTOR, next_button).click()
        time.sleep(SLEEP_TIME)
        html = driver.page_source
        if 'disabled' in button.attrs:
            break


def parse_key_dates(li_elem) -> tuple[str, str]:
    title = li_elem.select('.key-date-title')[0].text
    value = li_elem.select('.key-date-date')[0].text
    return title.strip(), value.strip()


def parse_contact_details(elem) -> dict[str, str]:
    name = elem.select('.member-info .member-name')[0].text
    role = elem.select('.member-info .member-designation')[0].text
    affiliation = elem.select('.member-info .member-designation')[0].next_sibling.text

    return {'name': name.strip(), 'role': role.strip(), 'affiliation': affiliation.strip()}


def parse_qanda(elem) -> dict[str, str]:
    question = elem.select('.question .q')[0].text
    meta = elem.select('.question .meta')[0].text
    if 'asked' not in meta:
        username = ''
        timestamp = meta
    else:
        username, timestamp = meta.split('asked')
    answer = elem.select('.qanda-answer .answer')[0].text
    return {
        'question': question.strip(),
        'username': username.strip(),
        'timestamp': timestamp.strip(),
        'answer': answer.strip(),
    }


def process_rezoning_page(url: str) -> tuple[dict, str]:
    # html = get_page_source(driver, f'{url}?tool=qanda')
    print(f'get: {url}?tool=qanda')
    html = requests.get(url, params={'tool': 'qanda'}).text
    with open('temp.html', 'w') as fh:
        fh.write(html)
    soup = BeautifulSoup(html, 'html.parser')
    dates = {}
    for elem in soup.select('.widget_key_date ul.widget-list li'):
        title, date = parse_key_dates(elem)
        dates[title] = date

    decision = ''
    if soup.select('#project_description_text > p'):
        paragraphs = [
            p.text.strip() for p in soup.select('#project_description_text > p') if p.text.strip()
        ]
        if paragraphs:
            decision = paragraphs[0]

    description = soup.select('.full-description')[0].text.strip()

    contacts = []
    for elem in soup.select('.widget_project_team'):
        contacts.append(parse_contact_details(elem))

    q_and_a = []
    for elem in soup.select('.qanda-list > ul > li'):
        q_and_a.append(parse_qanda(elem))
    return dict(
        description=description,
        qanda=q_and_a,
        contacts=contacts,
        dates=dates,
        decision=decision,
        url=url,
    ), remove_tags(soup)


if __name__ == '__main__':
    # instance of Options class allows
    # us to configure Headless Chrome
    options = Options()

    # this parameter tells Chrome that
    # it should be run without UI (Headless)
    # options.add_argument('--headless=new')

    # spoof options to avoid ssl errors from airbnb
    # options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36")
    # options.add_argument("--window-size=1920x1080")

    # initializing webdriver for Chrome with our options
    driver = webdriver.Chrome(options=options)
    access_date = datetime.datetime.today().strftime('%Y-%m-%d')

    pages = {}
    rows = []
    try:
        for page_links in process_links(driver, 'https://www.shapeyourcity.ca/rezoning'):
            for page in page_links:
                row, page_source = process_rezoning_page(page)
                pages[page] = page_source
                row['type'] = 'rezoning'
                rows.append(row)

        for page_links in process_links(driver, 'https://www.shapeyourcity.ca/development'):
            for page in page_links:
                row, page_source = process_rezoning_page(page)
                pages[page] = page_source
                row['type'] = 'development'
                rows.append(row)
    finally:
        driver.close()
    df = pd.DataFrame.from_records(rows)
    df['access_date'] = access_date
    dump_jsonl(df, f'data/shapeyourcity.{access_date}.jsonl')

    print(f'writing: data/pages/{access_date}.json')
    with open(f'data/pages/{access_date}.json', 'w') as fh:
        json.dump(pages, fh)
