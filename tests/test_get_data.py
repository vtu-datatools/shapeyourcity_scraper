import pytest

from shapeyourcity.get_data import process_rezoning_page


@pytest.mark.parametrize(
    'url,decision',
    [
        (
            'https://www.shapeyourcity.ca/1648-woodland-dr',
            'The Director of Planning has requested you be advised this development application was withdrawn by the applicant on March 15, 2024.',
        ),
        ('https://www.shapeyourcity.ca/215-229-e-13-ave', ''),
    ],
)
def test_process_rezoning_page_decision(url, decision):
    details, _ = process_rezoning_page(url)
    assert details['decision'] == decision


@pytest.mark.parametrize(
    'url,names',
    [
        (
            'https://www.shapeyourcity.ca/1245-1265-w-10-ave?tool=qanda',
            {'Daniel Silver', 'Robert White'},
        ),
    ],
)
def test_process_rezoning_page_contacts(url, names):
    details, _ = process_rezoning_page(url)

    found_names = {c['name'] for c in details['contacts']}
    assert names == found_names
