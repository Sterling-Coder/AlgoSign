"use client";

const KEY = "algosign.watchlist";
const EVENT = "algosign.watchlist.changed";

export function getWatchlist(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

function save(list: string[]) {
  localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event(EVENT));
}

export function isWatched(symbol: string): boolean {
  return getWatchlist().includes(symbol);
}

export function toggleWatch(symbol: string): boolean {
  const list = getWatchlist();
  const i = list.indexOf(symbol);
  if (i >= 0) {
    list.splice(i, 1);
    save(list);
    return false;
  }
  list.unshift(symbol);
  save(list);
  return true;
}

export function removeWatch(symbol: string) {
  save(getWatchlist().filter((s) => s !== symbol));
}

export function onWatchlistChange(cb: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(EVENT, cb);
  return () => window.removeEventListener(EVENT, cb);
}
