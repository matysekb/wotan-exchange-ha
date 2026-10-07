# Nastavení a bezpečný přechod

Úplný audit, výsledky testů a rollback jsou v README v kořeni repozitáře.

1. Instalujte verzi 0.2.0. Nechte Start on boot vypnutý a mode **preflight**.
2. Exchange heslo zadejte pouze zde v lokální konfiguraci Home Assistant. Ověřte uživatele, endpoint a vlastní e-mail.
3. Start: musí být **EWS preflight OK**. V preflight režimu neběží OpenAI tunnel.
4. Stop Green aplikace. Doplňte lokálně Tunnel ID a runtime API key (Tunnels Read + Use), nastavte mode **tunnel**.
5. Zastavte Windows tunnel runtime a ověřte jeho ukončení. Potom Start Green.
6. Čekejte **Tunnel ready**, ověřte v ChatGPT známou zprávu a kalendář. Až po ověření stability povolte Start on boot a zrušte Windows autostart.

**Rollback:** Stop Green + vypnout Start on boot, poté spustit původní Windows runtime. Nikdy dva stdio klienti se stejným Tunnel ID zároveň.

**Secrets:** password pole je maskované, options se zapisují jako prostý JSON do /data/options.json; tento mechanismus není šifrování at-rest. HA administrátor a přístup k disku/zálohám mohou secrets odhalit. Nic z options nekopírujte do GitHubu ani do diagnostiky.

TLS je vždy ověřované. Pracovní doba je 07:00–17:00, Po–Pá, 30 minut, Europe/Prague. Upstream MCP verze je 0.9.0; tunnel-client 0.0.16. Staré reference a rozpracované akce z Windows nemusí být na Green dostupné; proveďte nový lookup.

Raw EWS a tunnel logy nejsou předávány do HA. Zobrazují se pouze EWS preflight status, readiness a ukončení procesu. Selhání preflight vyžaduje kontrolu lokálních options, DNS, důvěryhodného TLS a síťového přístupu. Selhání readiness navíc vyžaduje platný API key, Tunnel ID, oprávnění a HTTPS přístup k OpenAI.

ARM64 container a reálný Exchange/OpenAI provoz nebyly v přípravném prostředí spuštěny. Před ostrým přechodem musí projít dodaný ARM64 CI a test na Green.
