'use strict';

// ─── PRO / PAYMENT ────────────────────────────────────────────────────────────

const STORAGE_KEY = 'finstack_pro';

function isPro() {
  const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
  if (!data) return false;
  if (Date.now() > data.expires) {
    localStorage.removeItem(STORAGE_KEY);
    return false;
  }
  return true;
}

function activatePro(paymentId) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    payment_id: paymentId,
    activated: Date.now(),
    expires: Date.now() + (30 * 24 * 60 * 60 * 1000),
    plan: 'dashboard_pro'
  }));
}

function openUpgradeModal() {
  document.getElementById('upgrade-modal').style.display = 'block';
}

function closeUpgradeModal() {
  document.getElementById('upgrade-modal').style.display = 'none';
}

function simulatePayment() {
  // Real Razorpay checkout — falls back to demo if key not set
  const RAZORPAY_KEY = 'rzp_test_XXXXXXXXXXXXXXXX'; // Replace with your key from razorpay.com → Settings → API Keys
  if (!RAZORPAY_KEY || RAZORPAY_KEY.includes('XXXX')) {
    // Demo fallback — remove this block once Razorpay key is set
    const payId = 'pay_demo_' + Date.now();
    activatePro(payId);
    closeUpgradeModal();
    applyProFeatures();
    showToast('Pro unlocked! (Demo mode — wire Razorpay key to take real payments)');
    return;
  }
  const options = {
    key: RAZORPAY_KEY,
    amount: 29900,           // ₹299 in paise
    currency: 'INR',
    name: 'Arthex',
    description: 'Dashboard Pro — Monthly',
    image: '',               // add your logo URL here
    prefill: { name: '', email: '', contact: '' },
    theme: { color: '#2962ff' },
    handler: function(response) {
      activatePro(response.razorpay_payment_id);
      closeUpgradeModal();
      applyProFeatures();
      showToast('Payment successful! Welcome to Dashboard Pro.');
    },
    modal: {
      ondismiss: function() { showToast('Payment cancelled.', 'error'); }
    }
  };
  try {
    const rzp = new Razorpay(options);
    rzp.on('payment.failed', function(r) {
      showToast('Payment failed: ' + r.error.description, 'error');
    });
    rzp.open();
  } catch(e) {
    showToast('Razorpay not loaded. Check internet connection.', 'error');
  }
}

function startTrial() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    payment_id: 'trial_' + Date.now(),
    activated: Date.now(),
    expires: Date.now() + (7 * 24 * 60 * 60 * 1000),
    plan: 'trial'
  }));
  closeUpgradeModal();
  applyProFeatures();
  showToast('7-day trial started! Explore all Pro features.');
}

function applyProFeatures() {
  document.querySelectorAll('.pro-gate').forEach(el => el.classList.add('pro-unlocked'));
  document.querySelectorAll('.pro-lock-badge').forEach(el => { el.style.display = 'none'; });
  const portLock = document.getElementById('portfolio-lock-badge');
  if (portLock) portLock.style.display = 'none';
  updateProBadge();
}

function showToast(msg, type) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  if (type === 'error') t.style.background = 'rgba(239,83,80,0.92)';
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function updateProBadge() {
  const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
  const navEl = document.getElementById('nav-pro-badge');
  if (!navEl) return;
  if (!data) {
    navEl.textContent = 'Upgrade';
    navEl.style.background = 'var(--gold)';
    navEl.style.color = 'var(--bg)';
    navEl.onclick = openUpgradeModal;
    return;
  }
  const daysLeft = Math.ceil((data.expires - Date.now()) / 86400000);
  const isTrial = data.plan === 'trial';
  navEl.textContent = isTrial ? `Trial (${daysLeft}d left)` : 'Pro ✓';
  navEl.style.background = isTrial ? 'var(--gold)' : 'var(--green-bright)';
  navEl.style.color = 'var(--bg)';
  navEl.onclick = () => showToast(isTrial
    ? `Trial ends in ${daysLeft} days. Upgrade to keep access.`
    : `Pro active · ${daysLeft} days remaining`);
}

function checkExpiry() {
  if (!isPro() && document.querySelector('.pro-unlocked')) {
    document.querySelectorAll('.pro-unlocked').forEach(el => el.classList.remove('pro-unlocked'));
    showToast('Your Pro trial has expired. Upgrade to continue.');
    updateProBadge();
    // Re-show lock badges
    document.querySelectorAll('.pro-lock-badge').forEach(el => { el.style.display = ''; });
    const portLock = document.getElementById('portfolio-lock-badge');
    if (portLock) portLock.style.display = '';
  }
}

setInterval(checkExpiry, 60000);

function handleExportClick() {
  if (!isPro()) { openUpgradeModal(); return; }
  showToast('Exporting data as CSV...');
}

// ─── DATA ────────────────────────────────────────────────────────────────────

const STOCKS = [
  { symbol: 'RELIANCE',    name: 'Reliance Industries',       sector: 'Oil & Gas',       ltp: 2891.45, change: 1.24,  changeAmt: 35.40,  high: 2915.00, low: 2856.20, open: 2856.05, vol: '8.4M',  mcap: '₹19.6L Cr', pe: '22.4×', eps: '₹128.90', divy: '0.44%', w52: '2,188 — 3,217',  startPrice: 2400 },
  { symbol: 'TCS',         name: 'Tata Consultancy Services', sector: 'IT Services',     ltp: 3456.80, change: -0.43, changeAmt: -14.95, high: 3489.00, low: 3440.10, open: 3471.75, vol: '3.1M',  mcap: '₹12.6L Cr', pe: '28.7×', eps: '₹120.44', divy: '1.12%', w52: '3,056 — 4,210',  startPrice: 3200 },
  { symbol: 'HDFCBANK',    name: 'HDFC Bank',                 sector: 'Banking',         ltp: 1642.30, change: 0.87,  changeAmt: 14.20,  high: 1658.00, low: 1631.50, open: 1628.10, vol: '7.8M',  mcap: '₹12.4L Cr', pe: '18.2×', eps: '₹90.24',  divy: '0.98%', w52: '1,363 — 1,794',  startPrice: 1450 },
  { symbol: 'INFY',        name: 'Infosys',                   sector: 'IT Services',     ltp: 1567.90, change: -1.12, changeAmt: -17.80, high: 1591.00, low: 1560.20, open: 1585.70, vol: '6.2M',  mcap: '₹6.5L Cr',  pe: '24.1×', eps: '₹65.05',  divy: '2.34%', w52: '1,352 — 1,888',  startPrice: 1380 },
  { symbol: 'SBIN',        name: 'State Bank of India',       sector: 'PSU Banking',     ltp: 812.45,  change: 2.34,  changeAmt: 18.60,  high: 819.00,  low: 793.80,  open: 793.85,  vol: '14.2M', mcap: '₹7.2L Cr',  pe: '11.4×', eps: '₹71.27',  divy: '1.45%', w52: '634 — 912',     startPrice: 650  },
  { symbol: 'WIPRO',       name: 'Wipro',                     sector: 'IT Services',     ltp: 487.60,  change: 0.34,  changeAmt: 1.65,   high: 491.00,  low: 483.20,  open: 485.95,  vol: '4.7M',  mcap: '₹2.5L Cr',  pe: '19.8×', eps: '₹24.63',  divy: '0.21%', w52: '392 — 612',     startPrice: 420  },
  { symbol: 'BAJFINANCE',  name: 'Bajaj Finance',             sector: 'NBFC',            ltp: 6789.00, change: -0.78, changeAmt: -53.40, high: 6845.00, low: 6751.00, open: 6842.40, vol: '1.2M',  mcap: '₹4.1L Cr',  pe: '34.6×', eps: '₹196.22', divy: '0.28%', w52: '5,832 — 8,190', startPrice: 5900 },
  { symbol: 'KOTAKBANK',   name: 'Kotak Mahindra Bank',       sector: 'Banking',         ltp: 1876.25, change: 1.56,  changeAmt: 28.85,  high: 1889.00, low: 1851.00, open: 1847.40, vol: '4.9M',  mcap: '₹3.7L Cr',  pe: '20.3×', eps: '₹92.43',  divy: '0.11%', w52: '1,544 — 2,184', startPrice: 1640 },
  { symbol: 'TATAMOTORS',  name: 'Tata Motors',               sector: 'Auto',            ltp: 742.80,  change: 1.88,  changeAmt: 13.75,  high: 756.00,  low: 729.00,  open: 729.05,  vol: '11.3M', mcap: '₹2.7L Cr',  pe: '9.4×',  eps: '₹79.02',  divy: '0.00%', w52: '608 — 1,063',   startPrice: 680  },
  { symbol: 'ICICIBANK',   name: 'ICICI Bank',                sector: 'Banking',         ltp: 1241.50, change: 0.62,  changeAmt: 7.65,   high: 1252.00, low: 1231.00, open: 1233.85, vol: '10.1M', mcap: '₹8.7L Cr',  pe: '19.8×', eps: '₹62.73',  divy: '0.73%', w52: '968 — 1,385',   startPrice: 1050 },
  { symbol: 'AXISBANK',    name: 'Axis Bank',                 sector: 'Banking',         ltp: 1089.25, change: -0.34, changeAmt: -3.75,  high: 1098.00, low: 1082.00, open: 1093.00, vol: '8.6M',  mcap: '₹3.4L Cr',  pe: '14.6×', eps: '₹74.60',  divy: '0.09%', w52: '878 — 1,339',   startPrice: 950  },
  { symbol: 'HINDUNILVR',  name: 'Hindustan Unilever',        sector: 'FMCG',            ltp: 2178.40, change: 0.24,  changeAmt: 5.20,   high: 2189.00, low: 2162.00, open: 2173.15, vol: '2.1M',  mcap: '₹5.1L Cr',  pe: '58.4×', eps: '₹37.30',  divy: '1.74%', w52: '1,980 — 2,860', startPrice: 2100 },
  { symbol: 'BHARTIARTL',  name: 'Bharti Airtel',             sector: 'Telecom',         ltp: 1645.30, change: 0.91,  changeAmt: 14.85,  high: 1658.00, low: 1631.00, open: 1630.45, vol: '6.4M',  mcap: '₹9.7L Cr',  pe: '72.3×', eps: '₹22.75',  divy: '0.27%', w52: '1,079 — 1,779', startPrice: 1400 },
  { symbol: 'SUNPHARMA',   name: 'Sun Pharmaceutical',        sector: 'Pharma',          ltp: 1712.60, change: -0.55, changeAmt: -9.50,  high: 1726.00, low: 1702.00, open: 1722.10, vol: '2.8M',  mcap: '₹4.1L Cr',  pe: '38.9×', eps: '₹44.02',  divy: '0.47%', w52: '1,313 — 1,960', startPrice: 1550 },
  { symbol: 'MARUTI',      name: 'Maruti Suzuki India',       sector: 'Auto',            ltp: 11456.00,change: -0.21, changeAmt: -24.10, high: 11512.00,low: 11400.00,open: 11480.00, vol: '0.5M',  mcap: '₹3.5L Cr',  pe: '27.1×', eps: '₹422.75', divy: '1.31%', w52: '9,832 — 13,680',startPrice: 10200},
  { symbol: 'LT',          name: 'Larsen & Toubro',           sector: 'Infrastructure',  ltp: 3389.50, change: 1.02,  changeAmt: 34.20,  high: 3412.00, low: 3355.00, open: 3355.30, vol: '2.2M',  mcap: '₹4.7L Cr',  pe: '32.4×', eps: '₹104.61', divy: '0.62%', w52: '2,866 — 3,966', startPrice: 2980 },
  { symbol: 'ASIANPAINT',  name: 'Asian Paints',              sector: 'Consumer',        ltp: 2256.80, change: -0.88, changeAmt: -20.05, high: 2289.00, low: 2241.00, open: 2276.85, vol: '1.4M',  mcap: '₹2.2L Cr',  pe: '54.8×', eps: '₹41.18',  divy: '0.71%', w52: '2,025 — 3,394', startPrice: 2400 },
  { symbol: 'TITAN',       name: 'Titan Company',             sector: 'Consumer',        ltp: 3145.60, change: 0.68,  changeAmt: 21.25,  high: 3168.00, low: 3120.00, open: 3124.35, vol: '1.8M',  mcap: '₹2.8L Cr',  pe: '88.2×', eps: '₹35.66',  divy: '0.32%', w52: '2,665 — 3,886', startPrice: 2800 },
  { symbol: 'NTPC',        name: 'NTPC',                      sector: 'Power',           ltp: 348.90,  change: 1.34,  changeAmt: 4.62,   high: 352.00,  low: 344.00,  open: 344.28,  vol: '15.6M', mcap: '₹3.4L Cr',  pe: '18.4×', eps: '₹18.96',  divy: '1.86%', w52: '261 — 448',     startPrice: 290  },
  { symbol: 'ADANIPORTS',  name: 'Adani Ports & SEZ',         sector: 'Infrastructure',  ltp: 1189.40, change: -0.42, changeAmt: -5.05,  high: 1201.00, low: 1180.00, open: 1194.45, vol: '4.1M',  mcap: '₹2.6L Cr',  pe: '28.3×', eps: '₹42.04',  divy: '0.63%', w52: '945 — 1,621',   startPrice: 1050 },
  { symbol: 'POWERGRID',   name: 'Power Grid Corp',           sector: 'Power',           ltp: 296.40,  change: 0.75,  changeAmt: 2.20,   high: 299.00,  low: 293.00,  open: 294.20,  vol: '8.9M',  mcap: '₹2.8L Cr',  pe: '19.2×', eps: '₹15.44',  divy: '2.36%', w52: '244 — 366',     startPrice: 260  },
  { symbol: 'TECHM',       name: 'Tech Mahindra',             sector: 'IT Services',     ltp: 1456.20, change: 0.55,  changeAmt: 7.95,   high: 1468.00, low: 1442.00, open: 1448.25, vol: '3.5M',  mcap: '₹1.4L Cr',  pe: '31.8×', eps: '₹45.79',  divy: '2.06%', w52: '1,133 — 1,762', startPrice: 1250 },
  { symbol: 'M&M',         name: 'Mahindra & Mahindra',       sector: 'Auto',            ltp: 2789.50, change: 1.44,  changeAmt: 39.65,  high: 2812.00, low: 2750.00, open: 2750.85, vol: '4.2M',  mcap: '₹3.5L Cr',  pe: '26.7×', eps: '₹104.47', divy: '0.54%', w52: '1,676 — 3,222', startPrice: 2400 },
  { symbol: 'NESTLEIND',   name: 'Nestle India',              sector: 'FMCG',            ltp: 2189.30, change: -0.18, changeAmt: -3.95,  high: 2203.00, low: 2178.00, open: 2193.15, vol: '0.8M',  mcap: '₹2.1L Cr',  pe: '62.4×', eps: '₹35.08',  divy: '1.28%', w52: '2,098 — 2,778', startPrice: 2300 },
  { symbol: 'BAJAJFINSV',  name: 'Bajaj Finserv',             sector: 'NBFC',            ltp: 1698.40, change: 0.92,  changeAmt: 15.50,  high: 1712.00, low: 1681.00, open: 1682.90, vol: '3.1M',  mcap: '₹2.7L Cr',  pe: '22.4×', eps: '₹75.82',  divy: '0.04%', w52: '1,420 — 2,030', startPrice: 1500 },
  { symbol: 'ULTRACEMCO',  name: 'UltraTech Cement',          sector: 'Cement',          ltp: 10234.00,change: 0.38,  changeAmt: 38.60,  high: 10298.00,low: 10160.00,open: 10195.50, vol: '0.5M',  mcap: '₹2.9L Cr',  pe: '39.8×', eps: '₹257.14', divy: '0.34%', w52: '8,888 — 12,156',startPrice: 9500 },
];

