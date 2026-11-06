import re
import unicodedata
from functools import lru_cache
from difflib import SequenceMatcher

CANONICAL_TEAMS: dict[str, str] = {
    # ==================== LIGA PORTUGAL ====================
    "sl benfica": "SL Benfica",
    "benfica": "SL Benfica",
    "sporting cp": "Sporting CP",
    "sporting": "Sporting CP",
    "sporting lisbon": "Sporting CP",
    "sporting clube de portugal": "Sporting CP",
    "fc porto": "FC Porto",
    "porto": "FC Porto",
    "sc braga": "SC Braga",
    "braga": "SC Braga",
    "sp. braga": "SC Braga",
    "sp braga": "SC Braga",
    "sporting de braga": "SC Braga",
    "vitoria sc": "Vitória SC",
    "vitoria de guimaraes": "Vitória SC",
    "vitoria guimaraes": "Vitória SC",
    "guimaraes": "Vitória SC",
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

    # ==================== PREMIER LEAGUE ====================
    "arsenal": "Arsenal",
    "aston villa": "Aston Villa",
    "bournemouth": "AFC Bournemouth",
    "afc bournemouth": "AFC Bournemouth",
    "brentford": "Brentford",
    "brighton": "Brighton",
    "brighton and hove albion": "Brighton",
    "chelsea": "Chelsea",
    "crystal palace": "Crystal Palace",
    "everton": "Everton",
    "fulham": "Fulham",
    "ipswich": "Ipswich Town",
    "ipswich town": "Ipswich Town",
    "leicester": "Leicester City",
    "leicester city": "Leicester City",
    "liverpool": "Liverpool",
    "manchester city": "Manchester City",
    "man city": "Manchester City",
    "manchester united": "Manchester United",
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "newcastle": "Newcastle United",
    "newcastle united": "Newcastle United",
    "newcastle utd": "Newcastle United",
    "nottingham forest": "Nottingham Forest",
    "nottingham": "Nottingham Forest",
    "southampton": "Southampton",
    "tottenham": "Tottenham Hotspur",
    "tottenham hotspur": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "west ham": "West Ham United",
    "west ham united": "West Ham United",
    "wolves": "Wolverhampton Wanderers",
    "wolverhampton": "Wolverhampton Wanderers",
    "wolverhampton wanderers": "Wolverhampton Wanderers",

    # ==================== LA LIGA ====================
    "real madrid": "Real Madrid",
    "barcelona": "FC Barcelona",
    "fc barcelona": "FC Barcelona",
    "barca": "FC Barcelona",
    "atletico madrid": "Atlético Madrid",
    "atletico de madrid": "Atlético Madrid",
    "athletic bilbao": "Athletic Bilbao",
    "athletic club": "Athletic Bilbao",
    "athletic club bilbao": "Athletic Bilbao",
    "real sociedad": "Real Sociedad",
    "sociedad": "Real Sociedad",
    "real betis": "Real Betis",
    "betis": "Real Betis",
    "villarreal": "Villarreal CF",
    "villarreal cf": "Villarreal CF",
    "valencia": "Valencia CF",
    "valencia cf": "Valencia CF",
    "sevilha": "Sevilla FC",
    "sevilla": "Sevilla FC",
    "sevilla fc": "Sevilla FC",
    "osasuna": "CA Osasuna",
    "ca osasuna": "CA Osasuna",
    "mallorca": "RCD Mallorca",
    "rcd mallorca": "RCD Mallorca",
    "celta de vigo": "Celta de Vigo",
    "celta vigo": "Celta de Vigo",
    "celta": "Celta de Vigo",
    "rayo vallecano": "Rayo Vallecano",
    "rayo": "Rayo Vallecano",
    "alaves": "Deportivo Alavés",
    "deportivo alaves": "Deportivo Alavés",
    "girona": "Girona FC",
    "girona fc": "Girona FC",
    "getafe": "Getafe CF",
    "getafe cf": "Getafe CF",
    "espanhol": "RCD Espanyol",
    "espanyol": "RCD Espanyol",
    "rcd espanyol": "RCD Espanyol",
    "las palmas": "UD Las Palmas",
    "ud las palmas": "UD Las Palmas",
    "leganes": "CD Leganés",
    "cd leganes": "CD Leganés",
    "valladolid": "Real Valladolid",
    "real valladolid": "Real Valladolid",
    "elche": "Elche CF",
    "elche cf": "Elche CF",
    "levante": "Levante UD",
    "levante ud": "Levante UD",
    "racing santander": "Racing Santander",
    "sporting gijon": "Sporting Gijón",
    "sporting de gijon": "Sporting Gijón",

    # ==================== SERIE A ====================
    "inter": "Inter Milan",
    "inter milan": "Inter Milan",
    "inter milao": "Inter Milan",
    "inter de milao": "Inter Milan",
    "internazionale": "Inter Milan",
    "milan": "AC Milan",
    "ac milan": "AC Milan",
    "milao": "AC Milan",
    "ac milao": "AC Milan",
    "juventus": "Juventus",
    "juve": "Juventus",
    "napoli": "SSC Napoli",
    "ssc napoli": "SSC Napoli",
    "napoles": "SSC Napoli",
    "ssc napoles": "SSC Napoli",
    "atalanta": "Atalanta BC",
    "atalanta bc": "Atalanta BC",
    "as roma": "AS Roma",
    "roma": "AS Roma",
    "lazio": "SS Lazio",
    "ss lazio": "SS Lazio",
    "fiorentina": "ACF Fiorentina",
    "acf fiorentina": "ACF Fiorentina",
    "bologna": "Bologna FC",
    "bologna fc": "Bologna FC",
    "torino": "Torino FC",
    "torino fc": "Torino FC",
    "como": "Como 1907",
    "como 1907": "Como 1907",
    "monza": "AC Monza",
    "ac monza": "AC Monza",
    "genoa": "Genoa CFC",
    "genoa cfc": "Genoa CFC",
    "parma": "Parma Calcio",
    "parma calcio": "Parma Calcio",
    "hellas verona": "Hellas Verona",
    "verona": "Hellas Verona",
    "empoli": "Empoli FC",
    "empoli fc": "Empoli FC",
    "udinese": "Udinese Calcio",
    "udinese calcio": "Udinese Calcio",
    "cagliari": "Cagliari Calcio",
    "cagliari calcio": "Cagliari Calcio",
    "lecce": "US Lecce",
    "us lecce": "US Lecce",
    "venezia": "Venezia FC",
    "venezia fc": "Venezia FC",

    # ==================== BUNDESLIGA ====================
    "bayern munich": "Bayern Munich",
    "bayern": "Bayern Munich",
    "bayern munchen": "Bayern Munich",
    "bayern munique": "Bayern Munich",
    "bayern de munique": "Bayern Munich",
    "fc bayern munchen": "Bayern Munich",
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
    "estugarda": "VfB Stuttgart",
    "vfb estugarda": "VfB Stuttgart",
    "sc freiburg": "SC Freiburg",
    "freiburg": "SC Freiburg",
    "hoffenheim": "TSG Hoffenheim",
    "tsg hoffenheim": "TSG Hoffenheim",
    "werder bremen": "Werder Bremen",
    "bremen": "Werder Bremen",
    "wolfsburg": "VfL Wolfsburg",
    "vfl wolfsburg": "VfL Wolfsburg",
    "borussia monchengladbach": "Borussia Mönchengladbach",
    "borussia monchen gladbach": "Borussia Mönchengladbach",
    "borussia mgladbach": "Borussia Mönchengladbach",
    "borussia m gladbach": "Borussia Mönchengladbach",
    "borussia m'gladbach": "Borussia Mönchengladbach",
    "monchengladbach": "Borussia Mönchengladbach",
    "monchen gladbach": "Borussia Mönchengladbach",
    "mgladbach": "Borussia Mönchengladbach",
    "m gladbach": "Borussia Mönchengladbach",
    "m'gladbach": "Borussia Mönchengladbach",
    "gladbach": "Borussia Mönchengladbach",
    "union berlin": "1. FC Union Berlin",
    "fc union berlin": "1. FC Union Berlin",
    "1. fc union berlin": "1. FC Union Berlin",
    "1 fc union berlin": "1. FC Union Berlin",
    "fc st pauli": "FC St. Pauli",
    "st pauli": "FC St. Pauli",
    "heidenheim": "1. FC Heidenheim",
    "augsburg": "FC Augsburg",
    "fc augsburg": "FC Augsburg",
    "bochum": "VfL Bochum",
    "mainz": "1. FSV Mainz 05",
    "mainz 05": "1. FSV Mainz 05",
    "holstein kiel": "Holstein Kiel",
    "hamburgo": "Hamburger SV",
    "hamburger": "Hamburger SV",
    "hamburger sv": "Hamburger SV",
    "hamburg sv": "Hamburger SV",
    "hamburg": "Hamburger SV",
    "koln": "1. FC Köln",
    "1. fc koln": "1. FC Köln",
    "1 fc koln": "1. FC Köln",
    "fc koln": "1. FC Köln",
    "fc cologne": "1. FC Köln",
    "cologne": "1. FC Köln",
    "colonia": "1. FC Köln",
    "fc colonia": "1. FC Köln",

    # ==================== LIGUE 1 ====================
    "paris saint-germain": "PSG",
    "paris sg": "PSG",
    "psg": "PSG",
    "marseille": "Marseille",
    "olympique marseille": "Marseille",
    "marselha": "Marseille",
    "olympique marselha": "Marseille",
    "olympique de marselha": "Marseille",
    "lyon": "Lyon",
    "olympique lyonnais": "Lyon",
    "olympique de lyon": "Lyon",
    "monaco": "AS Monaco",
    "as monaco": "AS Monaco",
    "lille": "Lille",
    "losc lille": "Lille",
    "nice": "OGC Nice",
    "ogc nice": "OGC Nice",
    "lens": "RC Lens",
    "rc lens": "RC Lens",
    "rennes": "Stade Rennais",
    "stade rennais": "Stade Rennais",
    "reims": "Stade de Reims",
    "stade de reims": "Stade de Reims",
    "strasbourg": "RC Strasbourg",
    "rc strasbourg": "RC Strasbourg",
    "estrasburgo": "RC Strasbourg",
    "rc estrasburgo": "RC Strasbourg",
    "brest": "Stade Brestois",
    "stade brestois": "Stade Brestois",
    "montpellier": "Montpellier HSC",
    "toulouse": "Toulouse FC",
    "auxerre": "AJ Auxerre",
    "aj auxerre": "AJ Auxerre",
    "angers": "Angers SCO",
    "saint-etienne": "AS Saint-Étienne",
    "saint etienne": "AS Saint-Étienne",
    "nantes": "FC Nantes",
    "le havre": "Le Havre AC",

    # ==================== BRASILEIRÃO ====================
    "flamengo": "Flamengo",
    "flamengo rj": "Flamengo",
    "palmeiras": "Palmeiras",
    "sao paulo": "São Paulo",
    "corinthians": "Corinthians",
    "fluminense": "Fluminense",
    "botafogo": "Botafogo",
    "gremio": "Grêmio",
    "gremio rs": "Grêmio",
    "internacional": "Internacional",
    "atletico-mg": "Atlético Mineiro",
    "atletico mg": "Atlético Mineiro",
    "atletico mineiro": "Atlético Mineiro",
    "atletico-pr": "Athletico Paranaense",
    "atletico pr": "Athletico Paranaense",
    "athletico paranaense": "Athletico Paranaense",
    "cruzeiro": "Cruzeiro",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "fortaleza": "Fortaleza EC",
    "bahia": "EC Bahia",
    "cuiaba": "Cuiabá",
    "coritiba": "Coritiba",
    "coritiba pr": "Coritiba",
    "santos": "Santos FC",

    # ==================== SAUDI PRO LEAGUE ====================
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

    # ==================== EUROPEAN COMPETITIONS ====================
    "salzburgo": "Red Bull Salzburg",
    "rb salzburgo": "Red Bull Salzburg",
    "salzburg": "Red Bull Salzburg",
    "rb salzburg": "Red Bull Salzburg",
    "red bull salzburg": "Red Bull Salzburg",
    "dinamo zagreb": "Dinamo Zagreb",
    "dnamo zagreb": "Dinamo Zagreb",
    "gnk dinamo zagreb": "Dinamo Zagreb",
    "sparta praga": "Sparta Prague",
    "sparta prague": "Sparta Prague",
    "slavia praga": "Slavia Prague",
    "slavia prague": "Slavia Prague",
    "levski sofia": "Levski Sofia",
    "levski sfia": "Levski Sofia",
    "jagiellonia": "Jagiellonia Bialystok",
    "jagiellonia bialystok": "Jagiellonia Bialystok",
    "anderlecht": "RSC Anderlecht",
    "rsc anderlecht": "RSC Anderlecht",
    "az": "AZ Alkmaar",
    "az alkmaar": "AZ Alkmaar",
    "galatasaray": "Galatasaray",
    "galatasaray sk": "Galatasaray",
    "fenerbahce": "Fenerbahçe",
    "fenerbahce sk": "Fenerbahçe",
    "besiktas": "Beşiktaş",
    "besiktas jk": "Beşiktaş",
    "shakhtar": "Shakhtar Donetsk",
    "shakhtar donetsk": "Shakhtar Donetsk",
    "dynamo kyiv": "Dynamo Kyiv",
    "dinamo kiev": "Dynamo Kyiv",
    "feyenoord": "Feyenoord",
    "feyenoord rotterdam": "Feyenoord",
    "psv": "PSV Eindhoven",
    "psv eindhoven": "PSV Eindhoven",
    "ajax": "Ajax",
    "bodo glimt": "Bodo/Glimt",
    "bodo/glimt": "Bodo/Glimt",
    "club brugge": "Club Brugge",
    "brugge": "Club Brugge",

    # ==================== EUROPEAN & SCOTTISH CLUBS ====================
    "heart of midlothian": "Hearts",
    "heart of midlothian fc": "Hearts",
    "hearts": "Hearts",
    "hearts fc": "Hearts",
    "fc thun": "Fc Thun",
    "thun": "Fc Thun",
    "hibernian": "Hibernian",
    "hibs": "Hibernian",
    "celtic": "Celtic",
    "celtic fc": "Celtic",
    "rangers": "Rangers",
    "rangers fc": "Rangers",
    "aberdeen": "Aberdeen",
    "estrela vermelha": "Red Star Belgrade",
    "red star": "Red Star Belgrade",
    "red star belgrade": "Red Star Belgrade",
    "crvena zvezda": "Red Star Belgrade",
    "inter club de escaldes": "Inter D'Escaldes",
    "inter escaldes": "Inter D'Escaldes",
    "friburgo": "SC Freiburg",
    "sc friburgo": "SC Freiburg",
    "freiburg": "SC Freiburg",
    "sc freiburg": "SC Freiburg",
    "copenhaga": "FC Copenhagen",
    "kobenhavn": "FC Copenhagen",
    "fc kobenhavn": "FC Copenhagen",
    "f.c. kobenhavn": "FC Copenhagen",
    "fc copenhagen": "FC Copenhagen",
    "lillestrom": "Lillestrom",
    "lillestrom sk": "Lillestrom",
    "lillestrom sk.": "Lillestrom",
    "lillestrøm": "Lillestrom",
    "lillestrøm sk": "Lillestrom",
    "viktoria plzen": "FC Viktoria Plzen",
    "fc viktoria plzen": "FC Viktoria Plzen",
    "viktoria plzeň": "FC Viktoria Plzen",
    "union saint-gilloise": "Union Saint-Gilloise",
    "union saint gilloise": "Union Saint-Gilloise",
    "union st gilloise": "Union Saint-Gilloise",
    "union st.-gilloise": "Union Saint-Gilloise",
    "royale union sg": "Union Saint-Gilloise",
    "cs universitatea craiova": "CSU Craiova",
    "universitatea craiova": "CSU Craiova",
    "csu craiova": "CSU Craiova",
    "kf egnatia rrogozhine": "Egnatia",
    "egnatia": "Egnatia",
    "sint-truidense vv": "Sint-Truidense",
    "sint truidense": "Sint-Truidense",
    "sint-truidense": "Sint-Truidense",
    "brann": "SK Brann",
    "sk brann": "SK Brann",
    "zalgiris kaunas": "Kauno Zalgiris",
    "kauno zalgiris": "Kauno Zalgiris",
    "lugano": "FC Lugano",
    "fc lugano": "FC Lugano",
    "fc iberia 1999": "Iberia 1999",
    "iberia 1999": "Iberia 1999",
    "fc nordsjaelland": "FC Nordsjælland",
    "fc nordsjælland": "FC Nordsjælland",
    "nordsjaelland": "FC Nordsjælland",
    "pafos fc": "Pafos",
    "pafos": "Pafos",
    "twente": "FC Twente",
    "fc twente": "FC Twente",
}

