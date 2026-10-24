import { useEffect, useState } from 'react';

export interface Route { name: string; param?: string; query: URLSearchParams }

function parse(): Route {
  const raw = window.location.hash.replace(/^#\/?/, '');
  const [path, qs] = raw.split('?');
  const [name, param] = path.split('/');
  return { name: name || 'overview', param: param ? decodeURIComponent(param) : undefined, query: new URLSearchParams(qs || '') };
}

export function useRoute(): Route {
  const [r, setR] = useState(parse);
  useEffect(() => {
    const f = () => setR(parse());
    window.addEventListener('hashchange', f);
    return () => window.removeEventListener('hashchange', f);
  }, []);
  return r;
}

export const go = (hash: string) => { window.location.hash = hash; };
