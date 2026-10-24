import { create } from 'zustand';

export type Lang = 'ar' | 'en';
export interface User { user_id: string; role: string; display_name: string }

function initialLang(): Lang {
  try { return (localStorage.getItem('bb_lang') as Lang) || 'ar'; } catch { return 'ar'; }
}

interface S {
  lang: Lang;
  setLang: (l: Lang) => void;
  user: User | null;
  setUser: (u: User | null) => void;
  pendingUser: string | null;
  setPendingUser: (u: string | null) => void;
  selected: string | null;
  select: (id: string | null) => void;
}

export const useStore = create<S>((set) => ({
  lang: initialLang(),
  setLang: (lang) => {
    try { localStorage.setItem('bb_lang', lang); } catch { /* ignore */ }
    set({ lang });
  },
  user: null,
  setUser: (user) => set({ user }),
  pendingUser: null,
  setPendingUser: (pendingUser) => set({ pendingUser }),
  selected: null,
  select: (selected) => set({ selected }),
}));

/** Pick the string for the active language. */
export function useT() {
  const lang = useStore((s) => s.lang);
  return (ar: string, en: string) => (lang === 'ar' ? ar : en);
}
