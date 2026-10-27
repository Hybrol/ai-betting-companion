import re
import unicodedata
from difflib import SequenceMatcher

CANONICAL_TEAMS = {
    # Liga Portugal
    "sl benfica": "SL Benfica",
    "benfica": "SL Benfica",
    "sporting cp": "Sporting CP",
    "sporting": "Sporting CP",
    "sporting lisbon": "Sporting CP",
    "fc porto": "FC Porto",
    "porto": "FC Porto",
    "sc braga": "SC Braga",
    "braga": "SC Braga",
    "sp. braga": "SC Braga",
    "sp braga": "SC Braga",
    "vitoria sc": "Vitória SC",
    "vitoria de guimaraes": "Vitória SC",
    "vitoria guimaraes": "Vitória SC",
    "santa clara": "Santa Clara",
    "cd santa clara": "Santa Clara",
    "casa pia": "Casa Pia AC",
    "casa pia ac": "Casa Pia AC",
    "famalicao": "FC Famalicão",
    "fc famalicao": "FC Famalicão",
    "rio ave": "Rio Ave FC",
    "rio ave fc": "Rio Ave FC",
    "boavista": "Boavista FC",
    "boavista fc": "Boavista FC",
    "estoril": "GD Estoril Praia",
    "estoril praia": "GD Estoril Praia",
    "gd estoril praia": "GD Estoril Praia",
    "moreirense": "Moreirense FC",
    "moreirense fc": "Moreirense FC",
    "gil vicente": "Gil Vicente FC",
    "gil vicente fc": "Gil Vicente FC",
    "arouca": "FC Arouca",
    "fc arouca": "FC Arouca",
    "nacional": "CD Nacional",
    "cd nacional": "CD Nacional",
    "nacional da madeira": "CD Nacional",
    "avs": "AVS Futebol SAD",
    "avs futebol": "AVS Futebol SAD",
    "farense": "SC Farense",
    "sc farense": "SC Farense",
    "estrela da amadora": "CF Estrela Amadora",
    "estrela amadora": "CF Estrela Amadora",

    # Premier League
    "arsenal": "Arsenal",
    "aston villa": "Aston Villa",
    "chelsea": "Chelsea",
    "liverpool": "Liverpool",
    "manchester city": "Manchester City",
    "man city": "Manchester City",
    "manchester united": "Manchester United",
    "man utd": "Manchester United",
    "newcastle": "Newcastle United",
    "newcastle utd": "Newcastle United",
    "tottenham": "Tottenham Hotspur",
    "tottenham hotspur": "Tottenham Hotspur",

    # La Liga
    "real madrid": "Real Madrid",
    "barcelona": "FC Barcelona",
    "fc barcelona": "FC Barcelona",
    "atletico madrid": "Atlético Madrid",
    "atletico de madrid": "Atlético Madrid",
    "sevilha": "Sevilla FC",
    "sevilla": "Sevilla FC",
    "sevilla fc": "Sevilla FC",
    "osasuna": "CA Osasuna",
    "ca osasuna": "CA Osasuna",
    "villarreal": "Villarreal CF",
    "espanhol": "RCD Espanyol",
    "espanyol": "RCD Espanyol",

    # Brasileirão
    "flamengo": "Flamengo",
    "flamengo rj": "Flamengo",
    "atletico-mg": "Atlético Mineiro",
    "atletico mg": "Atlético Mineiro",
    "atletico mineiro": "Atlético Mineiro",
    "atletico-pr": "Athletico Paranaense",
    "atletico pr": "Athletico Paranaense",
    "coritiba": "Coritiba",
    "coritiba pr": "Coritiba",
    "gremio": "Grêmio",
    "gremio rs": "Grêmio",
    "palmeiras": "Palmeiras",
    "sao paulo": "São Paulo",
    "corinthians": "Corinthians",
    "botafogo": "Botafogo",
    "fluminense": "Fluminense",
    "vasco": "Vasco da Gama",
    "cruzeiro": "Cruzeiro",
    "internacional": "Internacional",

    # Serie A (Italy)
    "como": "Como 1907",
    "como 1907": "Como 1907",
    "torino": "Torino FC",
    "torino fc": "Torino FC",
    "as roma": "AS Roma",
    "roma": "AS Roma",
    "cagliari": "Cagliari Calcio",
    "cagliari calcio": "Cagliari Calcio",
    "juventus": "Juventus",
    "inter": "Inter Milan",
    "inter milan": "Inter Milan",
    "internazionale": "Inter Milan",
    "milan": "AC Milan",
    "ac milan": "AC Milan",
    "napoli": "SSC Napoli",
    "ssc napoli": "SSC Napoli",
    "lazio": "SS Lazio",
    "ss lazio": "SS Lazio",
    "atalanta": "Atalanta BC",
    "fiorentina": "ACF Fiorentina",
    "bologna": "Bologna FC",
    "bologna fc": "Bologna FC",
    "monza": "AC Monza",
    "parma": "Parma Calcio",
    "hellas verona": "Hellas Verona",
    "verona": "Hellas Verona",
    "empoli": "Empoli FC",
    "venezia": "Venezia FC",
    "udinese": "Udinese Calcio",
    "lecce": "US Lecce",
    "genoa": "Genoa CFC",

    # Bundesliga (Germany)
    "bayern munich": "Bayern Munich",
    "bayern": "Bayern Munich",
    "bayern munchen": "Bayern Munich",
    "borussia dortmund": "Borussia Dortmund",
    "dortmund": "Borussia Dortmund",
    "bayer leverkusen": "Bayer Leverkusen",
    "leverkusen": "Bayer Leverkusen",
    "rb leipzig": "RB Leipzig",
    "leipzig": "RB Leipzig",
    "eintracht frankfurt": "Eintracht Frankfurt",
    "frankfurt": "Eintracht Frankfurt",
    "vfb stuttgart": "VfB Stuttgart",
    "stuttgart": "VfB Stuttgart",
    "wolfsburg": "VfL Wolfsburg",
    "hoffenheim": "TSG Hoffenheim",
    "werder bremen": "Werder Bremen",
    "bremen": "Werder Bremen",

    # Ligue 1 (France)
    "paris saint-germain": "PSG",
    "psg": "PSG",
    "marseille": "Marseille",
    "olympique marseille": "Marseille",
    "lyon": "Lyon",
    "olympique lyonnais": "Lyon",
    "monaco": "AS Monaco",
    "as monaco": "AS Monaco",
    "lille": "Lille",
    "losc lille": "Lille",
    "nice": "OGC Nice",
    "lens": "RC Lens",

    # Saudi Pro League
    "al hilal": "Al-Hilal",
    "al-hilal": "Al-Hilal",
    "al nassr": "Al-Nassr",
    "al-nassr": "Al-Nassr",
    "al ittihad": "Al-Ittihad",
    "al-ittihad": "Al-Ittihad",
    "al ahli": "Al-Ahli",
    "al-ahli": "Al-Ahli",
    "al ettifaq": "Al-Ettifaq",
    "al-ettifaq": "Al-Ettifaq",
    "al shabab": "Al-Shabab",
    "al-shabab": "Al-Shabab",
}

