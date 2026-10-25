# dirscan

Enumerador de directorios/ficheros por diccionario, estilo gobuster/ffuf.
Para reconocimiento en laboratorios autorizados (HTB, CTF, pentesting con permiso).

## Requisitos
```bash
pip install requests
```

## Uso
```bash
# Basico
python dirscan.py -u http://10.10.10.10/ -w wordlist.txt

# Con extensiones y mas hilos
python dirscan.py -u http://10.10.10.10/ -w wordlist.txt -x php,txt,html -t 40

# Solo mostrar ciertos codigos y guardar
python dirscan.py -u https://target/ -w wordlist.txt --include 200,301,403 -o hallazgos.txt -k
```

## Opciones
| Flag | Descripcion |
|------|-------------|
| `-u, --url` | URL base del objetivo (obligatorio) |
| `-w, --wordlist` | Diccionario (obligatorio) |
| `-x, --extensions` | Extensiones separadas por coma: `php,txt,html` |
| `-t, --threads` | Numero de hilos (def 20) |
| `--timeout` | Timeout por peticion en segundos (def 10) |
| `--include` | Mostrar solo estos codigos: `200,301,403` |
| `--exclude` | Ocultar estos codigos (def `404`) |
| `-a, --user-agent` | User-Agent personalizado |
| `-o, --output` | Guardar rutas encontradas en fichero |
| `-k, --insecure` | No verificar certificado TLS |
| `--no-color` | Salida sin colores |

## Notas
- Para resultados reales usa diccionarios grandes (SecLists `directory-list-2.3-medium.txt`).
- El script aprende un **baseline** pidiendo una ruta aleatoria inexistente, para
  descartar *soft-404* (webs que responden 200 a todo).
- Codigos: verde 2xx (existe), cian 3xx (redirige), amarillo 4xx (403/401 restringido), rojo 5xx.
