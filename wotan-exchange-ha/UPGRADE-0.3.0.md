# Kandidát 0.3.0: audit, změna a aktualizace Green

Základ: veřejný matysekb/wotan-exchange-ha, commit c7b4fb71dea88062ed4e4cc7051e75b7e9bca714 (add-on 0.2.0). Připravený balíček není nasazen ani publikován na GitHubu. Funkční Green a Windows fallback nebyly změněny. Windows autostart ponechte vypnutý.

## Audit a minimální změna

Vendored upstream je exchange-ews-mcp v0.9.0. EwsClient používá requests/requests-ntlm a vlastní SOAP XML, nikoli exchangelib nebo EWS Managed API. normalize_mail_folder přijímá jen šest standardních složek a jejich aliasy; FindItem vždy vytvářel DistinguishedFolderId. search_mail → service.find_email → workflow.find_email → EwsClient.search_emails_multi_folder. Více složek už fungovalo, ale jen standardních. SQLite ukládá reference zpráv; tento upgrade nemění jeho schéma ani existující reference.

Nově list_mail_folders(scope="primary") čte FindFolder s Deep traversal pod msgfolderroot. Stránkuje po 100, maximálně 20 stránek. Při neúplném či chybném stránkování selže, nepředstírá úplný strom. Výstup je plochá reprezentace stromu pomocí folder_ref a parent_ref, name, folder_class a searchable. Kořenová úroveň má parent_ref=null. Neznámé třídy, kalendáře a search folders nejsou cíle pro nové poštovní reference; běžné IPF.Note a jejich podtřídy ano.

Reference obsahuje verzi, scope a SHA256 endpointu, účtu, primary_email a EWS FolderId. Neobsahuje heslo ani raw ID; není přístupovým tokenem. Každé použití znovu načte dostupné složky a ověří členství a typ. Zůstává stejná po přejmenování i restartu, pokud EWS ID a konfigurace identity zůstanou stejné. Po změně endpointu/účtu, smazání či obnově složky může vyžadovat nové vyhledání. SHA256 reference není tvrzení o kryptografickém utajení názvů nebo identit.

search_mail.folders přijímá původní názvy i vrácené folder_ref. Původní default inbox+sentitems zůstává. Nově nejvýše 25 různých složek na dotaz; běžné původní volání tím není omezeno. Multi-folder limit+offset zůstává nejvýše 100. Není přidána volba „all“: velký mailbox může znamenat stovky sekvenčních požadavků; výběr více konkrétních složek je předvídatelnější. Každá reference vyžaduje nové discovery, což zvyšuje latenci. Existující souhrnná total_items_in_view/includes_last_item pro více složek popisuje načtené kandidáty, nikoli prokazatelný celkový počet zpráv ve schránce; nepoužívat jako důkaz úplnosti komunikace.

Nové operace používají pouze FindFolder a FindItem. Žádná nová operace nemaže, nepřesouvá ani neposílá zprávy. Dosavadní nástroje včetně draftů a kalendáře zůstávají registrované.

## Co lze tvrdit o archivu

Obyčejná složka Archiv v primární schránce se objeví ve stromu primary. Samostatný in-place/online archiv je jiný message store; EWS definuje archivemsgfolderroot. list_mail_folders(scope="archive") jej explicitně zkusí na stejném nastaveném endpointu a pod stejnou autentizací. Úspěch vrátí reference se scope archive; neúspěšný EWS výsledek vrátí unavailable_or_error a complete=false. Síťové chyby mohou skončit běžnou chybou nástroje. Žádný fallback na inbox ani tvrzení „archiv je prázdný“.

Hybridní/cloud archiv na jiném endpointu zde nemá autodiscovery, OAuth ani zvláštní přihlašovací konfiguraci. Jeho dostupnost není potvrzena. Místní Outlook PST není serverová složka a EWS jej touto cestou nezpřístupní. Podpora protokolu neznamená přístup ke konkrétnímu firemnímu archivu.

