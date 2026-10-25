#!/usr/bin/env python3
"""
dirscan.py - Enumerador de directorios/ficheros por diccionario.

Uso tipico (laboratorios tipo HTB / pentesting autorizado):
    python dirscan.py -u http://10.10.10.10/ -w wordlist.txt -x php,txt,html -t 40

Solo para objetivos para los que tengas autorizacion explicita.
"""

import argparse
import concurrent.futures as cf
import random
import string
import sys
import threading
from urllib.parse import quote, urljoin

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    sys.exit("Falta 'requests'. Instala con:  pip install requests")

# --- Colores ANSI (se desactivan solos si la salida no es una terminal) ---
class C:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    GREY = "\033[90m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        for k in ("GREEN", "YELLOW", "BLUE", "CYAN", "RED", "GREY", "RESET"):
            setattr(cls, k, "")


# Color por rango de codigo de estado
STATUS_COLOR = {
    2: C.GREEN,   # 2xx - existe
    3: C.CYAN,    # 3xx - redirige
    4: C.YELLOW,  # 4xx - presente pero restringido (403/401)
    5: C.RED,     # 5xx - error de servidor
}

print_lock = threading.Lock()


def log(msg):
    """Impresion thread-safe."""
    with print_lock:
        print(msg, flush=True)


def load_wordlist(path):
    """Lee el diccionario, ignora lineas vacias y comentarios, quita duplicados."""
    words = []
    seen = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip().strip("/")
            if not w or w.startswith("#"):
                continue
            if w not in seen:
                seen.add(w)
                words.append(w)
    return words


def build_candidates(words, extensions):
    """Genera cada ruta a probar: la palabra sola y con cada extension."""
    for w in words:
        yield w
        for ext in extensions:
            yield f"{w}.{ext}"


def learn_baseline(session, base, args):
    """
    Pide una ruta aleatoria que seguro no existe para aprender como responde
    el servidor ante un 'no encontrado'. Sirve para filtrar soft-404
    (webs que devuelven 200 a todo).
    """
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=24))
    url = urljoin(base, quote(rand))
    try:
        r = session.get(url, timeout=args.timeout, allow_redirects=False,
                        verify=not args.insecure)
        return {"status": r.status_code, "length": len(r.content)}
    except requests.RequestException:
        return None


def check_path(session, base, path, args, baseline):
    """Prueba una sola ruta y devuelve un dict con el resultado si es interesante."""
    url = urljoin(base, quote(path))
    try:
        r = session.get(url, timeout=args.timeout, allow_redirects=False,
                        verify=not args.insecure)
    except requests.RequestException:
        return None

    code = r.status_code
    length = len(r.content)

    # Filtro: codigos que no queremos ver
    if code in args.exclude:
        return None
    if args.include and code not in args.include:
        return None

    # Filtro soft-404: misma respuesta que la ruta basura -> descartar
    if baseline and code == baseline["status"] and length == baseline["length"]:
        return None

    location = r.headers.get("Location", "")
    return {"url": url, "code": code, "length": length, "location": location}


def format_result(res):
    color = STATUS_COLOR.get(res["code"] // 100, C.GREY)
    line = f"{color}[{res['code']}]{C.RESET} {res['url']} {C.GREY}({res['length']} bytes){C.RESET}"
    if res["location"]:
        line += f" {C.CYAN}-> {res['location']}{C.RESET}"
    return line


def main():
    ap = argparse.ArgumentParser(
        description="Enumerador de directorios por diccionario (uso autorizado)."
    )
    ap.add_argument("-u", "--url", required=True,
                    help="URL base, ej: http://10.10.10.10/")
    ap.add_argument("-w", "--wordlist", required=True, help="Ruta del diccionario")
    ap.add_argument("-x", "--extensions", default="",
                    help="Extensiones separadas por coma, ej: php,txt,html")
    ap.add_argument("-t", "--threads", type=int, default=20, help="Hilos (def 20)")
    ap.add_argument("--timeout", type=float, default=10, help="Timeout por peticion (s)")
    ap.add_argument("-a", "--user-agent",
                    default="Mozilla/5.0 (dirscan)", help="User-Agent")
    ap.add_argument("--include", default="",
                    help="Solo mostrar estos codigos, ej: 200,301,403")
    ap.add_argument("--exclude", default="404",
                    help="Codigos a ocultar (def 404)")
    ap.add_argument("-o", "--output", help="Guardar rutas encontradas en fichero")
    ap.add_argument("-k", "--insecure", action="store_true",
                    help="No verificar certificado TLS")
    ap.add_argument("--no-color", action="store_true", help="Sin colores")
    args = ap.parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()

    # Normaliza URL base (acabada en /) y parsea listas de codigos
    base = args.url if args.url.endswith("/") else args.url + "/"
    extensions = [e.strip().lstrip(".") for e in args.extensions.split(",") if e.strip()]
    args.exclude = {int(c) for c in args.exclude.split(",") if c.strip().isdigit()}
    args.include = {int(c) for c in args.include.split(",") if c.strip().isdigit()}

    words = load_wordlist(args.wordlist)
    candidates = list(build_candidates(words, extensions))

    log(f"{C.BLUE}Objetivo   :{C.RESET} {base}")
    log(f"{C.BLUE}Diccionario:{C.RESET} {len(words)} palabras / {len(candidates)} rutas")
    log(f"{C.BLUE}Hilos      :{C.RESET} {args.threads}")
    log(f"{C.GREY}{'-' * 60}{C.RESET}")

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    baseline = learn_baseline(session, base, args)
    if baseline:
        log(f"{C.GREY}Baseline no-existe: codigo {baseline['status']}, "
            f"{baseline['length']} bytes{C.RESET}")

    found = []
    try:
        with cf.ThreadPoolExecutor(max_workers=args.threads) as ex:
            futures = [ex.submit(check_path, session, base, p, args, baseline)
                       for p in candidates]
            for fut in cf.as_completed(futures):
                res = fut.result()
                if res:
                    found.append(res)
                    log(format_result(res))
    except KeyboardInterrupt:
        log(f"\n{C.RED}Interrumpido por el usuario.{C.RESET}")

    log(f"{C.GREY}{'-' * 60}{C.RESET}")
    log(f"{C.GREEN}Encontradas: {len(found)} rutas{C.RESET}")

    if args.output and found:
        with open(args.output, "w", encoding="utf-8") as f:
            for res in sorted(found, key=lambda r: r["url"]):
                f.write(f"{res['code']}\t{res['url']}\n")
        log(f"{C.BLUE}Guardado en:{C.RESET} {args.output}")


if __name__ == "__main__":
    main()
