import logging
import re
import unicodedata

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


def savefig(ax, plot_name, bbox_inches="tight", **kwargs):
    logging.info(f"writing: {plot_name}")
    default_kwargs = {}
    if bbox_inches is not None:
        default_kwargs["bbox_inches"] = bbox_inches

    try:
        ax.figure.savefig(plot_name, **default_kwargs, **kwargs)
    except AttributeError:
        ax.savefig(plot_name, **default_kwargs, **kwargs)
    plt.close()


def expand_dict_col(df, col):
    return pd.concat([df.drop([col], axis=1), df[col].apply(pd.Series)], axis=1)


df = pd.read_json('data/shapeyourcity.2024-03-23.jsonl', lines=True, dtype=False)
print(df)
print(df.columns)

questions_df = df.explode('qanda')


def parse_status(decision):
    for term in ['approved', 'refused', 'withdrawn', 'cancelled']:
        if re.search(r'\b' + term + r'\b', decision):
            return term
    if re.search(
        r'appeal was heard.*allowed.*overturning the decision.*permit was issued',
        decision,
        re.IGNORECASE,
    ):
        return 'approved on appeal'
    if re.search(r'this application not be referred to Public Hearing', decision, re.IGNORECASE):
        return 'not referred to public'

    logging.warning(f'failed to parse status from decision paragraph: {repr(decision)}')

    return ''


df['decision'] = df.decision.apply(lambda unicode_str: unicodedata.normalize("NFKD", unicode_str))
df['decision'] = df.decision.str.replace(r'\w+ \d\d?([a-z]{3})?, \d{4}', '<DATE>', regex=True)
df['decision'] = df.decision.str.replace(r'\w+ \d{4}', '<DATE>', regex=True)
df['status'] = df.decision.apply(parse_status)
print(df[['status', 'decision']].drop_duplicates())
for _, row in df[(df.status == '') & (df.decision != '')].iterrows():
    print(repr(row['decision']))


fig = sns.catplot(data=df, y='status', hue='type', kind='count')
savefig(fig, 'plots/status.png')