Primární zdroje:
- https://learn.microsoft.com/en-us/exchange/client-developer/web-service-reference/findfolder
- https://learn.microsoft.com/en-us/exchange/client-developer/exchange-web-services/how-to-work-with-folders-by-using-ews-in-exchange
- https://github.com/OfficeDev/ews-managed-api/blob/master/Enumerations/WellKnownFolderName.cs

## Ověření

Lokálně: 15 offline unittest testů s opravdovými runtime imports; izolované Windows dependencies v rámci upstream verzových rozsahů. Testy ověřují SOAP cíle/escaping, stránky a bezpečnostní limit, rodičovské vazby, stejné názvy, stabilitu při rename, cizí/stale reference, nepoštovní třídy, archive failure, standardní názvy i více složek. Skutečný stdio initialize/tools/list ověřil 12 nástrojů, všech 11 původních + list_mail_folders. Python kompilace prošla.

Produkční ARM64 requirements.lock, základní image, tunel, launcher, keyring a options zůstávají beze změny. Jeho Linux wheel hashes nejsou vhodné pro lokální Windows pip; lokální dependencies proto nejsou důkazem přesné ARM64 instalace. verify.yml sestavuje původní ARM64 container, dělá stdio discovery, nové offline testy s --network none a původní dummy adapter test. Žádná skutečná tajemství nejsou potřeba. Docker/ARM64 workflow ani živý EWS zde nebyly spuštěny; před produkční aktualizací musí projít CI.

UPSTREAM-SHA256.json zůstává manifestem původního upstreamu, nikoli upravených souborů. LOCAL-CHANGES.json uvádí každou lokální změnu a oba hashe. Upravený vendor již není byte-for-byte upstream; původní licence zůstává.

## Bezpečný postup aktualizace

1. Uložte chráněnou zálohu add-onu 0.2.0 včetně /data přes Home Assistant; obsahuje citlivé options a stav. Ověřte, že záloha existuje a znáte postup obnovy. Zapište současné nastavení režimu a automatického startu bez kopírování tajemství do veřejných souborů.
2. Připravte samostatnou větev v repozitáři a aplikujte přiložený patch na uvedený commit, nebo porovnejte a nahraďte zdroj dodaným kompletním balíčkem. Ponechte skrytou .github složku. Novější main nejprve porovnejte, nepřepisujte další změny slepě.
3. Na větvi/PR spusťte Verify ARM64 app (no secrets). Musí projít celý build, shell, stdio, folder tests i dummy adapter. Green zatím dál běží na 0.2.0. Verzi nepublikujte do hlavní větve, dokud kontrola není zelená.
4. Teprve pak publikujte změnu do větve, kterou HA repository používá. V HA obnovte store a ověřte verzi 0.3.0 i stejný slug. Aktualizujte v plánovaném krátkém servisním okně; aktualizace běžícího add-onu znamená přerušení služby. Nevytvářejte druhého klienta se stejným Tunnel ID.
5. Před prvním startem nastavte lokálně mode=preflight. Ověřte EWS preflight OK se zapnutým TLS. Pak zastavte aplikaci, vraťte mode=tunnel a spusťte. Ověřte Tunnel ready. Secrets ani options schema se nemění. Windows zůstává zastavený a jeho autostart vypnutý.
6. Obnovte seznam nástrojů v ChatGPT pluginu, pokud nový nástroj není vidět. Ověřte staré search_mail nad inbox/sentitems a read_mail známé zprávy, read_calendar. Potom list_mail_folders(primary), vyberte searchable archivní/podsložku a zavolejte search_mail(folders=[folder_ref]) s konkrétním obdobím. Ověřte read_mail vrácené reference. Zkuste dvě vybrané složky. Nakonec samostatně list_mail_folders(archive); negativní výsledek řešte se správcem Exchange, nepovažujte jej za úplný audit archivu. Nic neposílejte ani nemažte v rámci ověření.
7. Po úspěchu obnovte původní nastavení automatického startu Green a ověřte jeden řízený restart. Při selhání zastavte 0.3.0 a obnovte zálohu 0.2.0. Rollback nemá migraci DB k vracení. Pokud použijete Windows fallback, nejprve ověřte, že Green tunel skončil; nikdy dva klienti současně. Automatický start Windows nezapínejte.
