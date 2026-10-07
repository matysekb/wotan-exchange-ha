# Wotan Exchange pro Home Assistant Green — kandidát 0.3.0

Rozšíření dostupných poštovních složek. Audit, omezení archivu, testy a bezpečný upgrade: [UPGRADE-0.3.0.md](UPGRADE-0.3.0.md).

# Wotan Exchange pro Home Assistant Green — 0.2.0

Připravená implementace pro instalační ověření. **Není zatím potvrzen provoz na Green ani připojení ke skutečnému Exchange/OpenAI účtu.** Windows fallback nebyl upraven ani vypnut. Bez Dockeru a přístupu k zařízení nelze poctivě označit ARM64 container za otestovaný.

## Výsledek auditu

Auditovaný upstream: [ShermanGu/exchange-ews-mcp v0.9.0](https://github.com/ShermanGu/exchange-ews-mcp/tree/v0.9.0), commit `859b275db83184c9125ae50551c8d0fe89ad1c39`. Tag a commit ověřeny přes veřejné GitHub API. Zdroj byl stažen a čten přímo, nikoli odvozen z README. Kopie `src/`, `pyproject.toml`, README a MIT licence je v `wotan_exchange/vendor/exchange-ews-mcp/`; její SHA256 manifest je `UPSTREAM-SHA256.json`. Součástí balíčku není starý Windows runtime.

| Oblast | Ověření ve zdrojovém kódu |
|---|---|
| Konfigurace | `config.py`: dataclass `AppConfig`, validace, JSON, atomický zápis přes dočasný soubor. `config_path()` používá `platformdirs.user_config_dir(APP_NAME, appauthor=False)`. Konfigurace není natvrdo Windows-specific a neobsahuje heslo. |
| Heslo | `credentials.py`: service `exchange-ews-mcp`; `keyring.get_password(service, username)`, bez env fallbacku. `store_password`/`delete_password` používají stejný keyring. |
| EWS | `service.py:configured_client()` načte config a heslo, vytvoří `EwsClient`. `ews.py` používá `requests.Session` a `requests_ntlm.HttpNtlmAuth`; HTTPS ověření předává na každý request přes `verify=config.verify_tls`. |
| MCP start | Entry point `exchange-ews-mcp = exchange_ews_mcp.cli:main`; `serve` volá produkční `server.main()`, který spouští `FastMCP.run(transport="stdio")`. Neprovádí interaktivní configure. |
| Nástroje | `tool_profiles.py:PRODUCTION_TOOL_NAMES` obsahuje přesně požadovaných 11 názvů. Produkční registraci ověřil skutečný stdio `tools/list`, nejen analýza konstant. |
| Stav | `state_store.py` používá přenositelný SQLite a `platformdirs.user_data_dir`, včetně ItemId/ChangeKey referencí a rozpracovaných akcí. Stav patří do persistentního `/data`. |
| Windows části | Instalační `.cmd`/`.ps1` a Windows onboarding. V runtime `src/` nebyl nalezen import WinAPI, `winreg`, volání PowerShellu/cmd ani podmínka vyžadující Windows. Windows timezone ID v EWS XML jsou součástí protokolu Exchange, nikoli závislost na Windows hostiteli. |
| Vedlejší konfigurace | `dt_config.py`, `phase2_config.py`, `workflow_test_config.py` a DT reporty rovněž používají `platformdirs`. Produkční server nemusí spouštět DT testy. |

Deklarované runtime dependencies: Python >=3.10, `mcp[cli]>=1.27,<2`, `requests>=2.32,<3`, `requests-ntlm>=1.3,<2`, `keyring>=25,<26`, `platformdirs>=4.3,<5`, `tzdata>=2025.2`. Tranzitivně zejména Pydantic, AnyIO, HTTPX, pyspnego a cryptography. NTLM knihovna má platformní rozdíly v implementaci; skutečná autentizace na Linuxu zde nebyla ověřena. Pro každý zvolený Linux ARM64 balíček byl nalezen a stažen kompatibilní wheel. Linuxové keyring balíčky SecretStorage/Jeepney jsou nainstalovány jako dependencies, ale zvolený backend nepotřebuje D-Bus ani desktopový keyring.

**Závěr:** nebyl nalezen technický důvod Green odmítnout. Nejmenší port nepotřebuje měnit config modul ani server. Vyžaduje explicitně zvolený keyring backend a standardní XDG umístění konfigurace a dat. Závěr o nasaditelnosti musí ještě potvrdit ARM64 build a test na zařízení.

## Architektura

Supervisor předá `/data/options.json` → launcher validuje options → upstream `save_config()` vytvoří konfiguraci bez hesla → read-only keyring čte heslo z options pouze pro správný service a uživatele → nezměněný EWS/MCP server.

V režimu `tunnel` oficiální tunnel-client spouští přes `--mcp.command=exchange-ews-mcp serve` jeden stdio proces. API key je pouze v runtime prostředí klienta; Tunnel ID také. Heslo se nekopíruje do prostředí, dalšího souboru ani command-line argumentu. Upstream config a SQLite mají cesty `/data/config` a `/data/state`; přílohy jsou omezené na `/data/attachments`. Nové soubory vznikají pod `umask 077`. Windows workflow reference ani resume tokeny se nepřenášejí: po přechodu začněte novým vyhledáním, čtením či novou akcí. Windows SQLite fallback zůstává oddělený.

Container vychází z oficiálního glibc Python image `python:3.13.16-slim-bookworm`, připnutého digestem manifestu `sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641`. Registr potvrdil Linux ARM64/v8 variantu. Debian je zvolen kvůli dostupným ARM64 manylinux wheels. Home Assistant base image není podmínkou vlastní aplikace. Nepoužíváme S6, proto `init: true` ponechává Supervisor init pro práci s procesy. `startup: application`, výchozí `boot: manual`, žádný port, ingress, host networking, Supervisor API ani privileged přístup. `backup: cold` chrání konzistenci SQLite při záloze. `stage: experimental` odpovídá dosud neprovedenému testu na zařízení.

Připnutý oficiální [tunnel-client v0.0.16](https://github.com/openai/tunnel-client/releases/tag/v0.0.16), vydaný 6. 10. 2026. Ověřený asset je **`tunnel-client-v0.0.16-linux-arm64.zip`**, SHA256 `963d0384aaa7c798778479c45673f9051a4039dd891aef8f8978d2a1a628b74f`. Archiv byl stažen, porovnán s release `SHA256SUMS.txt` a jeho klient má ELF64 little-endian `e_machine=183` (AArch64). Build stahuje přesný asset, kontroluje připnutý hash a ELF hlavičku; instalují se klient a licenční informace. Přibalený cloudflared se pro tento stdio polling transport nepoužívá. Verzi lze aktualizovat až novým auditem a testy, nikoli aliasem latest.

Podle [oficiální konfigurace klienta](https://github.com/openai/tunnel-client/blob/v0.0.16/docs/configuration.md#stdio-deployment-limits) jsou dva současně aktivní stdio klienti se stejným Tunnel ID nepodporované. Výchozí preflight proto tunel nikdy nespustí.

## Bezpečnost a omezení

- HA options **nejsou tímto mechanismem šifrované at-rest**. V Supervisoru 2026.09.1 `apps/app.py:write_options` volá `utils/json.py:write_json_file`, který zapisuje prostý JSON a nastaví `0600`. `apps/options.py` převádí schema `password` na UI `format: password`. Jde o maskování a souborová práva, ne šifrování. Totéž platí pro upstream config a SQLite. Šifrování záloh je samostatná vlastnost a nenahrazuje ochranu běžících dat.
- HA administrátor, přístup k úložišti nebo privilegovaný host může secrets získat. Chraňte HA účet, zařízení a zálohy. Options nikdy neposílejte jako diagnostiku a neukládejte do repozitáře.
- Launcher vypisuje pouze pevné statusy, readiness a číselný exit status. Raw EWS/tunnel stdout a stderr do HA logu nepředává; tím se ztrácí podrobné diagnostické chyby. Nezapínejte dodatečné debug logování s reálnými secrets. Vnitřní admin/health endpoint zůstává na loopbacku containeru a není publikován.
- TLS verification je pevně `true`; vypnutí se nenabízí. Pokud firemní EWS potřebuje neveřejnou CA nebo přístup jen z firemní sítě, preflight selže. V takovém případě je potřeba spravovaná důvěryhodná CA nebo schválené síťové připojení; ne vypnutí TLS kontroly nebo zásah do HAOS.
- API key má mít pouze Tunnels Read + Use. Secrets zadáváte lokálně až po instalaci, nikoli při Docker buildu.
- Šlo o audit aktuálních souborů veřejného repozitáře a nového balíčku, ne kompletní historie všech dřívějších commitů. Skutečná tajemství mi nebyla předána. V balíčku jsou pouze prázdné secret defaults a zřetelně dummy testovací hodnoty.

## Změny proti veřejnému prototypu 0.1.0

`repository.yaml` zůstává. Nahrazeny jsou všechny čtyři prototypové soubory: Dockerfile, run.sh, config.yaml a ha_keyring.py. Odstraněn odkaz na neexistující start-wotan.sh, instalace git HEAD, nepřipnutý base image a vypisování uživatele/endpointu. Přidány launcher, kontrolované stažení tunelu, hashované dependency lock, nezměněná vendored upstream verze, testy, ARM64 CI, dokumentace, changelog a ochranné ignore soubory. Jméno složky i slug zůstávají stejné, verze je 0.2.0. Kalendář má explicitně Europe/Prague, Po–Pá, 07:00–17:00 a 30 minut.

## Provedené testy a zbývající ověření

| Kontrola | Skutečný výsledek |
|---|---|
| YAML | Parsování repository.yaml, config.yaml a CI YAML prošlo; není to validace běžícím Supervisorem. |
| Python | Kompilace souborů a reálné importy MCP/keyring/requests-ntlm/YAML prošly. |
| Testy | **241 passed**: 236 upstream unit testů a 5 portových testů. Použity skutečné dependencies, nikoli upstream fallback stubs. Testuje se config, načtení/rotace hesla, service/username scope, read-only backend, vytvoření EWS klienta, absence hesla v configu, SQLite cesta, výběr backendu a bezpečné launcher argumenty/logy. |
| Stdio MCP | Skutečný samostatný Python proces odpověděl na initialize a tools/list; přesně 11 produkčních tools. Žádný EWS request ani tunel nebyl v tomto testu proveden. |
| Upstream integrita | Vendored soubory mají stejné SHA256 jako stažený tag; source se neupravoval. |
| ARM64 klient | Release checksum + ELF64 AArch64 ověřeny. Windows kopie téhož release prošla --version a run --help; nešlo o existující Windows instalaci. Linux binary nebyla spuštěna. |
| Dependency ARM64 | Pro přesné zvolené Linux/CPython 3.13 dependencies byly staženy kompatibilní wheels; instalace v Linux image zatím neproběhla. |
| Shell syntax | `sh -n` byl skutečně zkusen, ale lokální Git shell odmítl vytvořit signal pipe (Win32 error 5). Obsah byl staticky zkontrolován; **shell syntax tool zde nedokončil kontrolu**. CI obsahuje sh -n. |
| Docker build/run | **Neprovedeno:** v prostředí není Docker a WSL není použitelný. CI je připravené pro build a dummy testy v ARM64 containeru přes QEMU, ale nebylo spuštěno na GitHubu. |
| Green/Supervisor | **Neprovedeno:** nemám přístup k vašemu Green. HAOS 18.3 / Core 2026.9.4 / Supervisor 2026.09.1 nejsou empiricky potvrzené; implementace odpovídá ověřenému aktuálnímu formátu a source Supervisoru. |
| Živý EWS/OpenAI/ChatGPT | **Neprovedeno:** žádná skutečná autentizace, čtení mailboxu, write tool, readiness proti OpenAI ani dlouhodobý 24/7 provoz. |

Při lokálních testech Windows `platformdirs` ignoruje XDG. Testovací runner proto izoloval DT report paths a adapter test emuloval Linux XDG cesty; nijak neměnil produkční source. Sandbox blokoval pytest temp dirs s restriktivním mode, proto runner použil obyčejné adresáře uvnitř work/. To není důkaz Linux běhu. Lokální pip byl rovněž omezen sandboxem; pro testy byly závislosti staženy z PyPI jako wheels a rozbaleny do izolovaného work/site, bez změny globální instalace.

## Co udělat dále

1. Rozbalte ZIP a nahraďte obsah svého GitHub repozitáře obsahem složky `wotan-exchange-ha` jako **jednu ucelenou změnu**. Secrets nepřidávejte. Alternativou je přiložený patch vůči staženému prototypu. ZIP obsahuje i skryté soubory `.github`, `.gitignore` a `.gitattributes`.
2. V GitHub Actions spusťte **Verify ARM64 app (no secrets)**. Musí projít build, shell syntax, stdio discovery a dummy adapter. Workflow nevyžaduje vaše Exchange heslo ani OpenAI API key. Pokud build selže, Windows dál funguje a Green zatím nespouštějte s tunelem.
3. V HA App Store obnovte repository a ověřte verzi **0.2.0**, poté instalujte. Ponechte automatický start vypnutý. V lokální konfiguraci zadejte Exchange heslo; uživatele ověřte jako `DOMLAS\barta` (jedno skutečné zpětné lomítko), e-mail a URL. Nechte `mode: preflight`; Tunnel ID a API key mohou zůstat prázdné.
4. Spusťte aplikaci. Požadovaný log je **EWS preflight OK (TLS verification enabled)** a informace, že tunel je vypnutý. Při chybě nepokračujte do tunnel režimu. Tento test pouze čte EWS, neposílá poštu ani pozvánky.
5. Zastavte Green aplikaci. Lokálně doplňte skutečné Tunnel ID a runtime API key, přepněte `mode: tunnel`. **Před Start na Green zastavte pouze stávající Windows tunnel runtime** a ověřte, že neběží. Windows konfiguraci, credentials a autostart zatím neměňte.
6. Spusťte Green. Čekejte na EWS preflight OK a **Tunnel ready**. V dosavadním ChatGPT pluginu ověřte vyhledání a přečtení konkrétní známé zprávy a čtení kalendáře. Staré message_ref/resume_token mohou vyžadovat nový lookup. Následně otestujte draft; pozvánku posílejte jen jako vědomý skutečný test. Nezaměňujte přítomnost toolu s ověřením jeho funkce.
7. Po potvrzení stabilního provozu přes restart Green a alespoň několik dní provozu povolte Start on boot na Green. Windows autostart odstraňte teprve po tomto potvrzení, aby při restartu PC nevznikl souběh. Do té doby PC bez dohledu nerestartujte se zapnutým Windows autostartem.

## Rollback

Zastavte Green aplikaci a vypněte její Start on boot; ověřte, že její tunnel proces skončil. Pak spusťte původní Windows runtime obvyklým způsobem. Tunnel ID a ChatGPT plugin nemusíte měnit. Ověřte jednoduchý read-only dotaz. Green nesmí běžet současně. Windows heslo ani jeho nastavení není potřeba obnovovat, protože se během přípravy neměnily. Před další aktualizací úspěšně nasazeného Green vytvořte chráněnou zálohu aplikace; `/data` obsahuje citlivý stav i secrets.

## Primární zdroje

- [Upstream source v0.9.0](https://github.com/ShermanGu/exchange-ews-mcp/tree/v0.9.0/src/exchange_ews_mcp)
- [Původní veřejný repozitář](https://github.com/matysekb/wotan-exchange-ha)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [Oficiální release 0.0.16](https://github.com/openai/tunnel-client/releases/tag/v0.0.16) a [SHA256SUMS](https://github.com/openai/tunnel-client/releases/download/v0.0.16/SHA256SUMS.txt)
- [HA App configuration, aktualizovaná 5. 10. 2026](https://developers.home-assistant.io/docs/apps/configuration/)
- [Supervisor 2026.09.1 options](https://github.com/home-assistant/supervisor/blob/2026.09.1/supervisor/apps/app.py), [JSON persistence](https://github.com/home-assistant/supervisor/blob/2026.09.1/supervisor/utils/json.py), [password UI schema](https://github.com/home-assistant/supervisor/blob/2026.09.1/supervisor/apps/options.py)
