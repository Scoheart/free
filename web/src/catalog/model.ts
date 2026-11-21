import { asList, normalize, redactSecrets } from "../shared/text";
import { claimGuideOf, deadlineMs, isExpired, isSuperseded, titleOf, type Offer } from "./offers";
import { categoryOf, platformOf, type CatalogKind } from "./platforms";

export interface PlatformGroup {
  name: string;
  slug: string;
  offers: Offer[];
  nearest: number;
}

export type CatalogGroups = Record<CatalogKind, PlatformGroup[]>;

const compareNames = (first: string, second: string) =>
  first.localeCompare(second, "zh-CN", { sensitivity: "base", numeric: true });

function slugify(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, "-")
    .replace(/[^a-z0-9\u3400-\u9fff-]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") || "platform";
}

function haystack(item: Offer): string {
  const steps = claimGuideOf(item).flatMap(({ step, detail, note }) => [step, detail, note]);
  const names = [item.providers, item.agents, item.models].flatMap((list) =>
    asList(list).map((entry) => entry?.name));
  const fields = [titleOf(item), item.model, item.product, item.summary, item.free_terms,
    item.desc, item.description, item.platform, ...steps, ...names];
  return normalize(redactSecrets(fields.filter(Boolean).join("\n")));
}

function compareOffers(a: Offer, b: Offer): number {
  const first = deadlineMs(a);
  const second = deadlineMs(b);
  return first === second ? compareNames(titleOf(a), titleOf(b)) : first - second;
}

export function offersByDeadline(groups: readonly PlatformGroup[]) {
  return groups
    .flatMap(({ name, offers }) => offers.map((offer) => ({ offer, platform: name })))
    .sort((a, b) => compareOffers(a.offer, b.offer));
}

function compareGroups(a: PlatformGroup, b: PlatformGroup): number {
  return a.nearest === b.nearest ? compareNames(a.name, b.name) : a.nearest - b.nearest;
}

export function buildGroups(items: readonly Offer[], now: number): PlatformGroup[] {
  const grouped = new Map<string, PlatformGroup>();
  for (const item of asList(items)) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    if (isExpired(item, now) || isSuperseded(item)) continue;
    const name = platformOf(item);
    let group = grouped.get(name);
    if (!group) {
      group = { name, slug: "", offers: [], nearest: Infinity };
      grouped.set(name, group);
    }
    group.offers.push(item);
    group.nearest = Math.min(group.nearest, deadlineMs(item));
  }

  const used = new Set<string>();
  const groups = [...grouped.values()].sort(compareGroups);
  for (const group of groups) {
    group.offers.sort(compareOffers);
    const base = slugify(group.name);
    let slug = base;
    for (let i = 2; used.has(slug); i++) slug = base + "-" + i;
    group.slug = slug;
    used.add(slug);
  }
  return groups;
}

export function groupsInKind(groups: readonly PlatformGroup[], kind: CatalogKind): PlatformGroup[] {
  return groups.flatMap((group) => {
    const offers = group.offers.filter((offer) => categoryOf(offer) === kind);
    return offers.length ? [{ ...group, offers, nearest: deadlineMs(offers[0]) }] : [];
  }).sort(compareGroups);
}

export function filterGroups(groups: PlatformGroup[], query: string): PlatformGroup[] {
  const search = normalize(query);
  if (!search) return groups;
  return groups.flatMap((group) => {
    if (normalize(group.name).includes(search)) return [group];
    const offers = group.offers.filter((offer) => haystack(offer).includes(search));
    return offers.length ? [{ ...group, offers }] : [];
  });
}

export function groupBySlug(groups: readonly PlatformGroup[], slug: string) {
  return groups.find((group) => group.slug === slug);
}

export function countOffers(groups: readonly PlatformGroup[]): number {
  return groups.reduce((sum, group) => sum + group.offers.length, 0);
}
