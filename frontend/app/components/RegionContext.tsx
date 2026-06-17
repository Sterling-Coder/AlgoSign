"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Region = "IN" | "US" | "WORLD";

export const REGION_LABEL: Record<Region, string> = {
  IN: "India",
  US: "US",
  WORLD: "World",
};

const Ctx = createContext<{
  region: Region;
  setRegion: (r: Region) => void;
}>({ region: "US", setRegion: () => {} });

export function RegionProvider({ children }: { children: React.ReactNode }) {
  const [region, setRegionState] = useState<Region>("US");

  useEffect(() => {
    const saved = localStorage.getItem("algosign.region") as Region | null;
    if (saved && ["IN", "US", "WORLD"].includes(saved)) setRegionState(saved);
  }, []);

  const setRegion = (r: Region) => {
    setRegionState(r);
    localStorage.setItem("algosign.region", r);
  };

  return <Ctx.Provider value={{ region, setRegion }}>{children}</Ctx.Provider>;
}

export const useRegion = () => useContext(Ctx);
