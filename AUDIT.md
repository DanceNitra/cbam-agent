# CBAM Comply — Audit & Verification Report

> **Dátum:** Jún 2026
> **Verzia engine:** 1.0.0
> **Repo:** github.com/DanceNitra/cbam-agent

---

## Čo tento produkt robí

Generuje **CBAM kvartálne emisné reporty** podľa:
- **Regulation (EU) 2023/956** — Carbon Border Adjustment Mechanism (základné nariadenie)
- **Commission Implementing Regulation (EU) 2025/177** — implementačné pravidlá pre CBAM register
- **Commission Delegated Regulation (EU) 2025/...** — zoznam tovarov a emisných faktorov

## Čo produkt NIE JE

- ❌ NIE JE náhrada za authorized CBAM declaranta
- ❌ NIE JE oficiálny EU register — report je určený na nahratie do CBAM Transitional Registry
- ❌ Negeneruje XML pre priamy upload (EU register nemá verejné REST API — používa UUM&DS portál)
- ❌ Nesubmittuje report za užívateľa — on musí cez EU Login schváliť a odoslať

---

## 1. CN kódy — overenie

Engine obsahuje **84 CN kódov** v 6 sektoroch. Každý kód je z oficiálnej EU **Combined Nomenclature 2025**.

| Sektor | Počet CN kódov | Zdroj |
|--------|:--------------:|-------|
| Cement | 7 | EU CN 2025, kapitola 25, 6810 |
| Iron & Steel | 24 | EU CN 2025, kapitola 72, 73 |
| Aluminium | 24 | EU CN 2025, kapitola 76 |
| Fertilizers | 27 | EU CN 2025, kapitola 28, 31 |
| Electricity | 1 | EU CN 2716.00.00 |
| Hydrogen | 1 | EU CN 2804.10.00 |

**Overenie:** Všetky kódy sú v tvare `NNNN.NN.NN` (8-miestny CN kód). Kódová štruktúra je validovaná regulárnym výrazom `^\d{4}\.\d{2}\.\d{2}$` v `engine/security.py`.

---

## 2. Default emission factors — zdroje

Default emisné faktory (tCO₂e/t) sú prevzaté z verejne dostupných zdrojov:

| Zdroj | Použité pre | Dátum |
|-------|-------------|-------|
| **EU Commission CBAM default values** | Cement, oceľ, hliník, hnojivá | 2025 |
| **World Bank Carbon Pricing Dashboard** | Štandardné faktory pre ne-EU krajiny | 2025 |
| **IEA Emission Factors Database** | Elektrina (grid emission factors) | 2025 |
| **OECD Carbon Pricing in Energy Sector** | Potvrdenie cien pre CN, UK, KR | 2025 |

**Dôležité upozornenie:** Default emisné faktory sú **konzervatívne odhady**. V reálnom CBAM reporte by mal importér použiť:
1. **Actual emissions** — overené údaje od dodávateľa (3rd party verified) → ideálne
2. **Default values** — EU defaulty, ak nie sú k dispozícii actual → konzervatívne (vyššie emisie)

Engine podporuje oba módy — ak užívateľ zadá `actual_emissions`, použije tie. Inak použije default.

### Konkrétne príklady default EF:

| CN kód | Produkt | Default EF (tCO₂e/t) | Zdôvodnenie |
|--------|---------|:--------------------:|-------------|
| 7601.10.00 | Unwrought aluminium | 1.800 | Priemer primárnej výroby hliníka (elektrolýza) |
| 7201.10.00 | Pig iron | 1.350 | Vysoká pec, koks + železná ruda |
| 7208.10.00 | Hot-rolled steel | 1.250 | Oceľový zvitok, priemerný EU EF |
| 3102.10.10 | Urea fertilizer | 1.800 | Proces Haber-Bosch, vysoká energetická náročnosť |
| 2523.10.00 | Cement clinker | 0.860 | Kalcinácia vápenca + energetika |
| 2716.00.00 | Electricity | 0.432 tCO₂e/MWh | EU priemer grid mix |

---

## 3. Manuálna kalkulácia — overenie správnosti

### Test case 1: Základný výpočet

```
1500 t unwrought aluminium (7601.10.00) z Ruska
  EF = 1.800 tCO₂e/t (default)
  Emissions = 1500 × 1.800 = 2,700.00 tCO₂e
  Carbon price (RU) = €0.00/t → deduction = €0.00
  Certificates = 2,700.00
```

✅ Engine output: `2,700.00 tCO₂e`, `2,700.00 certificates`

### Test case 2: S carbon price deduction

```
2,800 t hot-rolled steel (7208.10.00) z Číny
  EF = 1.250 tCO₂e/t (default)
  Emissions = 2800 × 1.250 = 3,500.00 tCO₂e
  Carbon price (CN ETS) = €10.50/t → deduction = 3,500 × 10.50 = €36,750.00
  Deduction v tCO₂e = 36,750 / 85 (EU ETS price) = 432.35 tCO₂e
  Certificates = 3,500.00 - 432.35 = 3,067.65
```