const SCREENER_DATA = [
  { symbol: 'RELIANCE',   sector: 'Oil & Gas',    mcap: '19.6L',  pe: 22.4,  roe: 11.2,  chg52: '+21.4', vol: '8.4M'  },
  { symbol: 'TCS',        sector: 'IT Services',  mcap: '12.6L',  pe: 28.7,  roe: 47.3,  chg52: '+8.1',  vol: '3.1M'  },
  { symbol: 'HDFCBANK',   sector: 'Banking',      mcap: '12.4L',  pe: 18.2,  roe: 16.8,  chg52: '+20.3', vol: '7.8M'  },
  { symbol: 'INFY',       sector: 'IT Services',  mcap: '6.5L',   pe: 24.1,  roe: 32.4,  chg52: '+13.6', vol: '6.2M'  },
  { symbol: 'SBIN',       sector: 'PSU Banking',  mcap: '7.2L',   pe: 11.4,  roe: 18.6,  chg52: '+28.1', vol: '14.2M' },
  { symbol: 'WIPRO',      sector: 'IT Services',  mcap: '2.5L',   pe: 19.8,  roe: 17.4,  chg52: '+23.8', vol: '4.7M'  },
  { symbol: 'BAJFINANCE', sector: 'NBFC',         mcap: '4.1L',   pe: 34.6,  roe: 22.1,  chg52: '+15.0', vol: '1.2M'  },
  { symbol: 'KOTAKBANK',  sector: 'Banking',      mcap: '3.7L',   pe: 20.3,  roe: 14.9,  chg52: '+14.5', vol: '4.9M'  },
];

const NEWS_ITEMS = [
  { headline: 'SEBI approves framework for algorithmic trading by retail investors', time: '2 hours ago',   source: 'SEBI' },
  { headline: 'RBI keeps repo rate unchanged at 6.25% in April MPC meet',           time: '4 hours ago',   source: 'RBI'  },
  { headline: 'FII outflows continue for 3rd consecutive session; DII absorb selling', time: '5 hours ago', source: 'NSE'  },
  { headline: 'Nifty 50 closes above 24,800 for first time since January 2026',     time: '7 hours ago',   source: 'NSE'  },
  { headline: 'Reliance Q4 FY26 results: Revenue ₹2.3L Cr, PAT ₹17,850 Cr (+12% YoY)', time: '1 day ago', source: 'BSE'  },
];

const FII_FLOW_DATA = [
  { day: 'Mon', fii: -890,  dii: +1120 },
  { day: 'Tue', fii: +540,  dii: +340  },
  { day: 'Wed', fii: -1240, dii: +1450 },
  { day: 'Thu', fii: -620,  dii: +880  },
  { day: 'Fri', fii: -1651, dii: +1667 },
];

const OPTIONS_STRIKES = [2700, 2750, 2800, 2850, 2900, 2950, 3000, 3050, 3100, 3150, 3200];
const ATM_STRIKE = 2900;

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function fmt(n, decimals = 2) {
  return (+n).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtChange(change, changeAmt) {
  const sign = change >= 0 ? '+' : '';
  return `${sign}₹${fmt(Math.abs(changeAmt))} &nbsp;(${sign}${fmt(change)}%)`;
}

function generateOHLCV(startPrice, days) {
  const data = [];
  let price = startPrice;
  const now = new Date('2026-03-29');
  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;
    const change = (Math.random() - 0.46) * 0.025;
    const open = price;
    const close = price * (1 + change);
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low  = Math.min(open, close) * (1 - Math.random() * 0.01);
    const volume = Math.floor(Math.random() * 5000000 + 2000000);
    data.push({ time: date.toISOString().split('T')[0], open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2), value: volume });
    price = close;
  }
  return data;
}

// Generate intraday demo OHLCV data (NSE market hours 9:15–15:30 IST)
function generateIntradayOHLCV(startPrice, tf) {
  const intervalMinutes = { '5m': 5, '15m': 15, '1H': 60, '30m': 30, '4H': 240 }[tf] || 5;
  const daysBack = { '5m': 1, '15m': 3, '1H': 10, '30m': 5, '4H': 20 }[tf] || 1;
  const data = [];
  let price = startPrice;
  const now = new Date('2026-03-28T15:30:00+05:30');
  for (let d = daysBack; d >= 0; d--) {
    const day = new Date(now);
    day.setDate(day.getDate() - d);
    if (day.getDay() === 0 || day.getDay() === 6) continue;
    // NSE 9:15 AM to 3:30 PM
    const openTime = new Date(day);
    openTime.setHours(9, 15, 0, 0);
    const closeTime = new Date(day);
    closeTime.setHours(15, 30, 0, 0);
    for (let t = new Date(openTime); t <= closeTime; t = new Date(t.getTime() + intervalMinutes * 60000)) {
      const change = (Math.random() - 0.48) * 0.004;
      const open = price;
      const close = price * (1 + change);
      const high = Math.max(open, close) * (1 + Math.random() * 0.003);
      const low  = Math.min(open, close) * (1 - Math.random() * 0.003);
      const volume = Math.floor(Math.random() * 500000 + 100000);
      // Unix seconds (LightweightCharts requires this for intraday)
      const unixSec = Math.floor(t.getTime() / 1000);
      data.push({ time: unixSec, open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2), value: volume });
      price = close;
    }
  }
  return data;
}

function tfDays(tf) {
  return { '5m': 1, '15m': 2, '1H': 7, '1D': 1, '1W': 7, '1M': 30, '3M': 90, '1Y': 365 }[tf] || 365;
}

function tfIsIntraday(tf) {
  return ['5m', '15m', '1H', '30m', '4H'].includes(tf);
}

// ─── STATE ───────────────────────────────────────────────────────────────────

let activeStockIdx = 0;
let activeTF = '1M';
let chart = null;
let candleSeries = null;
let volumeSeries = null;
let ma20Series = null;
let ema50Series = null;
let bbUpperSeries = null;
let bbLowerSeries = null;
let vwapSeries = null;
let lastHoverPrice = null;   // tracked by crosshairMove — fallback for hline clicks
let activeIndicators = new Set(['MA20']);
let stockPrices = STOCKS.map(s => ({ ltp: s.ltp, change: s.change, changeAmt: s.changeAmt }));
let activeDrawTool = 'cursor';
let drawnPriceLines = [];   // horizontal price lines
let drawnTrendLines = [];   // {series, p1, p2} trend line objects
let drawingsVisible = true;

// Trend line state machine
const tlineState = { active: false, p1: null, previewSeries: null };

// Ray line state machine (extends infinitely right)
const rayState = { active: false, p1: null };

// ─── WATCHLIST RENDER ────────────────────────────────────────────────────────

function renderWatchlist() {
  const list = document.getElementById('wl-list');
  list.innerHTML = '';
  STOCKS.forEach((s, i) => {
    const p = stockPrices[i];
    const isUp = p.change >= 0;
    const el = document.createElement('div');
    el.className = 'wl-item stock-item' + (i === activeStockIdx ? ' active' : '');
    el.dataset.idx = i;
    el.innerHTML = `
      <div class="stock-row1">
        <span class="stock-symbol">${s.symbol}</span>
        <span class="stock-ltp wl-price mono ${isUp ? 'green' : 'red'}" id="wl-ltp-${i}">₹${fmt(p.ltp)}</span>
      </div>
      <div class="stock-row2">
        <span class="stock-name">${s.name}</span>
        <span class="stock-chg wl-chg ${isUp ? 'green' : 'red'}" id="wl-chg-${i}">${isUp ? '+' : ''}${fmt(p.change)}%</span>
      </div>
    `;
    el.addEventListener('click', () => selectStock(i));
    list.appendChild(el);
  });
}

// ─── SELECT STOCK ────────────────────────────────────────────────────────────

