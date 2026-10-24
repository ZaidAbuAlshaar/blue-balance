import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, post } from './api';
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

const ROLEBAR_KEY = 'bb_rolebar_hidden';

/** Top bar for picking a demo role. No password; the server still enforces every role rule. */
function RoleBar() {
  const user = useStore((s) => s.user);
  const setUser = useStore((s) => s.setUser);
  const qc = useQueryClient();
  const t = useT();
  const [hidden, setHidden] = useState(() => {
    try { return localStorage.getItem(ROLEBAR_KEY) === '1'; } catch { return false; }
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  function toggle(h: boolean) {
    setHidden(h);
    try { localStorage.setItem(ROLEBAR_KEY, h ? '1' : '0'); } catch { /* ignore */ }
  }
  async function pick(id: string) {
    if (id === user?.user_id) return;
    setBusy(id); setErr(null);
    try {
      const u = await post<User>('/api/demo/switch', { user_id: id });
      qc.clear();
      setUser(u);
    } catch (x) {
      setErr(String((x as Error).message));
    } finally { setBusy(null); }
  }
  const current = DEMO_USERS.find((u) => u.user_id === user?.user_id);
  if (hidden) {
    return (
      <button className="rolebar-show" onClick={() => toggle(false)} aria-label={t('إظهار شريط الأدوار', 'Show role bar')}>
        {t('الدور', 'Role')}: <b>{current ? t(current.ar, current.en) : '—'}</b> · {t('إظهار', 'Show')}
      </button>
    );
  }
  return (
    <div className="rolebar" role="toolbar" aria-label={t('اختيار الدور', 'Choose your role')}>
      <span className="rb-label">{t('اختار دورك', 'Choose your role')} <span className="rb-note">· {t('عرض تجريبي', 'demo')}</span></span>
      <div className="rb-opts">
        {DEMO_USERS.map((u) => {
          const on = user?.user_id === u.user_id;
          return (
            <button key={u.user_id} className={`rb-opt ${on ? 'on' : ''}`} aria-pressed={on} disabled={busy !== null}
              onClick={() => pick(u.user_id)} data-user={u.user_id}>
              <b>{t(u.ar, u.en)}</b>
              <span>{ROLE[u.role]}</span>
            </button>
          );
        })}
      </div>
      {err && <span className="rb-err" role="alert">{err}</span>}
      <button className="btn ghost sm rb-hide" onClick={() => toggle(true)}>{t('إخفاء الشريط', 'Hide bar')}</button>
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
  const { user, lang, setLang } = useStore();
  const t = useT();
  const health = useQuery({ queryKey: ['health'], queryFn: () => api('/api/health'), refetchInterval: 30_000 });
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
    api<User>('/api/me')
      .then(setUser)
      .catch(() => post<User>('/api/demo/switch', { user_id: 'eng_a' }).then(setUser).catch(() => setUser(null)))
      .finally(() => setChecked(true));
  }, []);
  if (!checked) return <Loading />;
  if (!user) return <div className="content"><div className="error" role="alert">{'ما قدرنا نبدأ الجلسة · Could not start a session. Is the server running?'}</div></div>;
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
        <RoleBar />
        <Header />
        <main className="content" key={route.name + (route.param ?? '')}>{screen}</main>
      </div>
    </div>
  );
}

export { go };
