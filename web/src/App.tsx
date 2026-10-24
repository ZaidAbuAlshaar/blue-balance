import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, post } from './api';
import { useStore, useT, type User } from './store';
import { go, useRoute } from './route';
import { Loading } from './ui';
import { Overview } from './screens/Overview';
import { CaseDetail } from './screens/CaseDetail';
import { Ask } from './screens/Ask';
import { Crew } from './screens/Crew';
import { WorkOrders } from './screens/WorkOrders';
import { MapEdits } from './screens/MapEdits';
import { Transparency } from './screens/Transparency';

// Demo account ids and roles (passwords are never shipped in the bundle).
export const DEMO_USERS = [
  { user_id: 'eng_a', ar: 'مهندس أ', en: 'Engineer A', role: 'engineer' },
  { user_id: 'eng_b', ar: 'مهندس ب', en: 'Engineer B', role: 'engineer' },
  { user_id: 'insp_1', ar: 'مفتش ١', en: 'Inspector 1', role: 'inspector' },
  { user_id: 'admin_1', ar: 'مسؤول', en: 'Admin', role: 'admin' },
];
const ROLE: Record<string, string> = { engineer: 'مهندس · engineer', inspector: 'مفتش · inspector', admin: 'مسؤول · admin' };

const NAV: { group: [string, string]; items: { id: string; ar: string; en: string }[] }[] = [
  { group: ['اكتشف', 'Detect'], items: [{ id: 'overview', ar: 'نظرة عامة', en: 'Overview' }, { id: 'case', ar: 'تفاصيل الحالة', en: 'Case detail' }] },
  { group: ['تحقّق', 'Verify'], items: [{ id: 'crew', ar: 'تقرير الطاقم', en: 'Crew report' }, { id: 'work-orders', ar: 'أوامر العمل', en: 'Work orders' }, { id: 'ask', ar: 'اسأل المساعد', en: 'Ask the agent' }] },
  { group: ['تذكّر', 'Remember'], items: [{ id: 'map-edits', ar: 'تعديلات الخريطة', en: 'Map edits' }] },
  { group: ['الثقة', 'Trust'], items: [{ id: 'transparency', ar: 'الشفافية', en: 'Transparency' }] },
];

function Login() {
  const setUser = useStore((s) => s.setUser);
  const pending = useStore((s) => s.pendingUser);
  const t = useT();
  const [uid, setUid] = useState(pending ?? 'eng_a');
  const [pw, setPw] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const qc = useQueryClient();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const u = await post<User>('/api/login', { user_id: uid, password: pw });
      qc.clear();
      setUser(u);
    } catch (x) {
      setErr((x as ApiError).status === 401 ? 'كلمة السر أو المستخدم غلط · wrong user or password' : String((x as Error).message));
    } finally { setBusy(false); }
  }
  return (
    <div className="login-page">
      <form className="login" onSubmit={submit}>
        <div className="brand-lg"><Mark /> <div><div className="brand-ar">ميزان الأزرق</div><div className="brand-en">Blue Balance</div></div></div>
        <p className="login-tag">{t('اكتشف · تحقّق · تذكّر — وين يروح المفتش أول؟', 'Detect · Verify · Remember — where do inspectors go first?')}</p>
        <fieldset>
          <legend>{t('حساب تجريبي', 'Demo account')} <span className="muted">· Simulated</span></legend>
          {DEMO_USERS.map((u) => (
            <label key={u.user_id} className={`user-opt ${uid === u.user_id ? 'on' : ''}`}>
              <input type="radio" name="uid" value={u.user_id} checked={uid === u.user_id} onChange={() => setUid(u.user_id)} />
              <span><b>{u.ar}</b> · {u.en}</span>
              <span className="muted mono" dir="ltr">{u.user_id}</span>
              <span className="role">{ROLE[u.role]}</span>
            </label>
          ))}
        </fieldset>
        <label className="field">
          <span>{t('كلمة السر', 'Password')}</span>
          <input type="password" name="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" dir="ltr" autoFocus />
        </label>
        {err && <div className="error" role="alert">{err}</div>}
        <button className="btn primary" type="submit" disabled={busy || !pw}>{busy ? '…' : t('دخول', 'Sign in')}</button>
        <p className="muted small">{t('الحسابات للعرض المحلي فقط.', 'Accounts are for the local demo only.')}</p>
      </form>
    </div>
  );
}