function selectStock(idx) {
  activeStockIdx = idx;
  const s = STOCKS[idx];
  const p = stockPrices[idx];

  document.querySelectorAll('.stock-item').forEach((el, i) => el.classList.toggle('active', i === idx));

  document.getElementById('ch-symbol').textContent = s.symbol;
  document.getElementById('ch-name').textContent = s.name + ' · NSE';
  const isUp = p.change >= 0;
  document.getElementById('ch-ltp').textContent = '₹' + fmt(p.ltp);
  document.getElementById('ch-ltp').className = 'chart-ltp price-pulse mono';
  const chEl = document.getElementById('ch-change');
  chEl.innerHTML = fmtChange(p.change, p.changeAmt);
  chEl.className = 'chart-change ' + (isUp ? 'green' : 'red');
  document.getElementById('ch-open').textContent = fmt(s.open);
  document.getElementById('ch-high').textContent = fmt(s.high);
  document.getElementById('ch-low').textContent = fmt(s.low);
  document.getElementById('ch-vol').textContent = s.vol;

  document.getElementById('ip-symbol').textContent = s.symbol;
  document.getElementById('ip-name').textContent = s.name;
  document.getElementById('ip-sector').textContent = s.sector + ' · NSE';
  document.getElementById('ip-ltp').textContent = '₹' + fmt(p.ltp);
  const ipChEl = document.getElementById('ip-change');
  ipChEl.innerHTML = fmtChange(p.change, p.changeAmt);
  ipChEl.className = 'val ' + (isUp ? 'green' : 'red');
  document.getElementById('ip-range').textContent = fmt(s.low, 0) + ' — ' + fmt(s.high, 0);
  document.getElementById('ip-52w').textContent = s.w52;
  document.getElementById('ip-vol').innerHTML = s.vol + ' <span style="color:var(--green-bright);font-size:10px;">(1.8× avg)</span>';
  document.getElementById('ip-mcap').textContent = s.mcap;
  document.getElementById('ip-pe').textContent = s.pe;
  document.getElementById('ip-eps').textContent = s.eps;
  document.getElementById('ip-divy').textContent = s.divy;

  // Sync alert panel to currently selected stock
  const alertSel = document.getElementById('alert-sym-sel');
  if (alertSel) alertSel.value = STOCKS[idx].symbol;

  loadChart();
}

// ─── CHART ───────────────────────────────────────────────────────────────────

function initChart() {
  const container = document.getElementById('chart-container');

  chart = LightweightCharts.createChart(container, {
    layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
    grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#363a45' },
    timeScale: { borderColor: '#363a45', timeVisible: true, secondsVisible: false },
    autoSize: true,   // fills container automatically — no offsetWidth/Height needed
  });

  candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderUpColor: '#26a69a',
    borderDownColor: '#ef5350',
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
  });

  volumeSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
    scaleMargins: { top: 0.85, bottom: 0 },
  });
  chart.priceScale('volume').applyOptions({
    drawTicks: false,
    borderVisible: false,
    scaleMargins: { top: 0.85, bottom: 0 },
  });

  ma20Series = chart.addLineSeries({
    color: '#2962ff',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
  });

  ema50Series = chart.addLineSeries({
    color: '#ff9800',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
    visible: false,
  });

  bbUpperSeries = chart.addLineSeries({
    color: 'rgba(150,150,255,0.6)',
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    priceLineVisible: false,
    lastValueVisible: false,
    visible: false,
  });

  bbLowerSeries = chart.addLineSeries({
    color: 'rgba(150,150,255,0.6)',
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    priceLineVisible: false,
    lastValueVisible: false,
    visible: false,
  });

  vwapSeries = chart.addLineSeries({
    color: '#e91e63',
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    priceLineVisible: false,
    lastValueVisible: false,
    visible: false,
  });

  loadChart();

  // ── Subscribe to chart clicks for drawing tools ──────────────────────────
  chart.subscribeClick(function(param) {
    if (!param.point) return;
    const priceFromClick = candleSeries.coordinateToPrice(param.point.y);
    // Use click price, or fall back to last crosshair price if coordinateToPrice returned null
    const price = priceFromClick != null ? priceFromClick : lastHoverPrice;
    if (price == null) return;

    // ── HORIZONTAL LINE ── (doesn't need time — works anywhere on chart)
    if (activeDrawTool === 'hline') {
      const hlinePrice = +price.toFixed(2);
      const line = candleSeries.createPriceLine({
        price: hlinePrice,
        color: '#f7a600',
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: fmt(price),
      });
      line._price = hlinePrice;
      drawnPriceLines.push(line);
      saveDrawings();
      showToast('Horizontal level placed at ₹' + fmt(price));
      return;
    }

    // Everything below needs time — bail if clicking outside data range
    if (!param.time) return;
    const time = param.time;

    // ── TREND LINE (2-click: p1 then p2) ──
    if (activeDrawTool === 'tline') {
      if (!tlineState.active) {
        // First click — mark p1, start preview
        tlineState.active = true;
        tlineState.p1 = { time, price };
        // Create a preview line series (will update on mousemove)
        tlineState.previewSeries = chart.addLineSeries({
          color: 'rgba(41,98,255,0.5)',
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        tlineState.previewSeries.setData([{ time, value: price }]);
        showToast('Click a second point to complete the trend line');
        updateToolStatus('tline', 'Trend Line — now click point 2 to complete');
      } else {
        // Second click — finalize
        const p1 = tlineState.p1;
        const p2 = { time, price };

        // Remove preview
        if (tlineState.previewSeries) {
          chart.removeSeries(tlineState.previewSeries);
          tlineState.previewSeries = null;
        }
        tlineState.active = false;
        tlineState.p1 = null;

        // Draw the final trend line extended across the visible range
        let extendedData = buildTrendLineData(p1, p2);
        // Safety: if filter collapsed the data to < 2 points, just draw the segment
        if (extendedData.length < 2) {
          const earlier = chartTimeToMs(p1.time) <= chartTimeToMs(p2.time) ? p1 : p2;
          const later   = chartTimeToMs(p1.time) <= chartTimeToMs(p2.time) ? p2 : p1;
          extendedData = [
            { time: earlier.time, value: +earlier.price.toFixed(2) },
            { time: later.time,   value: +later.price.toFixed(2) },
          ];
        }
        const series = chart.addLineSeries({
          color: '#2962ff',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        series.setData(extendedData);
        drawnTrendLines.push({ series, p1, p2 });
        saveDrawings();
      }
      return;
    }

    // ── RAY (from point, extends right) ──
    if (activeDrawTool === 'ray') {
      const series = chart.addLineSeries({
        color: '#26a69a',
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      // Ray: start at clicked point, extend ~5 years forward
      // Must handle both ISO string times and Unix timestamp numbers
      const startMs  = chartTimeToMs(time);
      const endMs    = startMs + 5 * 365 * 24 * 60 * 60 * 1000;
      const endTime  = typeof time === 'string' ? msToDateStr(endMs) : Math.floor(endMs / 1000);
      series.setData([{ time, value: +price.toFixed(2) }, { time: endTime, value: +price.toFixed(2) }]);
      drawnTrendLines.push({ series, p1: { time, price }, p2: { time: endTime, price } });
      return;
    }

    // ── FIBONACCI RETRACEMENT (Pro gated) ──
    if (activeDrawTool === 'fib') {
      if (!isPro()) { openUpgradeModal(); return; }
      if (!tlineState.active) {
        tlineState.active = true;
        tlineState.p1 = { time, price };
        showToast('Click the end point to draw Fibonacci levels');
      } else {
        const p1 = tlineState.p1;
        const p2 = { time, price };
        tlineState.active = false;
        tlineState.p1 = null;
        drawFibonacci(p1, p2);
      }
      return;
    }
  });

  // ── Preview trend line on mouse move ─────────────────────────────────────
  chart.subscribeCrosshairMove(function(param) {
    // Always track hover price so hline can use it as fallback on click
    if (param.point) {
      const hp = candleSeries.coordinateToPrice(param.point.y);
      if (hp != null) lastHoverPrice = hp;
    }
    if (!tlineState.active || !tlineState.previewSeries || !param.point || !param.time) return;
    if (activeDrawTool !== 'tline' && activeDrawTool !== 'fib') return;
    const price = candleSeries.coordinateToPrice(param.point.y);
    if (price == null) return;
    const p1 = tlineState.p1;
    // Safe string-date comparison using < > on ISO strings (works because YYYY-MM-DD sorts lexicographically)
    const earlier = p1.time <= param.time ? p1 : { time: param.time, price };
    const later   = p1.time <= param.time ? { time: param.time, price } : p1;
    if (earlier.time !== later.time) {
      tlineState.previewSeries.setData([
        { time: earlier.time, value: +earlier.price.toFixed(2) },
        { time: later.time,   value: +later.price.toFixed(2) },
      ]);
    }
  });

  // autoSize:true handles resize automatically — no manual listener needed
}

// ── Build trend line data extended across chart timerange ──────────────────
// Convert any LightweightCharts time value to a Unix ms timestamp for arithmetic
function chartTimeToMs(t) {
  if (typeof t === 'string') return new Date(t).getTime();
  if (typeof t === 'object' && t.year) return new Date(t.year, t.month - 1, t.day).getTime();
  return t * 1000; // already a Unix second timestamp
}

// Convert ms timestamp back to ISO date string ("YYYY-MM-DD")
function msToDateStr(ms) {
  return new Date(ms).toISOString().split('T')[0];
}

function buildTrendLineData(p1, p2) {
  // Convert to ms for safe arithmetic (times are often ISO date strings)
  const t1 = chartTimeToMs(p1.time);
  const t2 = chartTimeToMs(p2.time);
  if (t1 === t2) return [{ time: p1.time, value: +p1.price.toFixed(2) }];

  const slope = (p2.price - p1.price) / (t2 - t1);
  const spanMs = Math.abs(t2 - t1);
  const tFarPast   = Math.min(t1, t2) - spanMs * 2;
  const tFarFuture = Math.max(t1, t2) + spanMs * 3;
  const pricePast   = p1.price + slope * (tFarPast - t1);
  const priceFuture = p1.price + slope * (tFarFuture - t1);

  const raw = [
    { time: msToDateStr(tFarPast),   value: +pricePast.toFixed(2) },
    { time: p1.time,                 value: +p1.price.toFixed(2) },
    { time: p2.time,                 value: +p2.price.toFixed(2) },
    { time: msToDateStr(tFarFuture), value: +priceFuture.toFixed(2) },
  ];
  // Sort chronologically (handles right-to-left clicks where p1 > p2)
  raw.sort((a, b) => chartTimeToMs(a.time) - chartTimeToMs(b.time));
  // Remove exact duplicate times
  return raw.filter((d, i, arr) => i === 0 || chartTimeToMs(d.time) > chartTimeToMs(arr[i - 1].time));
}

// ── Draw Fibonacci retracement levels ─────────────────────────────────────
function drawFibonacci(p1, p2) {
  const hi = Math.max(p1.price, p2.price);
  const lo = Math.min(p1.price, p2.price);
  const diff = hi - lo;
  const levels = [
    { ratio: 0,     color: '#ef5350', label: '0%'     },
    { ratio: 0.236, color: '#f7a600', label: '23.6%'  },
    { ratio: 0.382, color: '#26a69a', label: '38.2%'  },
    { ratio: 0.5,   color: '#2962ff', label: '50%'    },
    { ratio: 0.618, color: '#26a69a', label: '61.8%'  },
    { ratio: 0.786, color: '#f7a600', label: '78.6%'  },
    { ratio: 1,     color: '#ef5350', label: '100%'   },
  ];
  const t1ms = chartTimeToMs(p1.time), t2ms = chartTimeToMs(p2.time);
  const startMs = Math.min(t1ms, t2ms);
  const endMs   = Math.max(t1ms, t2ms) + (Math.max(t1ms, t2ms) - startMs) * 2;
  const startTime = typeof p1.time === 'string' ? msToDateStr(startMs) : Math.floor(startMs / 1000);
  const endTime   = typeof p1.time === 'string' ? msToDateStr(endMs)   : Math.floor(endMs / 1000);

  levels.forEach(({ ratio, color, label }) => {
    const price = lo + diff * (1 - ratio);
    const series = chart.addLineSeries({
      color,
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: true,
      title: `Fib ${label}`,
      crosshairMarkerVisible: false,
    });
    series.setData([
      { time: startTime, value: +price.toFixed(2) },
      { time: endTime,   value: +price.toFixed(2) },
    ]);
    drawnTrendLines.push({ series, p1, p2 });
  });
  showToast('Fibonacci retracement drawn (7 levels)');
}

function computeMA(data, period) {
  return data.map((d, i) => {
    if (i < period - 1) return null;
    const slice = data.slice(i - period + 1, i + 1);
    const avg = slice.reduce((s, x) => s + x.close, 0) / period;
    return { time: d.time, value: +avg.toFixed(2) };
  }).filter(Boolean);
}

function computeEMA(data, period) {
  const k = 2 / (period + 1);
  let ema = data[0].close;
  return data.map((d, i) => {
    if (i === 0) { ema = d.close; return { time: d.time, value: +ema.toFixed(2) }; }
    ema = d.close * k + ema * (1 - k);
    return { time: d.time, value: +ema.toFixed(2) };
  });
}

function computeBB(data, period = 20, mult = 2) {
  const upper = [], lower = [];
  data.forEach((d, i) => {
    if (i < period - 1) return;
    const slice = data.slice(i - period + 1, i + 1);
    const avg = slice.reduce((s, x) => s + x.close, 0) / period;
    const std = Math.sqrt(slice.reduce((s, x) => s + (x.close - avg) ** 2, 0) / period);
    upper.push({ time: d.time, value: +(avg + mult * std).toFixed(2) });
    lower.push({ time: d.time, value: +(avg - mult * std).toFixed(2) });
  });
  return { upper, lower };
}

function computeVWAP(data, period = 14) {
  // Rolling VWAP (14-period typical price × volume / volume)
  return data.map((d, i) => {
    if (i < period - 1) return null;
    const slice = data.slice(i - period + 1, i + 1);
    const sumTV = slice.reduce((s, x) => s + (x.high + x.low + x.close) / 3 * (x.value || 1), 0);
    const sumV  = slice.reduce((s, x) => s + (x.value || 1), 0);
    return { time: d.time, value: +(sumTV / sumV).toFixed(2) };
  }).filter(Boolean);
}

function loadChart(noShimmer) {
  // If API is live, use real data instead of fake OHLCV
  if (isLive) { loadLiveChart(); return; }
  const s = STOCKS[activeStockIdx];
  const days = tfDays(activeTF);
  const intraday = tfIsIntraday(activeTF);
  const container = document.getElementById('chart-container-wrap');

  if (!noShimmer) {
    const shimmer = document.createElement('div');
    shimmer.className = 'chart-shimmer';
    shimmer.id = 'chart-shimmer';
    container.appendChild(shimmer);
  }

  const data = intraday ? generateIntradayOHLCV(s.startPrice, activeTF) : generateOHLCV(s.startPrice, days);

  const render = () => {
    // Clear existing data before setting new stock's data
    try { candleSeries.setData([]); volumeSeries.setData([]); } catch(e) {}
    const candle = data.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }));
    const vol = data.map(d => ({
      time: d.time, value: d.value,
      color: d.close >= d.open ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)'
    }));

    candleSeries.setData(candle);
    volumeSeries.setData(vol);

    // MA20
    if (activeIndicators.has('MA20')) {
      ma20Series.setData(computeMA(data, 20));
      ma20Series.applyOptions({ visible: true });
    } else {
      ma20Series.applyOptions({ visible: false });
    }

    // EMA50
    if (activeIndicators.has('EMA50')) {
      ema50Series.setData(computeEMA(data, 50));
      ema50Series.applyOptions({ visible: true });
    } else {
      ema50Series.applyOptions({ visible: false });
    }

    // Bollinger Bands
    if (activeIndicators.has('BB')) {
      const bb = computeBB(data);
      bbUpperSeries.setData(bb.upper);
      bbLowerSeries.setData(bb.lower);
      bbUpperSeries.applyOptions({ visible: true });
      bbLowerSeries.applyOptions({ visible: true });
    } else {
      bbUpperSeries.applyOptions({ visible: false });
      bbLowerSeries.applyOptions({ visible: false });
    }

    // VWAP
    if (activeIndicators.has('VWAP')) {
      vwapSeries.setData(computeVWAP(data));
      vwapSeries.applyOptions({ visible: true });
    } else {
      vwapSeries.applyOptions({ visible: false });
    }

    chart.timeScale().fitContent();

    // Sub-panes — update if visible
    if (activeIndicators.has('RSI'))  updateRsiPane(data);
    if (activeIndicators.has('MACD')) updateMacdPane(data);

    // Restore drawings for this stock after new data loads
    setTimeout(restoreDrawings, 50);

    const shimEl = document.getElementById('chart-shimmer');
    if (shimEl) shimEl.remove();
  };

  if (!noShimmer) {
    setTimeout(render, 420);
  } else {
    render();
  }
}

// ─── DRAWING TOOLBAR ─────────────────────────────────────────────────────────

const PRO_TOOLS = new Set(['rect', 'text']); // fib handled separately (Pro check inside click handler)

function initDrawToolbar() {
  const wrap = document.getElementById('chart-container-wrap');

  document.querySelectorAll('.draw-tool').forEach(btn => {
    btn.addEventListener('click', () => {
      const tool = btn.dataset.tool;

      // Pro tools: open modal
      if (PRO_TOOLS.has(tool) && !isPro()) {
        openUpgradeModal();
        return;
      }

      if (tool === 'trash') {
        // Clear horizontal lines
        drawnPriceLines.forEach(line => { try { candleSeries.removePriceLine(line); } catch(e){} });
        drawnPriceLines = [];
        // Clear trend lines + fib
        drawnTrendLines.forEach(({ series }) => { try { chart.removeSeries(series); } catch(e){} });
        drawnTrendLines = [];
        // Cancel any in-progress tline draw
        if (tlineState.previewSeries) { try { chart.removeSeries(tlineState.previewSeries); } catch(e){} }
        tlineState.active = false; tlineState.p1 = null; tlineState.previewSeries = null;
        // Clear saved drawings for this stock
        const sym = STOCKS[activeStockIdx]?.symbol;
        if (sym) {
          const all = JSON.parse(localStorage.getItem(DRAWINGS_KEY) || '{}');
          delete all[sym];
          localStorage.setItem(DRAWINGS_KEY, JSON.stringify(all));
        }
        showToast('All drawings cleared');
        return;
      }

      if (tool === 'eye') {
        drawingsVisible = !drawingsVisible;
        drawnPriceLines.forEach(line => {
          try { line.applyOptions({ visible: drawingsVisible }); } catch(e) {}
        });
        drawnTrendLines.forEach(({ series }) => {
          try { series.applyOptions({ visible: drawingsVisible }); } catch(e) {}
        });
        btn.style.color = drawingsVisible ? '' : 'var(--muted2)';
        showToast(drawingsVisible ? 'Drawings visible' : 'Drawings hidden');
        return;
      }

      if (tool === 'magnet') {
        btn.classList.toggle('active');
        return;
      }

      // Set active draw tool
      activeDrawTool = tool;
      document.querySelectorAll('.draw-tool').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateToolStatus(tool);

      // Update cursor
      if (tool === 'cursor') {
        wrap.classList.add('cursor-default');
        wrap.classList.remove('cursor-crosshair');
      } else {
        wrap.classList.remove('cursor-default');
        wrap.classList.add('cursor-crosshair');
      }
    });
  });
}

// ─── TIMEFRAME TABS ──────────────────────────────────────────────────────────

document.getElementById('tf-tabs').addEventListener('click', e => {
  const tab = e.target.closest('.tf-tab');
  if (!tab) return;
  if (tab.dataset.pro && !isPro()) {
    openUpgradeModal();
    return;
  }
  document.querySelectorAll('.tf-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  activeTF = tab.dataset.tf;
  loadChart();
});

// ─── INDICATOR CHIPS ─────────────────────────────────────────────────────────

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const ind = chip.dataset.ind;
    if (activeIndicators.has(ind)) {
      activeIndicators.delete(ind);
      chip.classList.remove('active');
    } else {
      activeIndicators.add(ind);
      chip.classList.add('active');
    }
    // RSI and MACD use their own panes
    if (ind === 'RSI') { toggleRsiPane(activeIndicators.has('RSI')); return; }
    if (ind === 'MACD') { toggleMacdPane(activeIndicators.has('MACD')); return; }
    loadChart(true);
  });
});

