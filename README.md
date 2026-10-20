# JalSatya (जलसत्य)

**A chlorine test with proof built in.** Team PARAKRAM, Smart India Hackathon 2026, problem statement SIH26253 (Ministry of Jal Shakti, National Jal Jeevan Mission).

JalSatya is a dye-free test strip for free residual chlorine, a pocket reader and a field app. The reader measures the strip's current instead of asking anyone to judge a colour. It is designed to read in 0.1 mg/L steps, about 10 seconds from dip to result. Every result is signed with the strip serial, place, time and the strip's own signal, so no record exists without a real strip being read: no strip, no record. A village chlorine twin turns verified tests into the right dose at the tank, flags readings that do not fit their tap, and picks the next taps to test.

- Live demo: https://codedbysuryansh.github.io/PARAKRAM-SIH26253/
- Video: https://youtu.be/rtyKnEUzjjI
- Idea deck: `deck/PARAKRAM_SIH26253_JalSatya.pdf`

## What is in this folder

| Folder | What it holds |
|---|---|
| `demo/` | The working prototype. Open `demo/index.html` in Chrome, Edge or Safari. It runs offline. |
| `sim/` | The physics model behind the demo: strip current (Cottrell equation), chlorine chemistry, noise and drift, the Proof-of-Test checks and the village twin. `python3 sim/jalsatya_sim.py` writes `sim/results.json`. |
| `deck/` | The 6-slide idea deck on the official SIH 2026 template, and the script that builds it. |
| `DEMO_SCRIPT.md` | The 2-minute walkthrough: what to say, what to click, and answers to likely questions. |

## The prototype

1. **Test a tap.** Scan a strip, dip it, watch the electrode signal draw live, get a signed result.
2. **Try to fake a test.** Reuse a strip, type a number, upload a copied curve or an invented one. Each is refused, with the reason.
3. **Why it reads true.** Change the chlorine and the water's pH. The buffered strip stays true; a bare electrode and a colour chart do not.
4. **Village chlorine twin.** Learns how chlorine fades through a sample 120-tap scheme from a few verified tests, then recommends the dose and the next taps to test.
5. **District view.** Verified tests only, refused records, low-chlorine alerts and kit stock.

The field app switches between English and Hindi, and can read its prompts aloud.

## Honest status

This is a prototype. Sensor readings are simulated from published electrochemistry, and village and district data are sample data. Every simulated number is labelled as simulated in the demo and the deck. The next stage is a working strip and reader, checked against the standard DPD method in the lab, then a field pilot.

Simulated results (from `sim/results.json`): detection limit 0.027 mg/L, 98% of readings within ±0.1 mg/L over 0 to 2 mg/L, pH 6 to 9 handled by the buffer pad, all 2,000 fakes across the five attacks we modelled refused, 99.3% of real tests accepted. On the sample 120-tap scheme the twin, learning from five verified tests, moves the dose from 1.00 to 1.26 mg/L and the taps in range from 108 to 120.

Known limits, stated plainly: a reader cannot tell which water the strip was dipped in, so the twin flags readings that do not fit their tap; and a tampered reader that fakes a realistic curve is resisted by a key held in a secure chip, while every fake still uses up an issued strip.

## Key references

1. DDWS, Ministry of Jal Shakti. Drinking Water Quality Monitoring and Surveillance Framework, 2021.
2. CAG. Performance Audit of Jal Jeevan Mission, Maharashtra, Report No. 2 of 2026, Chapter V.
3. PIB. Jal Jeevan Mission factsheet, data as on 21 and 22 October 2025.
4. BIS. IS 10500:2012, Drinking Water Specification.
5. Bard, A. J. and Faulkner, L. R. Electrochemical Methods, 2nd ed., Wiley, 2001.
6. Morris, J. C. The acid ionization constant of HOCl from 5 to 35 °C. J. Phys. Chem., 1966.

The full list is on slide 6 of the deck.

## Third-party components

- Apache ECharts 5.6.0, Apache License 2.0 (`demo/vendor/echarts.min.js`, licence header kept in the file).
- Barlow and Barlow Semi Condensed typefaces, SIL Open Font License 1.1 (`demo/fonts/OFL.txt`).
- Noto Sans Devanagari, SIL Open Font License 1.1.
