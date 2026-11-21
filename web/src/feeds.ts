import type { Offer } from "./catalog/offers";
import type { CatalogPage, Section } from "./routes";
import type { VpsData } from "./vps/model";

async function readJson(section: Section): Promise<unknown> {
  const response = await fetch("../" + section + "/index.json", { cache: "no-cache" });
  if (!response.ok) throw new Error("Could not load site data");
  return response.json();
}

export async function loadItems(section: CatalogPage): Promise<Offer[]> {
  const value = await readJson(section);
  if (!Array.isArray(value)) throw new Error("Expected a catalog array");
  return value;
}

export async function loadVps(): Promise<VpsData> {
  const value = await readJson("vps");
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected a VPS object");
  return value as VpsData;
}