// ─── BOTTOM TABS ─────────────────────────────────────────────────────────────

function initBottomTabs() {
  const tabs = document.querySelectorAll('.bottom-tab');
  const underline = document.getElementById('tab-underline');

  function moveUnderline(tab) {
    underline.style.left = tab.offsetLeft + 'px';
    underline.style.width = tab.offsetWidth + 'px';
  }

  const activeTab = document.querySelector('.bottom-tab.active');
  if (activeTab) requestAnimationFrame(() => moveUnderline(activeTab));

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Portfolio tab: if not pro, switch to panel but gate shows overlay
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      const panel = document.getElementById('panel-' + tab.dataset.panel);
      if (panel) panel.classList.add('active');
      moveUnderline(tab);
    });
  });
}

// ─── OPTIONS CHAIN ───────────────────────────────────────────────────────────

function renderOptionsChain() {
  const tbody = document.getElementById('options-tbody');
  tbody.innerHTML = '';
  OPTIONS_STRIKES.forEach(strike => {
    const distToAtm = Math.abs(strike - ATM_STRIKE) / ATM_STRIKE;
    const isAtm = strike === ATM_STRIKE;
    const ceIV = (18 + distToAtm * 40 + Math.random() * 3).toFixed(1);
    const peIV = (17 + distToAtm * 42 + Math.random() * 3).toFixed(1);
    const ceLTP = Math.max(5, (ATM_STRIKE - strike + 60 + Math.random() * 20)).toFixed(2);
    const peLTP = Math.max(5, (strike - ATM_STRIKE + 55 + Math.random() * 20)).toFixed(2);
    const ceOI = Math.floor((500000 / (distToAtm * 10 + 1)) + Math.random() * 50000);
    const peOI = Math.floor((480000 / (distToAtm * 10 + 1)) + Math.random() * 50000);
    const tr = document.createElement('tr');
    if (isAtm) tr.className = 'atm-row';
    tr.innerHTML = `
      <td>${(ceOI/1000).toFixed(0)}K</td>
      <td>₹${(+ceLTP).toFixed(2)}</td>
      <td>${ceIV}%</td>
      <td class="strike-col">${isAtm ? '★ ' : ''}${strike}</td>
      <td>₹${(+peLTP).toFixed(2)}</td>
      <td>${(peOI/1000).toFixed(0)}K</td>
      <td>${peIV}%</td>
    `;
    tbody.appendChild(tr);
  });
}

// ─── SCREENER ────────────────────────────────────────────────────────────────