✅ Engine output: `3,067.65 certificates`, `€36,750.00 deduction`

### Test case 3: Multi-good kompletný report

```
4 goods:
- 1,500t aluminium (RU, EF=1.800) → 2,700.00 tCO₂e, 2,700 cert
- 3,200t pig iron (UA, EF=1.350) → 4,320.00 tCO₂e, 4,320 cert
- 2,800t steel coils (CN, EF=1.250) → 3,500.00 tCO₂e, 3,067.65 cert (deduction)
- 100t aluminium (CN, EF=1.800) → 180.00 tCO₂e, 157.76 cert (deduction)

TOTAL: 10,700.00 tCO₂e, 10,245.41 certificates, €870,860.00 cost
```

✅ Engine output: **všetky hodnoty sedia na cent** (overené 16.06.2026)

---

## 4. Carbon prices — zdroje a overenie

| Krajina | Systém | Cena (EUR/tCO₂e) | Zdroj | Dátum |
|---------|--------|:-----------------:|-------|-------|
| Čína | China National ETS | 10.50 | World Bank Carbon Pricing Dashboard 2025 | 2025 |
| UK | UK ETS | 55.00 | UK gov, obchodovaná cena | 2025 |
| Južná Kórea | K-ETS | 18.00 | World Bank 2025 | 2025 |
| Japonsko | Carbon tax | 3.50 | OECD, IEA | 2025 |
| Kanada | Federal fuel charge | 40.00 | Canadian gov | 2025 |

**Poznámka:** Väčšina ne-EU krajín (RU, UA, TR, EG, DZ, IN atď.) **nemá** národnú cenu uhlíka, preto je ich carbon_price = 0. To znamená **žiadna dedukcia**.

---

## 5. EU ETS cena pre CBAM certifikáty

CBAM certifikáty sú oceňované **priemernou cenou EU ETS** za predchádzajúci týždeň.

Engine používa konzervatívny odhad: **€85/tCO₂e** (základ 2026).

Táto hodnota je konfigurovateľná v:
- Python: `cn_codes.py` → `EU_ETS_PRICE_2026`
- JS: `cbam-data.json` → `eu_ets_price_2026`

---

## 6. Obmedzenia a riziká

| Riziko | Dôsledok | Mitigácia |
|--------|----------|-----------|
| Default EF ≠ actual EF | Report môže nadhodnotiť/podhodnotiť emisie | Engine podporuje `actual_emissions` — vždy preferovať reálne dáta od dodávateľa |
| Zmena CN kódov | Kódy sa menia každý rok (CN 2025, 2026...) | Potrebná aktualizácia datasetu pri vydaní novej CN |
| Zmena carbon price | Dedukcie budú nepresné | Ceny sa updatujú manuálne podľa World Bank dashboard |
| EU ETS cena sa mení denne | Cost estimate sa mení | Engine používa konzervatívny odhad €85 |

---

## 7. Audit trail — čo je v reporte

Každý vygenerovaný report obsahuje:

| Pole | Formát | Príklad |
|------|--------|---------|
| `report_id` | `CBAM-2026Q1-SK-008` | Unikátny identifikátor |
| `generated_at` | ISO datetime | `2026-06-16T09:35:00` |
| `version` | semver | `1.0.0` |
| Pre každý tovar: CN code, quantity, krajina, emisný faktor | Číselné | `7601.10.00, 1500t, RU, 1.8000` |
| Totals: emissions, certificates, cost | Číselné | `10,700.00 tCO₂e` |
| Carbon price deduction | EUR | `€38,640.00` |

Každý riadok v reporte je **dohľadateľný**:
- CN kód → sektor + default EF → zdôvodnený v dokumentácii
- Quantity → z importného CSV/JSON
- Country → ISO kód → carbon price → zdôvodnený

---

## 8. Záver

**CBAM Comply je overiteľný nástroj.** Každý výpočet je:
1. **Reprodukovateľný** — rovnaké vstupy → rovnaké výstupy (deterministický)
2. **Auditovateľný** — každé číslo má zdôvodnenie v dokumentácii
3. **Overený** — manuálna kalkulácia sedí s engine outputom
4. **Transparentný** — celý zdroják je na GitHub, vrátane datasetov

**Čo treba doplniť pre reálnu produkciu:**
- [ ] Pravidelná aktualizácia EU ETS ceny (týždenne)
- [ ] Aktualizácia CN kódov (ročne)
- [ ] Aktualizácia carbon prices (kvartálne)
- [ ] Integrácia s oficiálnym EU CBAM registrom (až bude API)

---

*Vypracoval: CBAM Comply Audit v1.0.0 — Jún 2026*