function Mark() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden className="mark">
      <rect width="34" height="34" rx="7" fill="#1D6FA3" />
      <path d="M7 12h20M17 8v18M10 12l-3 7h6zM24 12l-3 7h6z" stroke="#fff" strokeWidth="1.8" fill="none" strokeLinejoin="round" />
      <path d="M11 26h12" stroke="#fff" strokeWidth="1.8" />
    </svg>
  );
}

function Header() {
  const { user, setUser, setPendingUser, lang, setLang } = useStore();
  const qc = useQueryClient();
  const t = useT();
  const health = useQuery({ queryKey: ['health'], queryFn: () => api('/api/health'), refetchInterval: 30_000 });
  async function switchTo(id: string) {
    await post('/api/logout').catch(() => null);
    qc.clear();
    setPendingUser(id && id !== '__logout' ? id : null);
    setUser(null);
  }
  const ol = health.data?.ollama;
  return (
    <header className="topbar">
      <div className="tb-title">
        <span className="tb-motto">{t('القمر الصناعي يكتشف · الطاقم يتحقق · الخريطة تتذكر', 'The satellite detects · the crew verifies · the map remembers')}</span>
      </div>
      <div className="tb-right">
        <span className={`health ${ol?.up ? 'up' : 'down'}`} title="Ollama">
          <span className="dot" /> {ol?.up ? t('النماذج المحلية تعمل', 'Local models up') : t('النماذج المحلية متوقفة', 'Local models down')}
        </span>
        <button className="btn ghost sm" onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')} aria-label="toggle language">{lang === 'ar' ? 'English' : 'عربي'}</button>
        {user && (
          <div className="userbox">
            <div className="ub-name">{user.display_name}</div>
            <div className="ub-role">{ROLE[user.role] ?? user.role}</div>
            <select aria-label="switch user" value="" onChange={(e) => switchTo(e.target.value)} className="ub-switch">
              <option value="">{t('تبديل المستخدم…', 'Switch user…')}</option>
              {DEMO_USERS.filter((u) => u.user_id !== user.user_id).map((u) => <option key={u.user_id} value={u.user_id}>{u.ar} · {u.en}</option>)}
              <option value="__logout">{t('خروج', 'Log out')}</option>
            </select>
          </div>
        )}
      </div>
    </header>
  );
}

function Sidebar({ current }: { current: string }) {
  const selected = useStore((s) => s.selected);
  return (
    <nav className="sidebar" aria-label="main">
      <div className="brand"><Mark /><div><div className="brand-ar">ميزان الأزرق</div><div className="brand-en">Blue Balance · Karak</div></div></div>
      {NAV.map((g) => (
        <div key={g.group[1]} className="nav-group">
          <div className="nav-gh">{g.group[0]} <span>· {g.group[1]}</span></div>
          {g.items.map((it) => {
            const href = it.id === 'case' ? `#/case/${encodeURIComponent(selected ?? 'KRK-T-002')}` : `#/${it.id}`;
            return (
              <a key={it.id} href={href} className={`nav-item ${current === it.id ? 'on' : ''}`} data-nav={it.id}>
                <span className="ni-ar">{it.ar}</span>
                <span className="ni-en">{it.en}</span>
              </a>
            );
          })}
        </div>
      ))}
      <div className="side-foot">{'كل الأرقام مع فاصل ووسم دليل'}<br /><span>Every number carries an interval and an evidence label</span></div>
    </nav>
  );
}

export function App() {
  const { user, setUser, lang } = useStore();
  const route = useRoute();
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  }, [lang]);
  useEffect(() => {
    api<User>('/api/me').then(setUser).catch(() => setUser(null)).finally(() => setChecked(true));
  }, []);
  if (!checked) return <Loading />;
  if (!user) return <Login />;
  let screen;
  switch (route.name) {
    case 'case': screen = <CaseDetail id={route.param ?? 'KRK-T-002'} />; break;
    case 'ask': screen = <Ask />; break;
    case 'crew': screen = <Crew />; break;
    case 'work-orders': screen = <WorkOrders prefillCase={route.query.get('case')} />; break;
    case 'map-edits': screen = <MapEdits />; break;
    case 'transparency': screen = <Transparency />; break;
    default: screen = <Overview />;
  }
  return (
    <div className="shell">
      <Sidebar current={route.name} />
      <div className="main">
        <Header />
        <main className="content" key={route.name + (route.param ?? '')}>{screen}</main>
      </div>
    </div>
  );
}

export { go };