function renderScreener() {
  const tbody = document.getElementById('screener-tbody');
  tbody.innerHTML = '';
  SCREENER_DATA.forEach(row => {
    const isUp = row.chg52.startsWith('+');
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.symbol}</td>
      <td>${row.sector}</td>
      <td>₹${row.mcap} Cr</td>
      <td>${row.pe}</td>
      <td class="${row.roe > 20 ? 'green' : ''}">${row.roe}%</td>
      <td class="${isUp ? 'green' : 'red'}">${row.chg52}%</td>
      <td>${row.vol}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ─── FII/DII FLOW BARS ───────────────────────────────────────────────────────

// ─── PHASE 1: CHART.JS CHARTS ────────────────────────────────────────────────

let fiiChartJs = null;
let pcrChartJs = null;
let gsecChartJs = null;

function chartJsDefaults() {
  // Shared Chart.js theme defaults matching TV dark/light theme
  const isDark = !document.body.classList.contains('light-theme');
  return {
    color: isDark ? '#b2b5be' : '#434651',
    gridColor: isDark ? 'rgba(42,46,57,0.8)' : 'rgba(224,227,235,0.8)',
    textColor: isDark ? '#787b86' : '#787b86',
  };
}

function destroyChartJs(instance) {
  if (instance) { try { instance.destroy(); } catch(e) {} }
  return null;
}

function renderFiiChart(fiiData, diiData, labels) {
  fiiChartJs = destroyChartJs(fiiChartJs);
  const ctx = document.getElementById('fii-chart');
  if (!ctx) return;
  const th = chartJsDefaults();
  fiiChartJs = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'FII Net (₹ Cr)',
          data: fiiData,
          backgroundColor: fiiData.map(v => v >= 0 ? 'rgba(38,166,154,0.7)' : 'rgba(239,83,80,0.7)'),
          borderRadius: 2,
        },
        {
          label: 'DII Net (₹ Cr)',
          data: diiData,
          backgroundColor: diiData.map(v => v >= 0 ? 'rgba(41,98,255,0.7)' : 'rgba(239,83,80,0.5)'),
          borderRadius: 2,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { labels: { color: th.textColor, font: { size: 10 }, boxWidth: 10 } } },
      scales: {
        x: { ticks: { color: th.textColor, font: { size: 10 } }, grid: { color: th.gridColor } },
        y: { ticks: { color: th.textColor, font: { size: 10 } }, grid: { color: th.gridColor } },
      },
    },
  });
}

function renderPcrChart(pcrValues, labels) {
  pcrChartJs = destroyChartJs(pcrChartJs);
  const ctx = document.getElementById('pcr-chart');
  if (!ctx) return;
  const th = chartJsDefaults();
  pcrChartJs = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'PCR',
        data: pcrValues,
        borderColor: '#2962ff',
        backgroundColor: 'rgba(41,98,255,0.08)',
        fill: true, tension: 0.3, pointRadius: 2, borderWidth: 1.5,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { display: false },
        annotation: { annotations: {
          bullish: { type: 'line', yMin: 1, yMax: 1, borderColor: 'rgba(38,166,154,0.4)', borderDash: [4,2], borderWidth: 1, label: { content: 'Bullish 1.0', display: true, color: '#26a69a', font: { size: 9 } } },
        }}
      },
      scales: {
        x: { ticks: { color: th.textColor, font: { size: 10 }, maxTicksLimit: 8 }, grid: { display: false } },
        y: { ticks: { color: th.textColor, font: { size: 10 } }, grid: { color: th.gridColor }, min: 0.4, max: 1.8 },
      },
    },
  });
}

function renderGsecChart(yields, labels) {
  gsecChartJs = destroyChartJs(gsecChartJs);
  const ctx = document.getElementById('gsec-chart');
  if (!ctx) return;
  const th = chartJsDefaults();
  gsecChartJs = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '10Y G-Sec Yield %',
        data: yields,
        borderColor: '#f7a600',
        backgroundColor: 'rgba(247,166,0,0.07)',
        fill: true, tension: 0.3, pointRadius: 2, borderWidth: 1.5,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: th.textColor, font: { size: 10 }, maxTicksLimit: 8 }, grid: { display: false } },
        y: { ticks: { color: th.textColor, font: { size: 10 }, callback: v => v + '%' }, grid: { color: th.gridColor } },
      },
    },
  });
}

function initPhase1Charts() {
  // Demo data — replaced by live API data when connected
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  renderFiiChart(
    FII_FLOW_DATA.map(d => d.fii),
    FII_FLOW_DATA.map(d => d.dii),
    FII_FLOW_DATA.map(d => d.day)
  );
  // PCR demo — 30 days
  const pcrLabels = Array.from({ length: 30 }, (_, i) => {
    const d = new Date('2026-03-01'); d.setDate(d.getDate() + i);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  });
  const pcrDemo = pcrLabels.map((_, i) => +(0.75 + Math.sin(i * 0.3) * 0.3 + Math.random() * 0.1).toFixed(2));
  renderPcrChart(pcrDemo, pcrLabels);
  // G-Sec demo — 30 days
  const gsecDemo = pcrLabels.map((_, i) => +(6.5 + Math.sin(i * 0.2) * 0.3 + i * 0.01).toFixed(2));
  renderGsecChart(gsecDemo, pcrLabels);
}

// Live FII/DII Chart.js update
function updateFiiChartLive(fiiNet, diiNet) {
  // Shift in today's live data into the bar chart
  if (!fiiChartJs) return;
  const ds = fiiChartJs.data.datasets;
  const last = fiiChartJs.data.labels.length - 1;
  ds[0].data[last] = fiiNet;
  ds[0].backgroundColor[last] = fiiNet >= 0 ? 'rgba(38,166,154,0.7)' : 'rgba(239,83,80,0.7)';
  ds[1].data[last] = diiNet;
  ds[1].backgroundColor[last] = diiNet >= 0 ? 'rgba(41,98,255,0.7)' : 'rgba(239,83,80,0.5)';
  fiiChartJs.update('none');
}

// Rebuild all Chart.js charts on theme change (colors need to update)
function rebuildPhase1Charts() {
  initPhase1Charts();
  if (rsiChart) {
    const isDark = !document.body.classList.contains('light-theme');
    rsiChart.applyOptions({ layout: { background: { color: isDark ? '#131722' : '#ffffff' }, textColor: isDark ? '#d1d4dc' : '#434651' } });
    macdChart && macdChart.applyOptions({ layout: { background: { color: isDark ? '#131722' : '#ffffff' }, textColor: isDark ? '#d1d4dc' : '#434651' } });
  }
}

function renderFlowBars() {
  // Legacy - now replaced by Chart.js. No-op, kept to avoid breaking DOMContentLoaded.
}

// ─── NEWS ────────────────────────────────────────────────────────────────────

function renderNews() {
  const list = document.getElementById('news-list');
  NEWS_ITEMS.forEach(item => {
    const el = document.createElement('div');
    el.className = 'news-item';
    el.innerHTML = `
      <div class="news-headline">${item.headline}</div>
      <div class="news-meta">
        <span class="news-source">${item.source}</span>
        <span>${item.time}</span>
      </div>
    `;
    list.appendChild(el);
  });
}

// ─── PORTFOLIO ───────────────────────────────────────────────────────────────

function openAddTrade() {
  showToast('Add Trade form coming soon.');
}

// ─── MARKET STATUS ───────────────────────────────────────────────────────────

function updateMarketStatus() {
  const now = new Date();
  const ist = new Date(now.getTime() + 5.5 * 3600000);
  const h = ist.getUTCHours();
  const m = ist.getUTCMinutes();
  const mins = h * 60 + m;
  const isOpen = mins >= (9 * 60 + 15) && mins <= (15 * 60 + 30);
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  dot.className = 'status-dot ' + (isOpen ? 'open' : 'closed');
  text.textContent = isOpen ? 'MARKET OPEN' : 'MARKET CLOSED';
  text.style.color = isOpen ? 'var(--green-bright)' : 'var(--muted)';
}

// ─── LIVE PRICE SIMULATION ───────────────────────────────────────────────────

function updatePrices() {
  STOCKS.forEach((s, i) => {
    const tweak = (Math.random() - 0.5) * 0.002;
    const newLtp = stockPrices[i].ltp * (1 + tweak);
    const delta = newLtp - s.ltp;
    const newChange = stockPrices[i].change + tweak * 100;
    const newChangeAmt = stockPrices[i].changeAmt + delta;
    const prevLtp = stockPrices[i].ltp;
    stockPrices[i] = { ltp: +newLtp.toFixed(2), change: +newChange.toFixed(2), changeAmt: +newChangeAmt.toFixed(2) };

    const ltpEl = document.getElementById('wl-ltp-' + i);
    const chgEl = document.getElementById('wl-chg-' + i);
    if (ltpEl) {
      ltpEl.textContent = '₹' + fmt(stockPrices[i].ltp);
      const isUp = newLtp >= prevLtp;
      ltpEl.parentElement.parentElement.classList.remove('flash-green', 'flash-red');
      void ltpEl.parentElement.parentElement.offsetWidth;
      ltpEl.parentElement.parentElement.classList.add(isUp ? 'flash-green' : 'flash-red');
    }
    if (chgEl) {
      const isUp2 = stockPrices[i].change >= 0;
      chgEl.textContent = (isUp2 ? '+' : '') + fmt(stockPrices[i].change) + '%';
      chgEl.className = 'stock-chg wl-chg ' + (isUp2 ? 'green' : 'red');
    }
  });

  const p = stockPrices[activeStockIdx];
  const isUp = p.change >= 0;
  document.getElementById('ch-ltp').textContent = '₹' + fmt(p.ltp);
  const chEl = document.getElementById('ch-change');
  chEl.innerHTML = fmtChange(p.change, p.changeAmt);
  chEl.className = 'chart-change ' + (isUp ? 'green' : 'red');
  document.getElementById('ip-ltp').textContent = '₹' + fmt(p.ltp);
  const ipChEl = document.getElementById('ip-change');
  ipChEl.innerHTML = fmtChange(p.change, p.changeAmt);
  ipChEl.className = 'val ' + (isUp ? 'green' : 'red');

  const niftyTweak = (Math.random() - 0.5) * 0.001;
  const niftyVal = document.getElementById('nav-nifty-val');
  const cur = parseFloat(niftyVal.textContent.replace(/,/g, ''));
  const newNifty = cur * (1 + niftyTweak);
  niftyVal.textContent = newNifty.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── WATCHLIST SEARCH ────────────────────────────────────────────────────────

document.getElementById('wl-search').addEventListener('input', function () {
  const q = this.value.toLowerCase().trim();
  if (!q) { document.querySelectorAll('.stock-item').forEach(el => el.style.display = ''); return; }
  document.querySelectorAll('.stock-item').forEach(el => {
    const idx = parseInt(el.dataset.idx);
    const s = STOCKS[idx];
    const match = s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q);
    el.style.display = match ? '' : 'none';
  });
});

document.getElementById('wl-search').addEventListener('keydown', function (e) {
  if (e.key === 'Enter') addSymbolFromSearch(this.value.trim().toUpperCase());
});

document.querySelector('.watchlist-add').addEventListener('click', function () {
  const q = document.getElementById('wl-search').value.trim().toUpperCase();
  if (q) addSymbolFromSearch(q);
  else document.getElementById('wl-search').focus();
});

async function addSymbolFromSearch(symbol) {
  if (!symbol) return;
  // If already in watchlist, just select it
  const existing = STOCKS.findIndex(s => s.symbol === symbol);
  if (existing !== -1) { selectStock(existing); return; }

  showToast(`Searching ${symbol}…`);
  try {
    const d = await apiFetch(`/api/quote/${symbol}`);
    if (!d || d.error) throw new Error('not found');
    const ltp   = d.last_price || d.current_price || d.price || 0;
    const chg   = d.change_percent || d.pChange || 0;
    const chgAmt= d.change || d.net_change || 0;
    const newStock = {
      symbol,
      name: d.company_name || d.name || symbol,
      sector: d.sector || d.industry || 'NSE',
      ltp:   +ltp,
      change:+chg,
      changeAmt: +chgAmt,
      high:  +(d.high || d.day_high || ltp),
      low:   +(d.low  || d.day_low  || ltp),
      open:  +(d.open || d.day_open || ltp),
      vol:   d.volume ? (d.volume > 1e6 ? (d.volume/1e6).toFixed(1)+'M' : (d.volume/1e3).toFixed(0)+'K') : '—',
      mcap:  d.market_cap ? '₹'+d.market_cap : '—',
      pe:    d.pe ? d.pe+'×' : '—',
      eps:   d.eps ? '₹'+d.eps : '—',
      divy:  d.dividend_yield ? d.dividend_yield+'%' : '—',
      w52:   (d.year_low||'—') + ' — ' + (d.year_high||'—'),
      startPrice: +ltp * 0.85,
    };
    STOCKS.push(newStock);
    stockPrices.push({ ltp: newStock.ltp, change: newStock.change, changeAmt: newStock.changeAmt });
    renderWatchlist();
    selectStock(STOCKS.length - 1);
    document.getElementById('wl-search').value = '';
    showToast(`${symbol} added to watchlist`);
  } catch (_) {
    showToast(`${symbol} not found — check API connection`, 'error');
  }
}

