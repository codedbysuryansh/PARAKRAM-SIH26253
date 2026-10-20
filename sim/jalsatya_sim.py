"""JalSatya physics model (simulated sensor, literature parameters).

1. e-Strip: chronoamperometric reading of free chlorine on a 3 mm printed carbon electrode.
   i(t) = n F A C_HOCl sqrt(D / (pi t))   (Cottrell)   + double-layer charging + blank current + noise
   A dried buffer pad holds the sample near pH 5.5, so almost all free chlorine is HOCl.
2. Proof-of-Test: a real reading leaves a Cottrell-shaped trace; typed, flat, copied or synthetic traces fail.
3. Village chlorine twin: first-order chlorine decay along pipe travel time; dose window that keeps every tap
   between 0.2 mg/L (JJM acceptable) and 1.0 mg/L (JJM permissible).

Every number this script prints is a model output and must be labelled "simulated" wherever it is shown.
"""
import json, math, os
import numpy as np

rng = np.random.default_rng(20261020)
OUT = os.path.dirname(os.path.abspath(__file__))

F, n = 96485.0, 2
R_ELEC = 1.5e-3                     # 3 mm working electrode
A0 = math.pi * R_ELEC ** 2          # m2
D_HOCL = 1.6e-9                     # m2/s, literature order of magnitude
M_CL2 = 70.906                      # g/mol, chlorine reported as Cl2
T_S = np.arange(0.05, 5.0001, 0.05) # 100 samples over 5 s
BLANK_NA, NOISE_NA = 2.0, 0.8       # blank current and per-sample noise (nA)
BLANK_SD = 4.0                      # strip-to-strip blank variation (nA)
TEMP_RESID = 0.01                   # 1 % residual error after on-reader temperature compensation
STRIP_CV = 0.03                     # strip-to-strip area variation (3 %)


def pka(temp_c=25.0):
    t = temp_c + 273.15
    return 3000.0 / t - 10.0686 + 0.0253 * t          # Morris (1966)


def hocl_fraction(ph, temp_c=25.0):
    return 1.0 / (1.0 + 10 ** (ph - pka(temp_c)))


def trace(c_mgl, ph_sample=7.5, buffered=True, temp_c=25.0, strip_area=None, gen=None):
    """Simulated current transient in nA. Noise terms: strip area spread, residual temperature error on D,
    a per-strip blank offset, and white measurement noise."""
    g = gen if gen is not None else rng
    a = strip_area if strip_area is not None else A0 * (1 + STRIP_CV * g.standard_normal())
    ph = 5.5 if buffered else ph_sample
    c_hocl = c_mgl / M_CL2 * hocl_fraction(ph, temp_c)          # mol/m3
    d = D_HOCL * (1 + TEMP_RESID * g.standard_normal())
    i_far = n * F * a * c_hocl * np.sqrt(d / (math.pi * T_S)) * 1e9
    i_cap = 1500.0 * np.exp(-T_S / 0.04)                          # charging spike, nA
    blank = (BLANK_NA + BLANK_SD * g.standard_normal()) * (T_S ** -0.5)  # blank decays like a transient too
    return i_far + i_cap + blank + NOISE_NA * g.standard_normal(T_S.size)


def cottrell_slope(i_na):
    """Least-squares fit i = a * t^-1/2 + b over 1-5 s; returns a, b, r2."""
    m = T_S >= 1.0
    x, y = T_S[m] ** -0.5, i_na[m]
    X = np.vstack([x, np.ones_like(x)]).T
    (a, b), *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ np.array([a, b])
    r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2) if np.var(y) > 0 else 0.0
    return a, b, r2


