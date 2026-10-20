/* JalSatya physics model (simulated sensor, literature parameters). Mirrors sim/jalsatya_sim.py. */
(function (global) {
  "use strict";

  // ---------- seeded random ----------
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  let rand = mulberry32(20261020);
  function gauss() {
    let u = 0, v = 0;
    while (u === 0) u = rand();
    while (v === 0) v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  // ---------- constants ----------
  const F = 96485, N_E = 2;
  const R_ELEC = 1.5e-3, A0 = Math.PI * R_ELEC * R_ELEC;
  const D_HOCL = 1.6e-9, M_CL2 = 70.906;
  const BLANK = 2.0, BLANK_SD = 4.0, NOISE = 0.8, STRIP_CV = 0.03, TEMP_RESID = 0.01;
  const T = []; for (let i = 1; i <= 100; i++) T.push(+(i * 0.05).toFixed(2));
  // calibration produced by sim/jalsatya_sim.py
  const CAL = { slope: 430.29, intercept: 1.967, lod: 0.027, loq: 0.090, mae: 0.026, within01: 0.981 };

  function pKa(tc) { const t = tc + 273.15; return 3000 / t - 10.0686 + 0.0253 * t; }
  function hoclFraction(ph, tc) { return 1 / (1 + Math.pow(10, ph - pKa(tc == null ? 25 : tc))); }

  function trace(cMgL, opts) {
    opts = opts || {};
    const buffered = opts.buffered !== false;
    const ph = buffered ? 5.5 : (opts.ph == null ? 7.5 : opts.ph);
    const a = A0 * (1 + STRIP_CV * gauss());
    const d = D_HOCL * (1 + TEMP_RESID * gauss());
    const cHocl = (cMgL / M_CL2) * hoclFraction(ph, opts.temp);   // mol per m3
    const blank = BLANK + BLANK_SD * gauss();
    return T.map(t => {
      const iFar = N_E * F * a * cHocl * Math.sqrt(d / (Math.PI * t)) * 1e9;   // nA
      const iCap = 1500 * Math.exp(-t / 0.04);
      return iFar + iCap + blank * Math.pow(t, -0.5) + NOISE * gauss();
    });
  }

  function cottrellFit(i) {
    // least squares i = a t^-1/2 + b over 1..5 s
    let sx = 0, sy = 0, sxx = 0, sxy = 0, n = 0;
    for (let k = 0; k < T.length; k++) if (T[k] >= 1) { const x = Math.pow(T[k], -0.5); sx += x; sy += i[k]; sxx += x * x; sxy += x * i[k]; n++; }
    const a = (n * sxy - sx * sy) / (n * sxx - sx * sx);
    const b = (sy - a * sx) / n;
    let ssr = 0, sst = 0; const mean = sy / n;
    for (let k = 0; k < T.length; k++) if (T[k] >= 1) { const p = a * Math.pow(T[k], -0.5) + b; ssr += (i[k] - p) ** 2; sst += (i[k] - mean) ** 2; }
    return { a, b, r2: sst > 0 ? 1 - ssr / sst : 0 };
  }

  function readMgL(i) { return Math.max(0, (cottrellFit(i).a - CAL.intercept) / CAL.slope); }

  function powerExponent(i) {
    let sx = 0, sy = 0, sxx = 0, sxy = 0, n = 0;
    for (let k = 0; k < T.length; k++) if (T[k] >= 1) { const x = Math.log(T[k]); const y = Math.log(Math.max(i[k], 1e-3)); sx += x; sy += y; sxx += x * x; sxy += x * y; n++; }
    return (n * sxy - sx * sy) / (n * sxx - sx * sx);
  }

  function physicsOk(i) {
    if (!i || i.length !== T.length) return { ok: false, why: "No electrode signal was recorded." };
    if (Math.max(i[0], i[1], i[2]) < 200) return { ok: false, why: "No switch-on spike, so no strip was connected." };
    const f = cottrellFit(i);
    if (f.a < 15) return { ok: true, why: "Blank-level reading." };
    const beta = powerExponent(i);
    if (!(beta > -0.62 && beta < -0.40) || Math.abs(f.b) > 8 || f.r2 < 0.9)
      return { ok: false, why: "The curve decays as t^" + beta.toFixed(2) + ". A real strip decays as t^-0.50." };
    return { ok: true, why: "Curve matches a real electrode transient." };
  }

  function fingerprint(i) {
    // short, readable fingerprint of the rounded trace (FNV-1a)
    let h = 0x811c9dc5;
    const s = i.map(v => v.toFixed(1)).join(",");
    for (let k = 0; k < s.length; k++) { h ^= s.charCodeAt(k); h = Math.imul(h, 0x01000193) >>> 0; }
    let h2 = 0x01234567;
    for (let k = s.length - 1; k >= 0; k--) { h2 ^= s.charCodeAt(k); h2 = Math.imul(h2, 0x01000193) >>> 0; }
    const hex = (h.toString(16).padStart(8, "0") + h2.toString(16).padStart(8, "0")).slice(0, 12);
    return hex.slice(0, 4) + " " + hex.slice(4, 8) + " " + hex.slice(8, 12);
  }

  // ---------- village twin ----------
  function buildVillage() {
    const r = mulberry32(7);
    const tank = { x: 120, y: 92 };
    const nodes = [], pipes = [];
    // a trunk with branches; each tap gets water age from storage + pipe distance
    const trunk = [[120, 92], [210, 150], [330, 190], [470, 230], [600, 300], [710, 380], [790, 470]];
    for (let k = 1; k < trunk.length; k++) pipes.push({ a: trunk[k - 1], b: trunk[k], main: true });
    const branchDefs = [];
    for (let k = 1; k < trunk.length; k++) {
      const [x, y] = trunk[k];
      const dirs = k % 2 ? [[-1, 1.1], [1, -0.9]] : [[1, 0.9], [-1, 1.2]];
      dirs.forEach((d, j) => branchDefs.push({ start: [x, y], dir: d, len: 120 + r() * 110, k, j }));
    }
    let id = 1;
    const cum = [0]; for (let k = 1; k < trunk.length; k++) cum.push(cum[k - 1] + Math.hypot(trunk[k][0] - trunk[k - 1][0], trunk[k][1] - trunk[k - 1][1]));
    branchDefs.forEach(bd => {
      const [sx, sy] = bd.start; const dl = Math.hypot(bd.dir[0], bd.dir[1]);
      const ux = bd.dir[0] / dl, uy = bd.dir[1] / dl;
      const ex = sx + ux * bd.len, ey = sy + uy * bd.len;
      pipes.push({ a: [sx, sy], b: [ex, ey], main: false });
      const taps = 10;
      for (let t = 1; t <= taps; t++) {
        const f = t / taps;
        const px = sx + ux * bd.len * f + (r() - 0.5) * 18 + (uy) * (t % 2 ? 16 : -16);
        const py = sy + uy * bd.len * f + (r() - 0.5) * 18 - (ux) * (t % 2 ? 16 : -16);
        const dist = cum[bd.k] + bd.len * f;
        nodes.push({ id: "T-" + String(id).padStart(3, "0"), x: px, y: py, dist });
        id++;
      }
    });
    nodes.splice(120);
    const maxD = Math.max(...nodes.map(n => n.dist));
    nodes.forEach(n => { n.age = 2.5 + 21.5 * Math.pow(n.dist / maxD, 1.15); });   // hours: storage plus pipe
    return { tank, trunk, pipes, nodes };
  }

  // kLearned, window and rec come from sim/jalsatya_sim.py village_twin() on this same village (sim/results.json)
  const TWIN = { kTrue: 0.05, demand: 0.40, kLearned: 0.049, window: [1.048, 1.648], rec: 1.26 };
  function frcAt(dose, age, k) { return Math.max(0, dose - TWIN.demand) * Math.exp(-(k == null ? TWIN.kTrue : k) * age); }
  function doseWindow(nodes, k) {
    const maxAge = Math.max(...nodes.map(n => n.age)), minAge = Math.min(...nodes.map(n => n.age));
    const lo = TWIN.demand + 0.2 * Math.exp(k * maxAge);
    const hi = TWIN.demand + 1.0 * Math.exp(k * minAge);
    return [lo, hi];
  }

  global.JS = { T, CAL, TWIN, trace, cottrellFit, readMgL, physicsOk, fingerprint, hoclFraction, pKa, buildVillage, frcAt, doseWindow, gauss, reseed: s => { rand = mulberry32(s); } };
})(window);