// ─── REAL DATA LAYER ─────────────────────────────────────────────────────────

const API = 'http://localhost:8000';
let isLive = false;

async function apiFetch(path) {
  const r = await fetch(API + path, { signal: AbortSignal.timeout(6000) });
  if (!r.ok) throw new Error(r.status);
  return r.json();
}

function showLiveMode() {
  const badge = document.createElement('span');
  badge.textContent = '⬤ LIVE';
  badge.style.cssText = 'font-family:JetBrains Mono,monospace;font-size:10px;font-weight:700;color:#26a69a;margin-left:8px;animation:pulse-dot 2s infinite;';
  const ver = document.querySelector('#nav-version');
  if (ver) ver.appendChild(badge);
}

async function loadLiveNifty() {
  try {
    const d = await apiFetch('/api/nifty');
    const items = [
      { key: 'NIFTY50',   elId: 'nav-nifty',    label: 'NIFTY 50' },
      { key: 'BANKNIFTY', elId: 'nav-banknifty', label: 'BANKNIFTY' },
    ];
    items.forEach(({ key, elId, label }) => {
      const el = document.getElementById(elId);
      if (!el || !d[key] || d[key].error) return;
      const nd = d[key];
      const price = nd.last_price || nd.price || nd.current;
      const chg = nd.change_percent || nd.pChange || 0;
      if (!price) return;
      const cls = chg >= 0 ? 'green' : 'red';
      const sign = chg >= 0 ? '+' : '';
      el.innerHTML = `<span class="muted" style="font-size:10px;">${label}</span> <span class="mono">${Number(price).toLocaleString('en-IN', {maximumFractionDigits:2})}</span> <span class="${cls}">${sign}${Number(chg).toFixed(2)}%</span>`;
    });
  } catch (_) {}
}

async function loadLiveVix() {
  try {
    const d = await apiFetch('/api/vix');
    const el = document.getElementById('nav-vix');
    if (!el || !d) return;
    const vix = d.current_vix || d.vix || d.last_price;
    if (!vix) return;
    const v = Number(vix).toFixed(1);
    const cls = v < 15 ? 'green' : v < 20 ? 'gold' : 'red';
    const sig = v < 15 ? '↓ Calm' : v < 20 ? '→ Neutral' : '↑ Fear';
    el.innerHTML = `<span class="muted" style="font-size:10px;">INDIA VIX</span> <span class="mono ${cls}">${v}</span> <span class="${cls}">${sig}</span>`;
  } catch (_) {}
}

async function loadLiveQuote(symbol) {
  try {
    const d = await apiFetch(`/api/quote/${symbol}`);
    if (!d || d.error) return null;
    return d;
  } catch (_) { return null; }
}

async function loadLiveFiiDii() {
  try {
    const d = await apiFetch('/api/fii-dii');
    if (!d || d.error) return;
    const fiiNet = d.fii?.net || d.fii_net;
    const diiNet = d.dii?.net || d.dii_net;
    const fiiEl = document.getElementById('live-fii-net');
    const diiEl = document.getElementById('live-dii-net');
    if (fiiEl && fiiNet !== undefined) {
      const v = Number(fiiNet);
      fiiEl.textContent = (v >= 0 ? '+' : '') + v.toLocaleString('en-IN') + ' Cr';
      fiiEl.className = v >= 0 ? 'green' : 'red';
    }
    if (diiEl && diiNet !== undefined) {
      const v = Number(diiNet);
      diiEl.textContent = (v >= 0 ? '+' : '') + v.toLocaleString('en-IN') + ' Cr';
      diiEl.className = v >= 0 ? 'green' : 'red';
    }
    // Update Chart.js FII/DII bar with live data
    if (fiiNet !== undefined && diiNet !== undefined) {
      updateFiiChartLive(Number(fiiNet), Number(diiNet));
    }
  } catch (_) {}
}

async function loadLiveMacro() {
  try {
    const d = await apiFetch('/api/macro');
    if (!d) return;
    const patch = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.textContent = val;
    };
    const rbi = d.rbi;
    if (rbi && !rbi.error) {
      patch('macro-repo', rbi.repo_rate ? rbi.repo_rate + '%' : null);
    }
    const mac = d.macro;
    if (mac && !mac.error) {
      const cpi = mac.cpi_inflation || mac.cpi;
      const gdp = mac.gdp_growth || mac.gdp;
      patch('macro-cpi', cpi ? Number(cpi).toFixed(2) + '%' : null);
      patch('macro-gdp', gdp ? Number(gdp).toFixed(1) + '%' : null);
    }
    const gsec = d.gsec;
    if (gsec && !gsec.error) {
      const y10 = gsec['10y'] || gsec.yield_10y;
      patch('macro-gsec', y10 ? Number(y10).toFixed(2) + '%' : null);
    }
  } catch (_) {}
}

async function loadLiveChart() {
  if (!isLive || !candleSeries) return;
  // Clear stale data immediately so switching stocks shows blank until new data loads
  try { candleSeries.setData([]); volumeSeries.setData([]); } catch(e) {}
  try {
    const sym = STOCKS[activeStockIdx]?.symbol;
    if (!sym) return;
    const periodMap =   { '5m': '1d', '15m': '5d', '1H': '1mo', '30m': '5d', '4H': '1mo', '1D': '5d', '1W': '1mo', '1M': '3mo', '3M': '6mo', '1Y': '2y' };
    const intervalMap = { '5m': '5m', '15m': '15m', '1H': '60m', '30m': '30m', '4H': '60m', '1D': '1d', '1W': '1d', '1M': '1d', '3M': '1d', '1Y': '1wk' };
    const period   = periodMap[activeTF]   || '3mo';
    const interval = intervalMap[activeTF] || '1d';
    const d = await apiFetch(`/api/historical/${sym}.NS?period=${period}&interval=${interval}`);
    if (!d || d.error || !d.data) return;
    const isIntraday = tfIsIntraday(activeTF);
    const candles = d.data.map(row => {
      let rawTime = row.date || row.Date;
      let t;
      if (typeof rawTime === 'number') {
        // Angel One already returns unix seconds for intraday
        t = rawTime;
      } else if (typeof rawTime === 'string' && rawTime.includes('T')) {
        // ISO 8601 with timezone e.g. "2026-03-28T09:15:00+05:30"
        t = Math.floor(new Date(rawTime).getTime() / 1000);
      } else if (typeof rawTime === 'string' && rawTime.includes(' ')) {
        // yfinance intraday "2026-03-29 09:15" — assume IST
        t = Math.floor(new Date(rawTime.replace(' ', 'T') + '+05:30').getTime() / 1000);
      } else {
        t = rawTime; // daily: ISO date string "2026-03-29"
      }
      return {
        time:  t,
        open:  row.open  || row.Open  || 0,
        high:  row.high  || row.High  || 0,
        low:   row.low   || row.Low   || 0,
        close: row.close || row.Close || 0,
        value: row.volume || row.Volume || 0,
      };
    }).filter(c => c.time && c.open);
    if (candles.length > 5) {
      candleSeries.setData(candles);
      const vol = candles.map(c => ({
        time: c.time, value: c.value,
        color: c.close >= c.open ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
      }));
      volumeSeries.setData(vol);
      // Render active indicators on live data
      if (activeIndicators.has('MA20'))  { ma20Series.setData(computeMA(candles, 20));   ma20Series.applyOptions({ visible: true }); }
      else ma20Series.applyOptions({ visible: false });
      if (activeIndicators.has('EMA50')) { ema50Series.setData(computeEMA(candles, 50)); ema50Series.applyOptions({ visible: true }); }
      else ema50Series.applyOptions({ visible: false });
      if (activeIndicators.has('BB'))    { const bb = computeBB(candles); bbUpperSeries.setData(bb.upper); bbLowerSeries.setData(bb.lower); bbUpperSeries.applyOptions({ visible: true }); bbLowerSeries.applyOptions({ visible: true }); }
      else { bbUpperSeries.applyOptions({ visible: false }); bbLowerSeries.applyOptions({ visible: false }); }
      if (activeIndicators.has('VWAP'))  { vwapSeries.setData(computeVWAP(candles));     vwapSeries.applyOptions({ visible: true }); }
      else vwapSeries.applyOptions({ visible: false });
      if (activeIndicators.has('RSI'))  updateRsiPane(candles);
      if (activeIndicators.has('MACD')) updateMacdPane(candles);
      chart?.timeScale().fitContent();
      setTimeout(restoreDrawings, 50);
    }
  } catch (_) {}
}

async function refreshLivePrices() {
  if (!isLive) return;
  const sym = STOCKS[activeStockIdx]?.symbol;
  if (!sym) return;
  const d = await loadLiveQuote(sym);
  if (!d) return;
  const ltp = d.ltp || d.last_price || d.price;
  const chg = d.change_percent || d.pChange || 0;
  const chgAmt = d.change || d.net_change || 0;
  if (!ltp) return;
  // Check price alerts for this symbol
  checkAlerts(STOCKS[activeStockIdx]?.symbol, +ltp);
  const ltpEl = document.getElementById('ch-ltp');
  const chgEl = document.getElementById('ch-change');
  if (ltpEl) ltpEl.textContent = '₹' + Number(ltp).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2});
  if (chgEl) {
    const sign = chgAmt >= 0 ? '+' : '';
    const cls = chgAmt >= 0 ? 'green' : 'red';
    chgEl.textContent = `${sign}₹${Number(chgAmt).toFixed(2)} (${sign}${Number(chg).toFixed(2)}%)`;
    chgEl.className = 'chart-change ' + cls;
  }
  const rows = document.querySelectorAll('.wl-item');
  if (rows[activeStockIdx]) {
    const priceEl = rows[activeStockIdx].querySelector('.wl-price');
    const chgElW  = rows[activeStockIdx].querySelector('.wl-chg');
    if (priceEl) priceEl.textContent = '₹' + Number(ltp).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2});
    if (chgElW) {
      const sign = chg >= 0 ? '+' : '';
      chgElW.textContent = sign + Number(chg).toFixed(2) + '%';
      chgElW.className = 'wl-chg ' + (chg >= 0 ? 'green' : 'red');
    }
  }
}

async function refreshAllWatchlistPrices() {
  if (!isLive) return;
  // Stagger requests to avoid rate limiting (1 per 500ms)
  for (let i = 0; i < Math.min(STOCKS.length, 10); i++) {
    await new Promise(r => setTimeout(r, 500));
    const s = STOCKS[i];
    const d = await loadLiveQuote(s.symbol);
    if (!d) continue;
    const ltp   = d.ltp || d.last_price || d.price;
    const chg   = d.change_percent || d.pChange || 0;
    if (!ltp) continue;
    stockPrices[i] = { ltp: +ltp, change: +chg, changeAmt: d.change || d.net_change || 0 };
    const row = document.querySelector(`.wl-item[data-idx="${i}"]`);
    if (!row) continue;
    const priceEl = row.querySelector('.wl-price');
    const chgEl   = row.querySelector('.wl-chg');
    if (priceEl) priceEl.textContent = '₹' + Number(ltp).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2});
    if (chgEl) {
      const sign = chg >= 0 ? '+' : '';
      chgEl.textContent = sign + Number(chg).toFixed(2) + '%';
      chgEl.className = 'wl-chg ' + (chg >= 0 ? 'green' : 'red');
    }
  }
}

