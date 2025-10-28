"""Parser for BattleScribe HTML exports (lightweight).

Extracts unit summaries (name, models, wounds per model, attacks, to-hit,
to-wound, save) from a BattleScribe-generated HTML file like
`Current Stormcasts.html`.

This module requires BeautifulSoup (bs4).
"""

import re
from typing import List

from bs4 import BeautifulSoup


def _int_or_none(s: str):
    if s is None:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def parse_battlescribe_html(path: str):
    """Parse the Battlescribe HTML file and return a list of unit dicts.

    Each dict contains: name, models, wounds_per_model, attacks, to_hit,
    to_wound, save.
    """
    with open(path, 'r', encoding='utf-8') as f:
        doc = f.read()

    soup = BeautifulSoup(doc, 'html.parser')

    units = []

    # Find all unit containers: li elements with class 'rootselection'
    for li in soup.find_all('li', class_='rootselection'):
        h4 = li.find('h4')
        if not h4:
            continue
        name = h4.get_text(strip=True)

        # Skip non-unit blocks like Allegiance, Game Type, Grand Strategy
        skip_names = {'allegiance', 'game type', 'grand strategy'}
        if name.strip().lower() in skip_names:
            continue

        # Look for the selections paragraph to find model counts
        selections_p = None
        for p in li.find_all('p'):
            if p.get_text().strip().startswith('Selections:'):
                selections_p = p.get_text()
                break

        models = 1
        if selections_p:
            # look for e.g., '5 Liberators [100pts]'
            m = re.search(r"(\d+)\s+[A-Za-z'\-]+", selections_p)
            if m:
                models = int(m.group(1))

        # Find the first stats table after this li that contains 'Unit' header
        wounds_per_model = 1
        save = 6
        stats_table = li.find('table')
        if stats_table:
            # search for a row that has Wounds and Save columns
            # find header row text
            hdrs = [th.get_text(strip=True) for th in stats_table.find_all('th')]
            if 'Wounds' in hdrs and 'Save' in hdrs:
                # find the first data row
                tr = stats_table.find('tr')
                # find subsequent tr containing numeric stats (skip header)
                trs = stats_table.find_all('tr')
                if len(trs) >= 2:
                    data_tr = trs[1]
                    tds = [td.get_text(strip=True) for td in data_tr.find_all('td')]
                    # Expect Move, Wounds, Bravery, Save
                    # find Wounds and Save by header index
                    try:
                        w_idx = hdrs.index('Wounds')
                        s_idx = hdrs.index('Save')
                        wounds_per_model = _int_or_none(tds[w_idx]) or wounds_per_model
                        save_text = tds[s_idx]
                        save = _int_or_none(save_text) or save
                    except Exception:
                        pass

        # Weapons: parse all tables that include a Weapon header and gather
        # weapon profiles. We will return a list of weapon dicts. If none
        # found, fall back to basic attacks/to_hit/to_wound defaults.
        weapons = []
        for tbl in li.find_all('table'):
            hdrs = [th.get_text(strip=True) for th in tbl.find_all('th')]
            if 'Weapon' in hdrs and 'Attacks' in hdrs:
                # collect weapon rows
                rows = tbl.find_all('tr')
                # skip header row(s)
                for data_tr in rows[1:]:
                    tds = [td.get_text(strip=True) for td in data_tr.find_all('td')]
                    # map headers to columns
                    weapon = {}
                    try:
                        weapon['title'] = tds[0] if len(tds) > 0 else ''
                    except Exception:
                        weapon['title'] = ''
                    # helper to extract value by header name
                    def col_val(name):
                        try:
                            idx = hdrs.index(name)
                            return tds[idx]
                        except Exception:
                            return ''

                    # Attacks, To Hit, To Wound, Rend, Damage
                    weapon['attacks'] = _int_or_none(col_val('Attacks')) or 1
                    weapon['to_hit'] = _int_or_none(col_val('To Hit')) or 4
                    weapon['to_wound'] = _int_or_none(col_val('To Wound')) or 4
                    # Rend may be like '-1'
                    rend_text = col_val('Rend')
                    if rend_text:
                        m = re.search(r"(-?\d+)", rend_text)
                        weapon['rend'] = int(m.group(1)) if m else 0
                    else:
                        weapon['rend'] = 0

                    dmg_text = col_val('Damage')
                    # Normalize damage: numeric or D3/D6 etc.
                    if dmg_text:
                        dmg_text = dmg_text.strip()
                        # if form D3 or D6
                        m = re.match(r"D(\d+)", dmg_text, flags=re.I)
                        if m:
                            weapon['damage'] = {'type': 'D', 'sides': int(m.group(1))}
                        else:
                            # try integer
                            m2 = re.search(r"(\d+)", dmg_text)
                            weapon['damage'] = int(m2.group(1)) if m2 else 1
                    else:
                        weapon['damage'] = 1

                    weapons.append(weapon)

        # fall back to simple weapon if none found
        attacks = 1
        to_hit = 4
        to_wound = 4
        if weapons:
            first = weapons[0]
            attacks = first.get('attacks', attacks)
            to_hit = first.get('to_hit', to_hit)
            to_wound = first.get('to_wound', to_wound)

        units.append({
            'name': name,
            'models': models,
            'wounds_per_model': wounds_per_model,
            'attacks': attacks,
            'to_hit': to_hit,
            'to_wound': to_wound,
            'save': save,
            'weapons': weapons,
        })

    return units
