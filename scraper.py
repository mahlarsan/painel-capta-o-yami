"""Coleta oportunidades de financiamento para a Yami e grava data/editais.json."""
import json, re, hashlib, datetime as dt, pathlib
import requests, feedparser
from bs4 import BeautifulSoup

OUT = pathlib.Path("data/editais.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (painel-editais-yami)"}

# type: "html" (pega links com palavras de edital) ou "rss". Ajuste/adicione fontes aqui.
SOURCES = [
 # Impacto e filantropia
 {"name": "IDB Lab", "group": "Impacto e filantropia", "type": "html", "url": "https://bidlab.org/en/calls-for-proposals"},
 {"name": "Google.org", "group": "Impacto e filantropia", "type": "html", "url": "https://impactchallenge.withgoogle.com/"},
 # Fomento à inovação e tecnologia
 {"name": "Finep", "group": "Inovação e tecnologia", "type": "html", "url": "https://www.finep.gov.br/chamadas-publicas/chamadaspublicas?situacao=aberta"},
 {"name": "BNDES", "group": "Inovação e tecnologia", "type": "html", "url": "https://www.bndes.gov.br/wps/portal/site/home/transparencia/chamadas-publicas"},
 {"name": "CNPq", "group": "Inovação e tecnologia", "type": "html", "url": "http://memoria2.cnpq.br/web/guest/chamadas-publicas"},
 {"name": "FAPESP", "group": "Inovação e tecnologia", "type": "html", "url": "https://fapesp.br/oportunidades/"},
 {"name": "Embrapii", "group": "Inovação e tecnologia", "type": "html", "url": "https://embrapii.org.br/"},
 {"name": "Sebrae", "group": "Inovação e tecnologia", "type": "html", "url": "https://sebrae.com.br/sites/PortalSebrae/editais"},
]

LINK_WORDS = re.compile(r"edital|chamada|convocat|call for|open call|grant|challenge|fundo|prêmio|premio|funding|rfp", re.I)
FIT = {  # palavra-chave -> peso de aderência à Yami
 "impacto": 3, "impact": 3, "avaliação": 2, "monitoramento": 2, "inteligência artificial": 3, "artificial intelligence": 3,
 "ia ": 2, "ai ": 2, "gênero": 3, "gender": 3, "mulheres": 2, "socioambiental": 3, "clima": 2, "climate": 2,
 "startup": 2, "inovação": 2, "innovation": 2, "américa latina": 2, "latin america": 2, "negócios de impacto": 3, "tecnologia": 1,
}
DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

def score(text):
    t = text.lower()
    return sum(w for k, w in FIT.items() if k in t)

def deadline(text):
    ds = []
    for d, m, y in DATE.findall(text):
        try: ds.append(dt.date(int(y), int(m), int(d)))
        except ValueError: pass
    fut = [d for d in ds if d >= dt.date.today()]
    return (max(fut) if fut else None)

def from_html(src):
    soup = BeautifulSoup(requests.get(src["url"], headers=HEADERS, timeout=30).text, "html.parser")
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text().split())
        if len(title) < 15 or not LINK_WORDS.search(title): continue
        ctx = " ".join(a.parent.get_text(" ").split())[:400]
        link = requests.compat.urljoin(src["url"], a["href"])
        yield title, link, ctx

def from_rss(src):
    for e in feedparser.parse(src["url"]).entries:
        yield e.title, e.link, e.get("summary", "")

def main():
    old = {i["id"]: i for i in json.loads(OUT.read_text())["items"]} if OUT.exists() else {}
    items, log = {}, []
    for s in SOURCES:
        try:
            n = 0
            for title, link, ctx in (from_rss(s) if s["type"] == "rss" else from_html(s)):
                _id = hashlib.md5(link.encode()).hexdigest()[:12]
                d = deadline(ctx)
                items[_id] = {"id": _id, "fonte": s["name"], "grupo": s["group"], "titulo": title, "link": link,
                    "prazo": d.isoformat() if d else None, "aderencia": score(title + " " + ctx),
                    "visto_em": old.get(_id, {}).get("visto_em", dt.date.today().isoformat())}
                n += 1
            log.append({"fonte": s["name"], "itens": n, "erro": None})
        except Exception as ex:
            log.append({"fonte": s["name"], "itens": 0, "erro": str(ex)[:120]})
    OUT.write_text(json.dumps({"gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fontes": log, "items": sorted(items.values(), key=lambda i: -i["aderencia"])}, ensure_ascii=False, indent=1))
    for l in log: print(l)

if __name__ == "__main__":
    main()