async function connectRealData() {
  try {
    await apiFetch('/api/health');
    isLive = true;
    showLiveMode();
    document.getElementById('delay-banner')?.style.setProperty('display', 'none');
    await Promise.all([loadLiveNifty(), loadLiveVix(), loadLiveFiiDii(), loadLiveMacro()]);
    setTimeout(loadLiveChart, 500);
    setInterval(refreshLivePrices, 5000);   // active stock LTP every 5s
    setInterval(refreshAllWatchlistPrices, 15000); // all watchlist every 15s
    setInterval(loadLiveNifty, 15000);
    setInterval(loadLiveVix, 60000);
  } catch (_) {
    console.info('[finstack] Demo mode — start dashboard-api/main.py for live data');
  }
}

// ─── THEME TOGGLE ────────────────────────────────────────────────────────────

function toggleTheme() {
  const isLight = document.body.classList.toggle('light-theme');
  localStorage.setItem('arthex_theme', isLight ? 'light' : 'dark');
  document.getElementById('theme-label').textContent = isLight ? 'Dark' : 'Light';
  // Rebuild Chart.js charts with new theme colors
  rebuildPhase1Charts();
  // Update LightweightCharts colors
  if (chart) {
    chart.applyOptions({
      layout: { background: { color: isLight ? '#ffffff' : '#131722' }, textColor: isLight ? '#434651' : '#d1d4dc' },
      grid: { vertLines: { color: isLight ? '#e0e3eb' : '#2a2e39' }, horzLines: { color: isLight ? '#e0e3eb' : '#2a2e39' } },
    });
  }
}

function applyStoredTheme() {
  const t = localStorage.getItem('arthex_theme');
  if (t === 'light') {
    document.body.classList.add('light-theme');
    document.getElementById('theme-label').textContent = 'Dark';
    if (chart) chart.applyOptions({ layout: { background: { color: '#ffffff' }, textColor: '#434651' }, grid: { vertLines: { color: '#e0e3eb' }, horzLines: { color: '#e0e3eb' } } });
  }
}

// ─── CHART MAXIMIZE ──────────────────────────────────────────────────────────

let isMaximized = false;
function toggleChartMaximize() {
  isMaximized = !isMaximized;
  document.body.classList.toggle('chart-maximized', isMaximized);
  const icon = document.getElementById('maximize-icon');
  if (isMaximized) {
    icon.innerHTML = '<path d="M4 1H1v3M11 4V1H8M8 11h3V8M1 8v3h3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>';
  } else {
    icon.innerHTML = '<path d="M1 4V1h3M8 1h3v3M11 8v3H8M4 11H1V8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>';
  }
  // autoSize handles resize on maximize toggle automatically
}

// ─── TOOL STATUS BAR ─────────────────────────────────────────────────────────

const TOOL_HINTS = {
  cursor:  null,
  hline:   'H-Line active — click anywhere on chart to place a horizontal level',
  tline:   'Trend Line — click point 1 on chart',
  ray:     'Ray — click chart to place starting point (extends right)',
  fib:     'Fibonacci — click the high point on chart',
  rect:    null,
  eye:     null,
  magnet:  null,
  trash:   null,
};

function updateToolStatus(tool, override) {
  const bar = document.getElementById('tool-status');
  const txt = document.getElementById('tool-status-text');
  const msg = override || TOOL_HINTS[tool];
  if (msg) { bar.classList.add('visible'); txt.textContent = msg; }
  else { bar.classList.remove('visible'); }
}

// ESC to cancel drawing tool
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && activeDrawTool !== 'cursor') {
    document.getElementById('dt-cursor').click();
  }
});

// ─── RSI SUB-PANE ────────────────────────────────────────────────────────────

let rsiChart = null;
let rsiSeries = null;

function computeRSI(data, period = 14) {
  if (data.length < period + 1) return [];
  const result = [];
  let avgGain = 0, avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const diff = data[i].close - data[i - 1].close;
    if (diff > 0) avgGain += diff; else avgLoss += Math.abs(diff);
  }
  avgGain /= period; avgLoss /= period;
  const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  result.push({ time: data[period].time, value: +(100 - 100 / (1 + rs)).toFixed(2) });
  for (let i = period + 1; i < data.length; i++) {
    const diff = data[i].close - data[i - 1].close;
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? Math.abs(diff) : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    const rs2 = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result.push({ time: data[i].time, value: +(100 - 100 / (1 + rs2)).toFixed(2) });
  }
  return result;
}