def calibrate():
    levels = [0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    xs, ys = [], []
    for c in levels:
        for _ in range(40):
            a, _, _ = cottrell_slope(trace(c))
            xs.append(c); ys.append(a)
    k, b0 = np.polyfit(xs, ys, 1)
    blanks = [cottrell_slope(trace(0.0))[0] for _ in range(200)]
    lod = 3 * np.std(blanks) / k
    loq = 10 * np.std(blanks) / k
    # independent test set over the working range
    true = rng.uniform(0, 2, 2000)
    pred = np.array([(cottrell_slope(trace(c))[0] - b0) / k for c in true])
    err = pred - true
    return dict(levels=levels, slope_nA_per_mgL=k, intercept=b0, lod_mgL=lod, loq_mgL=loq,
                mae_mgL=float(np.mean(np.abs(err))), rmse_mgL=float(np.sqrt(np.mean(err ** 2))),
                within_005=float(np.mean(np.abs(err) <= 0.05)), within_01=float(np.mean(np.abs(err) <= 0.10)),
                cal_points=[[float(x), float(y)] for x, y in zip(xs[::8], ys[::8])])


def ph_robustness(k, b0):
    """A 0.50 mg/L sample read across pH. 'buffered' is the JalSatya strip; 'unbuffered' is the same electrode
    without its pad, read with the strip's calibration; 'bare_ph7cal' is a bare electrode calibrated in pH 7 water,
    the fairer comparison for a meter without a buffer (own random stream, so other results are unchanged)."""
    g2 = np.random.default_rng(7)
    xs, ys = [], []
    for c in [0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]:
        for _ in range(40):
            xs.append(c); ys.append(cottrell_slope(trace(c, 7.0, False, gen=g2))[0])
    k7, b7 = np.polyfit(xs, ys, 1)
    rows = []
    for ph in [6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]:
        r = {}
        for buffered in (True, False):
            p = np.mean([(cottrell_slope(trace(0.5, ph, buffered))[0] - b0) / k for _ in range(60)])
            r['buffered' if buffered else 'unbuffered'] = float(p)
        r['bare_ph7cal'] = float(np.mean([(cottrell_slope(trace(0.5, ph, False, gen=g2))[0] - b7) / k7
                                          for _ in range(60)]))
        rows.append(dict(ph=ph, **r))
    return rows


def proof_of_test(k, b0, n_each=400):
    """Layer 1: one strip, one test (serial + one-time code). Layer 2: the reader signs the raw trace.
    Layer 3: the trace must look like a real electrode transient (power-law decay near t^-1/2)."""
    def physics_ok(i_na):
        if i_na is None or len(i_na) != T_S.size or np.max(i_na[:3]) < 200:
            return False
        m = T_S >= 1.0
        a, b, r2 = cottrell_slope(i_na)
        if a < 15:                      # below ~0.03 mg/L: must look like a blank
            return np.std(i_na[m]) < 6
        beta = np.polyfit(np.log(T_S[m]), np.log(np.clip(i_na[m], 1e-3, None)), 1)[0]
        return -0.62 < beta < -0.40 and abs(b) < 8 and r2 > 0.9

    used, sigs = set(), set()
    def submit(rec):
        if rec['strip'] in used:
            return False                # strip already used
        used.add(rec['strip'])          # a strip is spent the moment it is read, pass or fail
        if not rec['signed']:
            return False                # not signed by a registered reader
        if rec['trace'] is not None and hash(np.round(rec['trace'], 1).tobytes()) in sigs:
            return False                # copied trace
        if not physics_ok(rec['trace']):
            return False
        sigs.add(hash(np.round(rec['trace'], 1).tobytes()))
        return True

    res = {}
    real = []
    for j in range(n_each):
        real.append(dict(strip=f'S{j}', signed=True, trace=trace(rng.uniform(0, 2))))
    res['real tests accepted'] = float(np.mean([submit(r) for r in real]))
    fakes = {
        'typed number, no trace': [dict(strip=f'T{j}', signed=False, trace=None) for j in range(n_each)],
        'same strip used twice': [dict(strip=real[j]['strip'], signed=True, trace=trace(0.5)) for j in range(n_each)],
        'copied trace on a new strip': [dict(strip=f'C{j}', signed=True, trace=real[j]['trace'].copy()) for j in range(n_each)],
        'invented curve, unsigned': [dict(strip=f'U{j}', signed=False, trace=trace(0.6)) for j in range(n_each)],
        'invented curve from a tampered reader': [dict(strip=f'E{j}', signed=True,
            trace=1500 * np.exp(-T_S / 0.04) + rng.uniform(40, 400) * np.exp(-T_S / rng.uniform(0.8, 3)) + 2 + 0.8 * rng.standard_normal(T_S.size)) for j in range(n_each)],
    }
    for name, arr in fakes.items():
        res[name + ' rejected'] = float(np.mean([not submit(r) for r in arr]))
    return res


def village_twin():
    """The sample 120-tap scheme shown in the demo (sim/village.json, exported from demo/model.js buildVillage).
    Chlorine decays first-order with water age. The twin learns the decay rate from five verified tests
    (the two tail-end taps plus three others) and computes the dose window that keeps every tap in range."""
    with open(os.path.join(OUT, 'village.json')) as f:
        age = np.array([t['age_h'] for t in json.load(f)['taps']])
    taps = int(age.size)
    k_true, demand = 0.05, 0.40                                    # decay (1/h) and immediate demand (mg/L)

    def frc(dose, k=k_true):
        return np.clip(dose - demand, 0, None) * np.exp(-k * age)

    def n_safe(v):
        return int(np.sum((v >= 0.2) & (v <= 1.0)))

    habit = 1.0                                                     # the operator's usual dose
    order = np.argsort(age)
    idx = np.r_[order[-2:], rng.choice(order[:-10], 3, replace=False)]
    obs = frc(habit)[idx] + 0.03 * rng.standard_normal(idx.size)    # five noisy verified readings
    ks = np.linspace(0.01, 0.15, 281)
    sse = [np.sum((frc(habit, kk)[idx] - obs) ** 2) for kk in ks]
    k_hat = float(ks[int(np.argmin(sse))])
    lo = demand + 0.2 * math.exp(k_hat * age.max())                # farthest tap stays >= 0.2
    hi = demand + 1.0 * math.exp(k_hat * age.min())                # nearest tap stays <= 1.0
    rec = round(lo + 0.35 * (hi - lo), 2)                          # inside the window, nearer the safe floor
    at_habit, at_rec = frc(habit), frc(rec)
    return dict(taps=taps, farthest_h=float(age.max()), nearest_h=float(age.min()), k_true=k_true,
                k_learned=k_hat, tests_used=int(idx.size), habit_dose=habit,
                habit_safe=n_safe(at_habit), habit_below_02=int(np.sum(at_habit < 0.2)),
                habit_tail=float(at_habit[order[-1]]), recommended_dose=rec,
                dose_window=[round(lo, 3), round(hi, 3)], twin_safe=n_safe(at_rec),
                twin_tail=float(at_rec[order[-1]]), twin_range=[float(at_rec.min()), float(at_rec.max())])


if __name__ == "__main__":
    cal = calibrate()
    phr = ph_robustness(cal['slope_nA_per_mgL'], cal['intercept'])
    pot = proof_of_test(cal['slope_nA_per_mgL'], cal['intercept'])
    tw = village_twin()
    sample = {str(c): [round(float(v), 2) for v in trace(c)] for c in (0.0, 0.32, 1.2)}
    res = dict(calibration=cal, ph=phr, proof=pot, twin=tw, t_s=[round(float(t), 2) for t in T_S],
               sample_traces=sample, pka_25C=pka(25.0),
               hocl_frac={'5.5': hocl_fraction(5.5), '7.5': hocl_fraction(7.5), '8.5': hocl_fraction(8.5)})
    with open(os.path.join(OUT, 'results.json'), 'w') as f:
        json.dump(res, f, indent=1)
    c = cal
    print(f"slope {c['slope_nA_per_mgL']:.1f} nA per mg/L | LOD {c['lod_mgL']:.3f} | LOQ {c['loq_mgL']:.3f} mg/L")
    print(f"MAE {c['mae_mgL']:.3f} | RMSE {c['rmse_mgL']:.3f} | within 0.05 {c['within_005']:.1%} | within 0.1 {c['within_01']:.1%}")
    print("pH (true 0.5 mg/L):", [(r['ph'], round(r['buffered'], 3), round(r['unbuffered'], 3), round(r['bare_ph7cal'], 3)) for r in phr])
    print("proof:", {k: round(v, 3) for k, v in pot.items()})
    print("twin:", tw)
    print("HOCl fraction:", res['hocl_frac'], 'pKa', round(res['pka_25C'], 3))