def clean_string(s: str) -> str:
    s = s.lower().strip()
    # Normalize unicode accents
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    # Remove common prefixes/suffixes & club types
    s = re.sub(r'\b(fc|cf|cd|sc|ac|sad|gd|sl|rcd|ca|rj|rs|pr|mg|sp|vfl|vfb|tsg|ogc|rc|afc|bsc|ssc|calcio|us|ss|as)\b', '', s)
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def get_canonical_stem(name: str) -> str:
    """
    Returns a unified canonical stem for deduplication and matching.
    Strips founding years (e.g. 1907, 1899, 1904), club prefixes, extra whitespace,
    and resolves canonical mappings.
    """
    canonical = normalize_team_name(name)
    cleaned = clean_string(canonical)
    # Strip founding years / 2-4 digit suffixes (e.g. 1907, 1899, 1904, 04, 96)
    stem = re.sub(r'\b(18\d{2}|19\d{2}|20\d{2}|\d{2,4})\b', '', cleaned).strip()
    stem = re.sub(r'\s+', ' ', stem).strip()
    return stem if stem else cleaned

def normalize_team_name(name: str) -> str:
    cleaned = clean_string(name)
    
    # Check exact dictionary match
    raw_lower = name.lower().strip()
    if raw_lower in CANONICAL_TEAMS:
        return CANONICAL_TEAMS[raw_lower]
    if cleaned in CANONICAL_TEAMS:
        return CANONICAL_TEAMS[cleaned]
        
    # Check partial / fuzzy matching against canonical names
    best_match = name.strip()
    best_score = 0.0
    for key, canonical in CANONICAL_TEAMS.items():
        sim = SequenceMatcher(None, cleaned, clean_string(key)).ratio()
        if sim > best_score and sim >= 0.75:
            best_score = sim
            best_match = canonical

    return best_match

def create_match_key(home_team: str, away_team: str, kickoff_date: str) -> str:
    h = get_canonical_stem(home_team).replace(' ', '_')
    a = get_canonical_stem(away_team).replace(' ', '_')
    # Keep YYYYMMDD
    date_part = kickoff_date.split('T')[0].replace('-', '')
    return f"{h}_vs_{a}_{date_part}"