function initRsiPane() {
  const container = document.getElementById('rsi-container');
  const isDark = !document.body.classList.contains('light-theme');
  rsiChart = LightweightCharts.createChart(container, {
    layout: { background: { color: isDark ? '#131722' : '#ffffff' }, textColor: isDark ? '#d1d4dc' : '#434651' },
    grid: { vertLines: { color: 'transparent' }, horzLines: { color: isDark ? '#2a2e39' : '#e0e3eb' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: isDark ? '#363a45' : '#d1d4dc', scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { visible: false },
    autoSize: true,
  });
  rsiSeries = rsiChart.addLineSeries({
    color: '#9c27b0', lineWidth: 1,
    priceLineVisible: false, lastValueVisible: true,
  });
  // Overbought/oversold reference lines
  const ob = rsiChart.addLineSeries({ color: 'rgba(239,83,80,0.4)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
  const os = rsiChart.addLineSeries({ color: 'rgba(38,166,154,0.4)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
  // These will be set with actual time range when data loads — store refs
  rsiChart._obSeries = ob;
  rsiChart._osSeries = os;
  // Sync time scale with main chart
  chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
    if (range && rsiChart) rsiChart.timeScale().setVisibleLogicalRange(range);
  });
}

function updateRsiPane(data) {
  if (!rsiChart || !rsiSeries) return;
  const rsiData = computeRSI(data, 14);
  if (!rsiData.length) return;
  rsiSeries.setData(rsiData);
  // Draw flat 70/30 reference lines using actual time range
  const t0 = rsiData[0].time, t1 = rsiData[rsiData.length - 1].time;
  rsiChart._obSeries.setData([{ time: t0, value: 70 }, { time: t1, value: 70 }]);
  rsiChart._osSeries.setData([{ time: t0, value: 30 }, { time: t1, value: 30 }]);
  rsiChart.timeScale().fitContent();
}

function toggleRsiPane(show) {
  const pane = document.getElementById('rsi-pane');
  if (show) {
    pane.classList.add('visible');
    if (!rsiChart) initRsiPane();
  } else {
    pane.classList.remove('visible');
  }
}

// ─── MACD SUB-PANE ───────────────────────────────────────────────────────────

let macdChart = null;
let macdLineSeries = null;    // MACD line (fast EMA - slow EMA)
let macdSignalSeries = null;  // Signal line (9 EMA of MACD)
let macdHistSeries = null;    // Histogram (MACD - Signal)

function computeMACD(data, fast = 12, slow = 26, signal = 9) {
  if (data.length < slow + signal) return { macd: [], signal: [], hist: [] };
  const emaFast = computeEMA(data, fast);
  const emaSlow = computeEMA(data, slow);
  // MACD line starts where slow EMA starts
  const startIdx = slow - 1;
  const macdLine = emaSlow.map((d, i) => ({
    time: d.time,
    value: +(emaFast[startIdx + i]?.value - d.value || 0).toFixed(2),
  }));
  // Signal = 9 EMA of MACD line
  const macdAsData = macdLine.map(d => ({ time: d.time, close: d.value }));
  const signalLine = computeEMA(macdAsData, signal);
  // Histogram = MACD - Signal (aligned by signal start)
  const sigStart = signal - 1;
  const hist = signalLine.map((s, i) => {
    const m = macdLine[sigStart + i];
    if (!m) return null;
    return { time: s.time, value: +(m.value - s.value).toFixed(2), color: m.value >= s.value ? 'rgba(38,166,154,0.6)' : 'rgba(239,83,80,0.6)' };
  }).filter(Boolean);
  return { macd: macdLine.slice(sigStart), signal: signalLine, hist };
}

function initMacdPane() {
  const container = document.getElementById('macd-container');
  const isDark = !document.body.classList.contains('light-theme');
  macdChart = LightweightCharts.createChart(container, {
    layout: { background: { color: isDark ? '#131722' : '#ffffff' }, textColor: isDark ? '#d1d4dc' : '#434651' },
    grid: { vertLines: { color: 'transparent' }, horzLines: { color: isDark ? '#2a2e39' : '#e0e3eb' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: isDark ? '#363a45' : '#d1d4dc', scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { visible: false },
    autoSize: true,
  });
  macdHistSeries = macdChart.addHistogramSeries({
    priceLineVisible: false, lastValueVisible: false,
    priceScaleId: 'macd',
  });
  macdLineSeries = macdChart.addLineSeries({
    color: '#2962ff', lineWidth: 1,
    priceLineVisible: false, lastValueVisible: false,
    priceScaleId: 'macd',
  });
  macdSignalSeries = macdChart.addLineSeries({
    color: '#ff9800', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed,
    priceLineVisible: false, lastValueVisible: false,
    priceScaleId: 'macd',
  });
  chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
    if (range && macdChart) macdChart.timeScale().setVisibleLogicalRange(range);
  });
}

function updateMacdPane(data) {
  if (!macdChart) return;
  const { macd, signal, hist } = computeMACD(data);
  if (!macd.length) return;
  macdLineSeries.setData(macd);
  macdSignalSeries.setData(signal);
  macdHistSeries.setData(hist);
  macdChart.timeScale().fitContent();
}

function toggleMacdPane(show) {
  const pane = document.getElementById('macd-pane');
  if (show) {
    pane.classList.add('visible');
    if (!macdChart) initMacdPane();
  } else {
    pane.classList.remove('visible');
  }
}

// ─── PHASE 1: SUPABASE CLOUD PERSISTENCE ─────────────────────────────────────
// Replace SUPABASE_URL and SUPABASE_ANON_KEY with your project values from:
// supabase.com → New project → Settings → API

const SUPABASE_URL      = '';   // e.g. 'https://xyzxyz.supabase.co'
const SUPABASE_ANON_KEY = '';   // your anon/public key

let supabase = null;

function initSupabase() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return;  // not configured yet
  try {
    supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    console.info('[arthex] Supabase connected — cloud sync enabled');
  } catch(e) {
    console.warn('[arthex] Supabase init failed:', e.message);
  }
}

async function cloudSaveDrawings(symbol, hlines, tlines) {
  if (!supabase) return;  // fall back to localStorage (always works)
  try {
    await supabase.from('drawings').upsert({
      symbol,
      hlines: JSON.stringify(hlines),
      tlines: JSON.stringify(tlines),
      updated_at: new Date().toISOString(),
    }, { onConflict: 'symbol' });
  } catch(e) {}
}

async function cloudLoadDrawings(symbol) {
  if (!supabase) return null;
  try {
    const { data } = await supabase.from('drawings').select('*').eq('symbol', symbol).single();
    if (!data) return null;
    return {
      hlines: JSON.parse(data.hlines || '[]'),
      tlines: JSON.parse(data.tlines || '[]'),
    };
  } catch(e) { return null; }
}

async function cloudSaveAlert(alert) {
  if (!supabase) return;
  try {
    await supabase.from('alerts').insert({ ...alert, created_at: new Date().toISOString() });
  } catch(e) {}
}

// ─── PHASE 1: INDIA SCREENER UPGRADE ─────────────────────────────────────────

const SCREENER_FILTERS = {
  sector: '', minPe: 0, maxPe: 999, minRoe: 0, marketCap: 'all'
};

function renderScreenerFilters() {
  const panel = document.getElementById('panel-screener');
  if (!panel || panel.querySelector('.screener-filters')) return;
  const bar = document.createElement('div');
  bar.className = 'screener-filters';
  bar.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;padding:8px 0 10px;border-bottom:1px solid var(--border);margin-bottom:8px;';
  bar.innerHTML = `
    <select id="sf-sector" style="background:var(--panel2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:4px 8px;font-size:11px;">
      <option value="">All Sectors</option>
      <option value="IT Services">IT Services</option>
      <option value="Banking">Banking</option>
      <option value="NBFC">NBFC</option>
      <option value="Oil & Gas">Oil & Gas</option>
      <option value="Pharma">Pharma</option>
      <option value="Auto">Auto</option>
      <option value="FMCG">FMCG</option>
      <option value="Power">Power</option>
      <option value="Infrastructure">Infrastructure</option>
      <option value="Telecom">Telecom</option>
      <option value="Cement">Cement</option>
    </select>
    <select id="sf-mcap" style="background:var(--panel2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:4px 8px;font-size:11px;">
      <option value="all">All Cap</option>
      <option value="large">Large Cap (>₹20,000 Cr)</option>
      <option value="mid">Mid Cap (₹5,000–20,000 Cr)</option>
      <option value="small">Small Cap (<₹5,000 Cr)</option>
    </select>
    <input id="sf-minpe" type="number" placeholder="Min P/E" style="width:70px;background:var(--panel2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:4px 8px;font-size:11px;" />
    <input id="sf-maxpe" type="number" placeholder="Max P/E" style="width:70px;background:var(--panel2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:4px 8px;font-size:11px;" />
    <input id="sf-minroe" type="number" placeholder="Min ROE%" style="width:80px;background:var(--panel2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:4px 8px;font-size:11px;" />
    <button onclick="applyScreenerFilters()" style="background:var(--accent);color:#fff;border:none;border-radius:4px;padding:4px 14px;font-size:11px;font-weight:600;cursor:pointer;">Filter</button>
    <button onclick="resetScreenerFilters()" style="background:none;border:1px solid var(--border2);color:var(--muted);border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer;">Reset</button>
    <button onclick="loadLiveScreener()" style="background:none;border:1px solid var(--accent);color:var(--accent);border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer;">Live Data</button>
  `;
  panel.insertBefore(bar, panel.firstChild);
}

function applyScreenerFilters() {
  const sector  = document.getElementById('sf-sector')?.value || '';
  const mcap    = document.getElementById('sf-mcap')?.value   || 'all';
  const minPe   = parseFloat(document.getElementById('sf-minpe')?.value)  || 0;
  const maxPe   = parseFloat(document.getElementById('sf-maxpe')?.value)  || 999;
  const minRoe  = parseFloat(document.getElementById('sf-minroe')?.value) || 0;
  const rows    = document.querySelectorAll('#screener-tbody tr');
  let visible = 0;
  rows.forEach(tr => {
    const tds = tr.querySelectorAll('td');
    if (tds.length < 7) return;
    const sym    = tds[0].textContent.trim();
    const sec    = tds[1].textContent.trim();
    const pe     = parseFloat(tds[3].textContent) || 0;
    const roe    = parseFloat(tds[4].textContent) || 0;
    const show   = (!sector || sec === sector)
                && pe >= minPe && pe <= maxPe
                && roe >= minRoe;
    tr.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  showToast(`${visible} stocks match filter`);
}

function resetScreenerFilters() {
  ['sf-sector','sf-mcap','sf-minpe','sf-maxpe','sf-minroe'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = el.tagName === 'SELECT' ? el.options[0]?.value : '';
  });
  document.querySelectorAll('#screener-tbody tr').forEach(tr => tr.style.display = '');
}

async function loadLiveScreener() {
  if (!isLive) { showToast('Connect API first (run dashboard-api)', 'error'); return; }
  showToast('Loading live screener data...');
  try {
    const d = await apiFetch('/api/screener');
    if (!d || d.error || !d.stocks) { showToast('Screener data unavailable', 'error'); return; }
    const tbody = document.getElementById('screener-tbody');
    tbody.innerHTML = '';
    d.stocks.forEach(row => {
      const isUp = row.chg_52w >= 0;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:600;cursor:pointer;" onclick="addSymbolFromSearch('${row.symbol}')">${row.symbol}</td>
        <td>${row.sector || '—'}</td>
        <td>₹${row.market_cap_cr ? Number(row.market_cap_cr).toLocaleString('en-IN') + ' Cr' : '—'}</td>
        <td>${row.pe ? row.pe.toFixed(1) + '×' : '—'}</td>
        <td class="${row.roe > 20 ? 'green' : ''}">${row.roe ? row.roe.toFixed(1) + '%' : '—'}</td>
        <td class="${isUp ? 'green' : 'red'}">${row.chg_52w != null ? (isUp ? '+' : '') + row.chg_52w.toFixed(1) + '%' : '—'}</td>
        <td>${row.volume || '—'}</td>
      `;
      tbody.appendChild(tr);
    });
    showToast(`${d.stocks.length} stocks loaded from live data`);
  } catch(e) {
    showToast('Screener fetch failed: ' + e.message, 'error');
  }
}

// ─── DRAWING PERSISTENCE (localStorage) ──────────────────────────────────────

const DRAWINGS_KEY = 'arthex_drawings';

function saveDrawings() {
  const hlines = drawnPriceLines.map(line => {
    try { return { type: 'hline', price: line._price }; } catch(e) { return null; }
  }).filter(Boolean);
  const tlines = drawnTrendLines.map(({ p1, p2 }) => ({ type: 'tline', p1, p2 }));
  const sym = STOCKS[activeStockIdx]?.symbol || 'ALL';
  const all = JSON.parse(localStorage.getItem(DRAWINGS_KEY) || '{}');
  all[sym] = { hlines, tlines, saved: Date.now() };
  localStorage.setItem(DRAWINGS_KEY, JSON.stringify(all));
}

function restoreDrawings() {
  const sym = STOCKS[activeStockIdx]?.symbol || 'ALL';
  const all = JSON.parse(localStorage.getItem(DRAWINGS_KEY) || '{}');
  const saved = all[sym];
  if (!saved) return;
  // Restore horizontal lines
  (saved.hlines || []).forEach(({ price }) => {
    if (!price) return;
    const line = candleSeries.createPriceLine({
      price, color: '#f7a600', lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true, title: fmt(price),
    });
    line._price = price;
    drawnPriceLines.push(line);
  });
  // Restore trend lines
  (saved.tlines || []).forEach(({ p1, p2 }) => {
    if (!p1 || !p2) return;
    let extendedData = buildTrendLineData(p1, p2);
    if (extendedData.length < 2) {
      const earlier = chartTimeToMs(p1.time) <= chartTimeToMs(p2.time) ? p1 : p2;
      const later   = chartTimeToMs(p1.time) <= chartTimeToMs(p2.time) ? p2 : p1;
      extendedData = [{ time: earlier.time, value: +earlier.price.toFixed(2) }, { time: later.time, value: +later.price.toFixed(2) }];
    }
    const series = chart.addLineSeries({ color: '#2962ff', lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    series.setData(extendedData);
    drawnTrendLines.push({ series, p1, p2 });
  });
}

// Patch hline creation to store price on the object
const _origCreatePriceLine = function(opts) {
  const line = candleSeries.createPriceLine(opts);
  line._price = opts.price;
  return line;
};

// ─── PRICE ALERTS ────────────────────────────────────────────────────────────

const ALERTS_KEY = 'arthex_alerts';
let priceAlerts = JSON.parse(localStorage.getItem(ALERTS_KEY) || '[]');
// {id, symbol, condition:'above'|'below', price, triggered:false}

function saveAlerts() {
  localStorage.setItem(ALERTS_KEY, JSON.stringify(priceAlerts));
}

function requestAlertPermission() {
  if (!('Notification' in window)) { showToast('Browser notifications not supported', 'error'); return; }
  Notification.requestPermission().then(p => {
    if (p === 'granted') {
      document.getElementById('alert-notify-btn').style.display = 'none';
      showToast('Notifications enabled — you will be alerted when price crosses your target');
    } else {
      showToast('Notification permission denied. Allow it in browser settings.', 'error');
    }
  });
}

function initAlertPanel() {
  // Populate symbol dropdown
  const sel = document.getElementById('alert-sym-sel');
  sel.innerHTML = '';
  STOCKS.forEach(s => {
    const o = document.createElement('option');
    o.value = s.symbol; o.textContent = s.symbol;
    sel.appendChild(o);
  });
  // Set dropdown to current active stock
  sel.value = STOCKS[activeStockIdx]?.symbol || STOCKS[0].symbol;
  // Show notification button if permission not yet granted
  if ('Notification' in window && Notification.permission !== 'granted') {
    document.getElementById('alert-notify-btn').style.display = 'block';
  }
  renderAlertList();
}

function addAlert() {
  const sym    = document.getElementById('alert-sym-sel').value;
  const cond   = document.getElementById('alert-cond-sel').value;
  const price  = parseFloat(document.getElementById('alert-price-inp').value);
  if (!sym || !cond || isNaN(price) || price <= 0) {
    showToast('Enter a valid price', 'error'); return;
  }
  priceAlerts.push({ id: Date.now(), symbol: sym, condition: cond, price, triggered: false });
  saveAlerts();
  renderAlertList();
  document.getElementById('alert-price-inp').value = '';
  showToast(`Alert set: ${sym} ${cond} ₹${fmt(price)}`);
}

function deleteAlert(id) {
  priceAlerts = priceAlerts.filter(a => a.id !== id);
  saveAlerts();
  renderAlertList();
}

function renderAlertList() {
  const container = document.getElementById('alert-list');
  if (!container) return;
  if (!priceAlerts.length) {
    container.innerHTML = '<div style="color:var(--muted);font-size:11px;">No alerts set. Add one above.</div>';
    return;
  }
  container.innerHTML = '';
  priceAlerts.forEach(a => {
    const row = document.createElement('div');
    row.className = 'alert-row' + (a.triggered ? ' triggered' : '');
    row.innerHTML = `
      <span class="alert-sym">${a.symbol}</span>
      <span class="alert-cond">${a.condition} ₹${fmt(a.price)}${a.triggered ? ' ✓ Triggered' : ''}</span>
      <button class="alert-del" onclick="deleteAlert(${a.id})" title="Delete">×</button>
    `;
    container.appendChild(row);
  });
}

function checkAlerts(symbol, ltp) {
  if (!priceAlerts.length) return;
  priceAlerts.forEach(a => {
    if (a.triggered || a.symbol !== symbol) return;
    const hit = (a.condition === 'above' && ltp >= a.price) ||
                (a.condition === 'below' && ltp <= a.price);
    if (!hit) return;
    a.triggered = true;
    saveAlerts();
    renderAlertList();
    const msg = `${symbol} ${a.condition === 'above' ? 'crossed above' : 'crossed below'} ₹${fmt(a.price)} — now ₹${fmt(ltp)}`;
    showToast('Alert: ' + msg);
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Arthex Price Alert', { body: msg, icon: '' });
    }
  });
}

// ─── INIT ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  renderWatchlist();
  try { initChart(); } catch(e) { console.error('[arthex] Chart init failed:', e); }
  initDrawToolbar();
  initBottomTabs();
  renderOptionsChain();
  renderScreener();
  renderFlowBars();
  renderNews();
  updateMarketStatus();
  setInterval(updateMarketStatus, 30000);
  setInterval(updatePrices, 3000);
  initAlertPanel();
  try { initPhase1Charts(); } catch(e) { console.warn('[arthex] Phase1 charts:', e); }
  renderScreenerFilters();
  initSupabase();

  if (isPro()) applyProFeatures();
  updateProBadge();
  applyStoredTheme();

  connectRealData();
});