@lru_cache(maxsize=4096)
def clean_string(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # Normalize special European characters before ASCII encode
    s = s.replace('ø', 'o').replace('æ', 'ae').replace('ß', 'ss').replace('ł', 'l').replace('đ', 'd').replace('ı', 'i')
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    # Remove common prefixes/suffixes & club acronyms without stripping genuine team names
    s = re.sub(r'\b(fc|cf|cd|sc|ac|sad|gd|sl|rcd|ca|rj|rs|pr|mg|sp|vfl|vfb|tsg|ogc|rc|afc|bsc|ssc|calcio|us|ss|as|ud|sk|fk|bk|if|ff)\b', '', s)
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

PREPARED_CANONICAL = [(clean_string(k), canon) for k, canon in CANONICAL_TEAMS.items()]

@lru_cache(maxsize=4096)
def normalize_team_name(name: str) -> str:
    if not name or not name.strip():
        return ""

    raw = name.strip()
    raw_lower = raw.lower()

    # 1. Exact raw lowercase match
    if raw_lower in CANONICAL_TEAMS:
        return CANONICAL_TEAMS[raw_lower]

    cleaned = clean_string(raw)
    # 2. Exact cleaned match
    if cleaned in CANONICAL_TEAMS:
        return CANONICAL_TEAMS[cleaned]

    # 3. Exact prepared canonical match
    for c_key, canonical in PREPARED_CANONICAL:
        if c_key == cleaned:
            return canonical

    # 4. Multi-word subset matching (whole tokens only, preventing substring corruption)
    cleaned_tokens = set(cleaned.split())
    if len(cleaned_tokens) >= 2:
        for c_key, canonical in PREPARED_CANONICAL:
            c_tokens = set(c_key.split())
            if len(c_tokens) >= 2 and (c_tokens == cleaned_tokens or c_tokens.issubset(cleaned_tokens)):
                return canonical

    # 5. Strict high-confidence fuzzy matching (ratio >= 0.90, max len difference <= 2)
    best_match = None
    best_score = 0.0
    for c_key, canonical in PREPARED_CANONICAL:
        if abs(len(c_key) - len(cleaned)) > 2:
            continue
        sim = SequenceMatcher(None, cleaned, c_key).ratio()
        if sim > best_score and sim >= 0.90:
            best_score = sim
            best_match = canonical

    if best_match:
        return best_match

    # 6. Fallback: preserve original name cleanly (NEVER cross-map to an unrelated club!)
    return " ".join(word.capitalize() for word in raw.split())

@lru_cache(maxsize=4096)
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

LEAGUE_CANONICAL: dict[str, str] = {
    "alemanha - bundesliga": "Bundesliga",
    "bundesliga": "Bundesliga",
    "brasileirao serie a": "Brasileirão",
    "brasileirão série a": "Brasileirão",
    "brasileirao": "Brasileirão",
    "brasileirão": "Brasileirão",
    "brasil - serie a": "Brasileirão",
    "conference league": "Conference League",
    "uefa conference league": "Conference League",
    "liga conferencia": "Conference League",
    "liga conferência": "Conference League",
    "espanha - la liga": "La Liga",
    "la liga": "La Liga",
    "laliga": "La Liga",
    "primera division": "La Liga",
    "franca - ligue 1": "Ligue 1",
    "frança - ligue 1": "Ligue 1",
    "ligue 1": "Ligue 1",
    "inglaterra - premier league": "Premier League",
    "premier league": "Premier League",
    "italia - serie a": "Serie A",
    "itália - serie a": "Serie A",
    "itália - série a": "Serie A",
    "italia - serie a tim": "Serie A",
    "serie a": "Serie A",
    "liga portugal": "Liga Portugal",
    "liga portugal betclic": "Liga Portugal",
    "portugal - primeira liga": "Liga Portugal",
    "primeira liga": "Liga Portugal",
    "liga dos campeoes": "Champions League",
    "liga dos campeões": "Champions League",
    "champions league": "Champions League",
    "uefa champions league": "Champions League",
    "liga europa": "Europa League",
    "europa league": "Europa League",
    "uefa europa league": "Europa League",
    "saudi pro league": "Saudi Pro League",
    "uae pro league": "UAE Pro League",
    "catar stars league": "Qatar Stars League",
    "qatar stars league": "Qatar Stars League"
}

def normalize_league_name(league: str) -> str:
    if not league:
        return "Desconhecido"
    cleaned = clean_string(league)
    return LEAGUE_CANONICAL.get(cleaned, LEAGUE_CANONICAL.get(league.lower().strip(), league.strip()))

def create_match_key(home_team: str, away_team: str, kickoff_date: str) -> str:
    h = get_canonical_stem(home_team).replace(' ', '_')
    a = get_canonical_stem(away_team).replace(' ', '_')
    date_part = str(kickoff_date).replace('T', ' ').split(' ')[0].replace('-', '')
    return f"{h}_vs_{a}_{date_part}"
