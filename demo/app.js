(function () {
  "use strict";
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const C = { ink: "#13315c", tap: "#2f7fc1", safe: "#1f8a5b", low: "#c8412d", high: "#d28a12", muted: "#5b6676", line: "#e8edf1", text: "#1d2633" };
  const FONT = "Barlow, 'Noto Sans Devanagari', sans-serif";
  const axisStyle = {
    axisLine: { lineStyle: { color: "#c9d3dc" } }, axisTick: { show: false },
    axisLabel: { color: C.muted, fontFamily: FONT, fontSize: 12 },
    splitLine: { lineStyle: { color: C.line } }, nameTextStyle: { color: C.muted, fontFamily: FONT, fontSize: 12 }
  };
  function status(v) { return v < 0.2 ? "low" : v > 1.0 ? "high" : "safe"; }
  function colorFor(v) { return C[status(v)]; }

  // ---------------- tabs ----------------
  const charts = {};
  $$(".tabs button").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
  function showView(v) {
    $$(".tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.view === v ? "true" : "false"));
    $$(".view").forEach(s => s.classList.toggle("active", s.id === "view-" + v));
    if (history.replaceState) history.replaceState(null, "", "#" + v);
    setTimeout(() => Object.values(charts).forEach(c => c && c.resize()), 30);
    if (v === "lab") initLab();
    if (v === "twin") initTwin();
    if (v === "district") initDistrict();
  }

  // ---------------- i18n (field app) ----------------
  const HI = {
    village: "सोनपुर ग्राम पंचायत", reader: "रीडर R-0417 जुड़ा है", hello: "नमस्ते, सुनीता",
    todayTests: "इस महीने: 2 अंतिम छोर के नल और 1 स्रोत की जाँच।", nextTap: "अगला: नल T-118, वार्ड 6",
    nextTapWhy: "लाइन का सबसे दूर का नल, जैसा JJM ढांचा कहता है।", stripsLeft: "आपके पास स्ट्रिप", lastSync: "पिछला अपलोड",
    lastSyncV: "आज, 08:10", start: "जाँच शुरू करें", scanH: "स्ट्रिप स्कैन करें", scanP: "स्ट्रिप का कोड फ्रेम के अंदर रखें।",
    stripOk: "स्ट्रिप JS-26-0019-4471 मान्य है", stripOkSub: "सोनपुर GP को जारी, अप्रयुक्त, मार्च 2027 तक", next: "आगे",
    dipH: "स्ट्रिप को नल के पानी में डुबोएं", dipP: "नल T-118 से कप भरें और काला सिरा 3 सेकंड डुबोएं।", dipped: "डुबोएं और पढ़ें",
    readingH: "स्ट्रिप पढ़ी जा रही है", readingP: "स्ट्रिप स्थिर रखें। 5 सेकंड लगेंगे।", seconds: "सेकंड",
    safe: "सुरक्षित। क्लोरीन JJM सीमा में है।", low: "क्लोरीन कम है। पंप ऑपरेटर को सूचना भेजी गई।", high: "क्लोरीन ज़्यादा है। खुराक घटाने की सलाह भेजी गई।",
    kvStrip: "स्ट्रिप", kvPlace: "स्थान", kvTime: "समय", kvSig: "सिग्नल पहचान", queued: "रीडर R-0417 द्वारा हस्ताक्षरित। ऑनलाइन होते ही WQMIS पर जाएगा।", done: "पूरा हुआ", app: "जलसत्य",
    voice: "आवाज़"
  };
  const EN = {};
  $$("[data-i18n]").forEach(el => { EN[el.dataset.i18n] = el.textContent; });
  EN.low = "Low chlorine. The pump operator has been alerted."; EN.high = "Too much chlorine. Dose cut advised to the operator.";
  let lang = "en";
  $$(".lang button").forEach(b => b.addEventListener("click", () => {
    lang = b.dataset.lang;
    $$(".lang button").forEach(x => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
    $$("[data-i18n]").forEach(el => { const k = el.dataset.i18n; const dict = lang === "hi" ? HI : EN; if (dict[k]) el.textContent = dict[k]; });
    $(".screen").style.fontFamily = lang === "hi" ? "var(--hi)" : "";
    if (lastResult != null) setVerdict(lastResult);
  }));
  function tr(k) { return (lang === "hi" ? HI : EN)[k] || EN[k] || k; }

  // ---------------- voice prompts for the tester (browser speech, off until switched on) ----------------
  let voiceOn = false;
  const vbtn = $("#voiceBtn");
  const canSpeak = "speechSynthesis" in window && typeof SpeechSynthesisUtterance !== "undefined";
  if (vbtn && !canSpeak) vbtn.hidden = true;
  if (vbtn) vbtn.addEventListener("click", () => {
    voiceOn = !voiceOn;
    vbtn.setAttribute("aria-pressed", voiceOn ? "true" : "false");
    if (voiceOn) say(lang === "hi" ? "आवाज़ चालू है।" : "Voice prompts are on."); else window.speechSynthesis.cancel();
  });
  function pickVoice(want) {
    const vs = window.speechSynthesis.getVoices() || [];
    const low = s => (s || "").toLowerCase().replace("_", "-");
    return vs.find(v => low(v.lang) === want) || vs.find(v => low(v.lang).startsWith(want.slice(0, 2))) || null;
  }
  function say(text) {
    if (!voiceOn || !canSpeak || !text) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = lang === "hi" ? "hi-IN" : "en-IN";
      const v = pickVoice(u.lang.toLowerCase());
      if (v) u.voice = v;
      u.rate = lang === "hi" ? 0.92 : 0.98;
      window.speechSynthesis.speak(u);
    } catch (e) { /* speech is a convenience; the screen still shows every prompt */ }
  }
  function spokenResult(v) {
    const n = v.toFixed(2);
    return lang === "hi" ? `${n} मिलीग्राम प्रति लीटर। ${tr(status(v))}` : `${n} milligrams per litre. ${tr(status(v))}`;
  }

  // ---------------- QR on strip ----------------
  (function drawQr() {
    const g = document.getElementById("qr"); const r = mulberry(19); let s = "";
    for (let y = 0; y < 9; y++) for (let x = 0; x < 9; x++) {
      const finder = (x < 3 && y < 3) || (x > 5 && y < 3) || (x < 3 && y > 5);
      if (finder ? !(x % 3 === 1 && y % 3 === 1) : r() > 0.5) s += `<rect x="${152 + x * 6}" y="${5 + y * 5.4}" width="6" height="5.4" fill="#1d2633"/>`;
    }
    g.innerHTML = s;
  })();
  function mulberry(a) { return function () { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  // ---------------- test flow ----------------
  const TRUE_FRC = 0.32;
  let lastResult = null, lastTrace = null, lastPrint = null, stripUsed = false, reading = false;
  const panes = $$(".pane");
  function go(n) {
    panes.forEach(p => p.classList.toggle("on", +p.dataset.pane === n));
    if (n === 1) {
      $("#scanOk").hidden = true; $("#scanNext").disabled = true;
      setTimeout(() => { $("#scanOk").hidden = false; $("#scanNext").disabled = false; }, 1300);
      say(tr("scanP"));
    }
    if (n === 2) { $("#dipStrip").classList.remove("down"); say(tr("dipP")); }
    if (n === 3) say(tr("readingP"));
  }
  $$("[data-next]").forEach(b => b.addEventListener("click", () => go(+b.dataset.next)));
  $("#dipBtn").addEventListener("click", () => {
    if (reading) return;
    $("#dipStrip").classList.add("down");
    setTimeout(() => { go(3); startReading(); }, 950);
  });

  charts.trace = echarts.init($("#traceChart"), null, { renderer: "canvas" });
  const baseTrace = {
    animation: false,
    grid: { left: 64, right: 24, top: 18, bottom: 46 },
    xAxis: Object.assign({ type: "value", min: 0, max: 5, name: "Time after dipping (s)", nameLocation: "middle", nameGap: 30 }, axisStyle),
    yAxis: Object.assign({ type: "value", min: 0, max: 450, name: "Current (nA)", nameLocation: "middle", nameGap: 46 }, axisStyle),
    series: [
      { name: "strip", type: "line", showSymbol: false, smooth: false, data: [], lineStyle: { color: C.tap, width: 2.4 }, areaStyle: { color: "rgba(47,127,193,0.08)" } },
      { name: "fit", type: "line", showSymbol: false, data: [], lineStyle: { color: C.ink, width: 1.5, type: "dashed" } },
      { name: "fake", type: "line", showSymbol: false, data: [], lineStyle: { color: C.low, width: 2, type: "dotted" } }
    ]
  };
  baseTrace.graphic = [{ id: "hint", type: "text", left: "center", top: "middle", style: { text: "Dip a strip to see its signal here", fill: "#9aa7b4", font: "600 16px Barlow" } }];
  charts.trace.setOption(baseTrace);
  window.addEventListener("resize", () => Object.values(charts).forEach(c => c && c.resize()));

  function startReading() {
    reading = true;
    JS.reseed(Date.now() % 100000);
    const tr0 = JS.trace(TRUE_FRC);
    const t0 = performance.now(), dur = 5000;
    const arc = $("#ringArc"), sec = $("#ringSec"), live = $("#liveVal");
    charts.trace.setOption({ graphic: [{ id: "hint", $action: "remove" }], series: [{ data: [] }, { data: [] }, { data: [] }] });
    (function frame(now) {
      const el = Math.min(dur, now - t0), tNow = el / 1000;
      arc.setAttribute("stroke-dashoffset", (276.5 * (1 - el / dur)).toFixed(1));
      sec.textContent = tNow.toFixed(1);
      const pts = [];
      for (let k = 0; k < JS.T.length && JS.T[k] <= tNow; k++) pts.push([JS.T[k], Math.min(450, tr0[k])]);
      charts.trace.setOption({ series: [{ data: pts }] });
      if (tNow > 1.2) {
        const partial = tr0.map((v, k) => (JS.T[k] <= tNow ? v : null)).filter(v => v !== null);
        const est = estimatePartial(partial);
        live.innerHTML = est.toFixed(2) + "<small>mg/L</small>";
      }
      if (el < dur) requestAnimationFrame(frame); else finishReading(tr0);
    })(t0);
  }
  function estimatePartial(arr) {
    let sx = 0, sy = 0, sxx = 0, sxy = 0, n = 0;
    for (let k = 0; k < arr.length; k++) { const t = JS.T[k]; if (t < 1) continue; const x = Math.pow(t, -0.5); sx += x; sy += arr[k]; sxx += x * x; sxy += x * arr[k]; n++; }
    if (n < 3) return 0;
    const a = (n * sxy - sx * sy) / (n * sxx - sx * sx);
    return Math.max(0, (a - JS.CAL.intercept) / JS.CAL.slope);
  }
  function finishReading(trc) {
    reading = false;
    const v = JS.readMgL(trc);
    const f = JS.cottrellFit(trc);
    charts.trace.setOption({ series: [{}, { data: JS.T.filter(t => t >= 0.6).map(t => [t, f.a * Math.pow(t, -0.5) + f.b]) }] });
    lastResult = v; lastTrace = trc; lastPrint = JS.fingerprint(trc); stripUsed = false;
    $("#resV").textContent = v.toFixed(2);
    $("#liveVal").innerHTML = v.toFixed(2) + "<small>mg/L</small>";
    $("#recHash").textContent = lastPrint;
    const d = new Date(); $("#recTime").textContent = d.toLocaleDateString("en-IN", { day: "numeric", month: "short" }) + ", " + d.toTimeString().slice(0, 5);
    setVerdict(v);
    $("#resPin").style.left = Math.min(98, v / 2 * 100) + "%";
    go(4);
    say(spokenResult(v));
    stripUsed = true;
    $("#cheatReuse").disabled = false; $("#cheatCopy").disabled = false;
    addVerdict(true, "Accepted", "Strip JS-26-0019-4471, first use, curve signed by reader R-0417. Reading " + v.toFixed(2) + " mg/L.");
  }
  function setVerdict(v) {
    const s = status(v), el = $("#resVerdict");
    el.className = "verdict " + s; el.textContent = tr(s);
  }
  function addVerdict(ok, head, text) {
    const row = document.createElement("div");
    row.className = "vrow " + (ok ? "ok" : "no");
    row.innerHTML = `<b>${head}</b><span>${text}</span>`;
    const box = $("#verdicts"); box.prepend(row);
    while (box.children.length > 5) box.lastChild.remove();
  }
  $("#cheatReuse").addEventListener("click", () => addVerdict(false, "Refused", "Strip JS-26-0019-4471 was already read today at " + $("#recTime").textContent.split(", ")[1] + ". A strip works once."));
  $("#cheatTyped").addEventListener("click", () => addVerdict(false, "Refused", "A typed value has no electrode curve and no reader signature, so it never reaches WQMIS."));
  $("#cheatCopy").addEventListener("click", () => addVerdict(false, "Refused", "Signal fingerprint " + lastPrint + " already belongs to an earlier test. Copies are caught."));
  $("#cheatInvent").addEventListener("click", () => {
    const fake = JS.T.map(t => 1500 * Math.exp(-t / 0.04) + 230 * Math.exp(-t / 1.6) + 2 + 0.8 * JS.gauss());
    const check = JS.physicsOk(fake);
    charts.trace.setOption({ series: [{}, {}, { data: JS.T.map((t, k) => [t, Math.min(450, fake[k])]) }] });
    addVerdict(false, "Refused", "Not signed by a registered reader. " + check.why);
  });

  // ---------------- strip lab ----------------
  let labReady = false;
  function initLab() {
    if (labReady) { charts.ph.resize(); charts.cal.resize(); return; }
    labReady = true;
    $("#labLod").textContent = JS.CAL.lod.toFixed(3).replace(/0$/, "");
    $("#labWithin").textContent = Math.round(JS.CAL.within01 * 100) + "%";
    $("#stSlope").textContent = Math.round(JS.CAL.slope);
    $("#stLoq").textContent = JS.CAL.loq.toFixed(2);
    $("#stMae").textContent = JS.CAL.mae.toFixed(3);
    charts.ph = echarts.init($("#phChart"));
    charts.cal = echarts.init($("#calChart"));
    // calibration scatter from fresh simulated strips
    JS.reseed(4242);
    const levels = [0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0], pts = [];
    levels.forEach(c => { for (let k = 0; k < 14; k++) pts.push([c + (Math.random() - 0.5) * 0.02, JS.readMgL(JS.trace(c))]); });
    charts.cal.setOption({
      animationDuration: 700,
      grid: { left: 58, right: 20, top: 16, bottom: 44 },
      xAxis: Object.assign({ type: "value", min: 0, max: 2.1, name: "True chlorine (mg/L)", nameLocation: "middle", nameGap: 28 }, axisStyle),
      yAxis: Object.assign({ type: "value", min: 0, max: 2.1, name: "JalSatya reading (mg/L)", nameLocation: "middle", nameGap: 40 }, axisStyle),
      series: [
        { type: "line", data: [[0, 0], [2.1, 2.1]], showSymbol: false, lineStyle: { color: C.ink, width: 1.5 } },
        { type: "scatter", data: pts, symbolSize: 6, itemStyle: { color: "rgba(47,127,193,0.55)" } },
        { type: "line", markArea: { silent: true, itemStyle: { color: "rgba(31,138,91,0.08)" }, data: [[{ xAxis: 0.2 }, { xAxis: 1.0 }]] }, data: [] }
      ]
    });
    const upd = () => {
      const c = +$("#cSlider").value, ph = +$("#phSlider").value;
      $("#cVal").textContent = c.toFixed(2) + " mg/L"; $("#phVal").textContent = ph.toFixed(1);
      JS.reseed(Math.round(c * 1000) + Math.round(ph * 10));
      const us = JS.readMgL(JS.trace(c));
      const bare = c * JS.hoclFraction(ph) / JS.hoclFraction(7.0);
      const band = c <= 0.2 ? "Low" : c < 1.1 ? "OK band" : "Excess";
      $("#usVal").textContent = us.toFixed(2);
      $("#bareVal").textContent = bare.toFixed(2);
      $("#eyeVal").textContent = c <= 0.2 ? "0 to 0.2" : c < 1.1 ? "0.2 to 1.1" : "above 1.1";
      setErr("#usErr", us, c); setErr("#bareErr", bare, c);
      $("#eyeErr").textContent = band + ", no number"; $("#eyeErr").style.color = C.muted;
      const phs = []; for (let p = 6; p <= 9.001; p += 0.1) phs.push(+p.toFixed(1));
      charts.ph.setOption({
        animationDurationUpdate: 300,
        grid: { left: 58, right: 20, top: 30, bottom: 44 },
        legend: { top: 0, right: 0, textStyle: { fontFamily: FONT, color: C.text }, itemWidth: 18 },
        xAxis: Object.assign({ type: "value", min: 6, max: 9, name: "Sample pH", nameLocation: "middle", nameGap: 28 }, axisStyle),
        yAxis: Object.assign({ type: "value", min: 0, max: Math.max(2.4, c * 1.4), name: "Reading (mg/L)", nameLocation: "middle", nameGap: 40 }, axisStyle),
        series: [
          { name: "JalSatya (buffered)", type: "line", showSymbol: false, data: phs.map(p => [p, c]), lineStyle: { color: C.ink, width: 2.6 }, itemStyle: { color: C.ink } },
          { name: "Bare electrode", type: "line", showSymbol: false, data: phs.map(p => [p, c * JS.hoclFraction(p) / JS.hoclFraction(7.0)]), lineStyle: { color: C.high, width: 2.2 }, itemStyle: { color: C.high } },
          { name: "True value", type: "line", showSymbol: false, data: [[6, c], [9, c]], lineStyle: { color: C.muted, width: 1, type: "dashed" }, itemStyle: { color: C.muted },
            markLine: { silent: true, symbol: "none", lineStyle: { color: C.tap, type: "solid", width: 1 }, label: { formatter: "your sample", color: C.tap, fontFamily: FONT }, data: [{ xAxis: ph }] } }
        ]
      });
    };
    function setErr(sel, v, c) {
      const e = c > 0.02 ? (v - c) / c * 100 : 0; const el = $(sel);
      el.textContent = (Math.abs(e) < 5 ? "within " : (e > 0 ? "+" : "")) + (Math.abs(e) < 5 ? "5%" : Math.round(e) + "%");
      el.style.color = Math.abs(e) < 10 ? C.safe : C.low;
    }
    $("#cSlider").addEventListener("input", upd); $("#phSlider").addEventListener("input", upd); upd();
  }

  // ---------------- village twin ----------------
  let twinReady = false, V = null, win = null;
  function initTwin() {
    if (twinReady) return;
    twinReady = true;
    V = JS.buildVillage();
    win = JS.doseWindow(V.nodes, JS.TWIN.kLearned);
    const rec = +(win[0] + (win[1] - win[0]) * 0.35).toFixed(2);
    JS.TWIN.rec = rec;
    $("#twFar").textContent = Math.round(Math.max(...V.nodes.map(n => n.age))) + " h";
    const svg = $("#villageMap"); let s = "";
    // fields and a road for context
    s += `<rect width="900" height="600" fill="#eef3ee"/>`;
    s += `<path d="M0 520 C 200 470, 380 560, 560 520 S 820 470, 900 500" fill="none" stroke="#d9e2d6" stroke-width="26"/>`;
    s += `<path d="M640 0 C 660 120, 610 200, 680 320 S 760 520, 740 600" fill="none" stroke="#cfdcea" stroke-width="18" opacity="0.8"/>`;
    V.pipes.forEach(p => { s += `<line x1="${p.a[0]}" y1="${p.a[1]}" x2="${p.b[0]}" y2="${p.b[1]}" stroke="${p.main ? "#7f93ab" : "#a8b7c7"}" stroke-width="${p.main ? 5 : 2.5}" stroke-linecap="round"/>`; });
    V.nodes.forEach((n, k) => { s += `<g class="tap" data-k="${k}"><circle cx="${n.x.toFixed(1)}" cy="${n.y.toFixed(1)}" r="7.5" fill="#1f8a5b" stroke="#fff" stroke-width="2"><title>${n.id}</title></circle></g>`; });
    s += `<g transform="translate(${V.tank.x - 26},${V.tank.y - 60})"><rect x="6" y="0" width="40" height="30" rx="4" fill="#13315c"/><rect x="14" y="30" width="4" height="26" fill="#13315c"/><rect x="34" y="30" width="4" height="26" fill="#13315c"/><text x="26" y="20" text-anchor="middle" font-family="Barlow" font-weight="700" font-size="11" fill="#fff">OHSR</text></g>`;
    s += `<text x="${V.tank.x + 30}" y="${V.tank.y - 36}" font-family="Barlow" font-size="14" fill="#13315c" font-weight="600">Tank, dosing point</text>`;
    s += `<g id="todoMarks"></g>`;
    svg.innerHTML = s;
    const lo = 0.4, hi = 2.2;
    $("#winOk").style.left = ((win[0] - lo) / (hi - lo) * 100) + "%";
    $("#winOk").style.width = ((win[1] - win[0]) / (hi - lo) * 100) + "%";
    const slider = $("#doseSlider");
    slider.addEventListener("input", () => paintTwin(+slider.value));
    $("#applyRec").addEventListener("click", () => animateDose(+slider.value, rec));
    $("#applyRec").textContent = "Use the recommended dose, " + rec.toFixed(2) + " mg/L";
    paintTwin(+slider.value);
    buildTodo(rec);
  }
  function paintTwin(dose) {
    const circles = $$("#villageMap .tap circle");
    let ok = 0, minV = 9, maxV = 0;
    V.nodes.forEach((n, k) => {
      const v = JS.frcAt(dose, n.age); if (v >= 0.2 && v <= 1.0) ok++;
      minV = Math.min(minV, v); maxV = Math.max(maxV, v);
      circles[k].setAttribute("fill", colorFor(v));
      circles[k].querySelector("title").textContent = n.id + ": " + v.toFixed(2) + " mg/L, water age " + n.age.toFixed(1) + " h";
    });
    $("#doseVal").innerHTML = dose.toFixed(2) + ' <small style="font-size:18px">mg/L</small>';
    $("#winCur").style.left = ((dose - 0.4) / 1.8 * 100) + "%";
    const sc = $("#safeCount"); sc.textContent = ok; $("#tapTotal").textContent = V.nodes.length; sc.style.color = ok === V.nodes.length ? C.safe : C.low;
    const bp = Math.round(50 * dose / 0.30);
    let note;
    if (dose < win[0]) note = `Farthest taps drop to ${minV.toFixed(2)} mg/L, below the 0.2 mg/L the framework requires.`;
    else if (dose > win[1]) note = `Taps near the tank reach ${maxV.toFixed(2)} mg/L, above the 1.0 mg/L limit. Families may stop drinking it.`;
    else note = `Every tap stays between ${minV.toFixed(2)} and ${maxV.toFixed(2)} mg/L. About ${bp} g of bleaching powder a day for 50,000 L.`;
    $("#doseNote").textContent = note;
  }
  function animateDose(from, to) {
    const t0 = performance.now(), dur = 900, sl = $("#doseSlider");
    (function f(now) { const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3); const v = from + (to - from) * e; sl.value = v; paintTwin(v); if (p < 1) requestAnimationFrame(f); })(t0);
  }
  function buildTodo(rec) {
    const byAge = V.nodes.map((n, k) => ({ n, k })).sort((a, b) => b.n.age - a.n.age);
    const picks = [byAge[0], byAge[1]];
    // most uncertain: largest prediction spread if decay were 20% off
    const unc = V.nodes.map((n, k) => ({ n, k, u: Math.abs(JS.frcAt(rec, n.age, JS.TWIN.kLearned * 1.2) - JS.frcAt(rec, n.age, JS.TWIN.kLearned * 0.8)) }))
      .filter(o => !picks.some(p => p.k === o.k)).sort((a, b) => b.u - a.u);
    // choose an uncertain tap on a different branch than the tail ends
    const third = unc.find(o => Math.hypot(o.n.x - picks[0].n.x, o.n.y - picks[0].n.y) > 120) || unc[0];
    picks.push(third);
    const why = ["Tail end, farthest water", "Second tail end", "Model least certain here"];
    $("#todo").innerHTML = picks.map((p, i) => `<li><b>${p.n.id}</b><span>${why[i]}. Expected ${JS.frcAt(rec, p.n.age).toFixed(2)} mg/L at the recommended dose.</span></li>`).join("");
    $("#todoMarks").innerHTML = picks.map(p => `<circle cx="${p.n.x.toFixed(1)}" cy="${p.n.y.toFixed(1)}" r="14" fill="none" stroke="#13315c" stroke-width="2.5" stroke-dasharray="4 3"/>`).join("");
  }

  // ---------------- district ----------------
  let distReady = false;
  function initDistrict() {
    if (distReady) { charts.d.resize(); return; }
    distReady = true;
    const rows = [
      ["Sonpur", 30, 29, 0, 0.31], ["Khedi Buzurg", 30, 30, 0, 0.27], ["Bhawanipur", 30, 26, 2, 0.12],
      ["Rajnagar", 40, 37, 1, 0.44], ["Nayagaon", 30, 18, 11, 0.24], ["Dharampur", 20, 20, 0, 0.36],
      ["Kesarpura", 30, 28, 0, 1.16], ["Ambavadi", 40, 39, 0, 0.29], ["Shivgarh", 30, 27, 3, 0.18], ["Ratanpur", 20, 19, 0, 0.52]
    ];
    const tests = rows.reduce((s, r) => s + r[2], 0), blocked = rows.reduce((s, r) => s + r[3], 0), low = rows.filter(r => r[4] < 0.2).length;
    countUp($("#dTests"), tests); countUp($("#dBlocked"), blocked); countUp($("#dLow"), low);
    $("#dRows").innerHTML = rows.map(r => {
      const s = status(r[4]); const label = s === "safe" ? "In range" : s === "low" ? "Below 0.2" : "Above 1.0";
      return `<tr class="${r[3] >= 10 ? "flag" : ""}"><td>${r[0]}</td><td class="num">${r[1]}</td><td class="num">${r[2]}</td><td class="num">${r[3]}</td><td class="num">${r[4].toFixed(2)}</td><td><span class="pill ${s}">${label}</span></td></tr>`;
    }).join("");
    $("#dAlerts").innerHTML = `
      <div class="alert"><b>Nayagaon: 11 records refused</b><p>The paper register shows 29 tests, but only 18 came with a valid strip and a signed curve. The 11 extra entries never reach WQMIS.</p></div>
      <div class="alert" style="border-left-color:var(--low)"><b>Bhawanipur and Shivgarh: tail ends below 0.2 mg/L</b><p>Dose advice sent to both pump operators. Re-test of the same taps is due within 48 hours.</p></div>
      <div class="alert" style="border-left-color:var(--high)"><b style="color:var(--high)">Kesarpura: 1.16 mg/L near the tank</b><p>Above the 1.0 mg/L limit. Operator advised to cut the dose.</p></div>
      <div class="alert"><b>Rajnagar: 1 reading does not fit its tap</b><p>Tail-end tap T-214 read 0.94 mg/L where the twin expects about 0.30. It may be tank water. Kept, flagged, and a re-test of T-214 is assigned.</p></div>`;
    charts.d = echarts.init($("#dChart"));
    charts.d.setOption({
      animationDuration: 800,
      grid: { left: 96, right: 26, top: 10, bottom: 50 },
      xAxis: Object.assign({ type: "value", min: 0, max: 1.4, interval: 0.2, name: "Lowest tail-end free chlorine (mg/L)", nameLocation: "middle", nameGap: 30 }, axisStyle),
      yAxis: Object.assign({ type: "category", data: rows.map(r => r[0]), inverse: true }, axisStyle, { splitLine: { show: false } }),
      series: [{ type: "bar", data: rows.map(r => ({ value: r[4], itemStyle: { color: colorFor(r[4]), borderRadius: [0, 4, 4, 0] } })), barWidth: 12,
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: C.muted, type: "dashed" }, data: [{ xAxis: 0.2 }, { xAxis: 1.0 }] } }]
    });
  }
  function countUp(el, to) {
    const t0 = performance.now(), dur = 900;
    (function f(now) { const p = Math.min(1, (now - t0) / dur); el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(f); })(t0);
  }

  // ---------------- boot ----------------
  const d = new Date(); $("#clock").textContent = d.toTimeString().slice(0, 5);
  const start = (location.hash || "#test").slice(1);
  showView(["test", "lab", "twin", "district"].includes(start) ? start : "test");
})();
