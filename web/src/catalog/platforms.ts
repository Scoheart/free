import { asList, hostnameOf, normalize } from "../shared/text";
import { AGENT_VENUES, FORCE_PROVIDER, HOST_LABELS, SOURCE_HOSTS } from "./platform-directory";
import { itemUrl, type Offer, type OfferLink } from "./offers";

export type CatalogKind = "providers" | "agents";

const specialNames: Record<string, string> = {
  ai: "AI", api: "API", llm: "LLM", openai: "OpenAI", openrouter: "OpenRouter",
  huggingface: "Hugging Face", deepseek: "DeepSeek", chatgpt: "ChatGPT",
  github: "GitHub", nvidia: "NVIDIA", aws: "AWS",
};

function prettifyToken(token: string): string {
  if (Object.hasOwn(specialNames, token)) return specialNames[token];
  return token.split(/[-_]+/).filter(Boolean).map((word) => {
    if (Object.hasOwn(specialNames, word)) return specialNames[word];
    return word.length <= 2 ? word.toUpperCase() : word[0].toUpperCase() + word.slice(1);
  }).join(" ");
}

function platformFromUrl(url: string): string {
  const host = hostnameOf(url);
  if (!host) return "";
  if (host === "vercel.com" && /ai-gateway/i.test(url)) return "Vercel AI Gateway";
  const parts = host.split(".");
  for (let index = 0; index < parts.length; index++) {
    const candidate = parts.slice(index).join(".");
    if (Object.hasOwn(HOST_LABELS, candidate)) return HOST_LABELS[candidate];
  }
  const suffix = parts.at(-1);
  let domain = parts.at(-2) ?? parts[0];
  if (/^(co|com|org|net|gov|ac)$/.test(domain) && parts.length >= 3) domain = parts[parts.length - 3];
  if (suffix && Object.hasOwn(HOST_LABELS, domain + "." + suffix)) return HOST_LABELS[domain + "." + suffix];
  return Object.hasOwn(HOST_LABELS, domain) ? HOST_LABELS[domain] : prettifyToken(domain);
}

function linkUrls(list: readonly (OfferLink | null)[] | undefined): string[] {
  return asList(list).flatMap((entry) => {
    const href = entry?.action_url || entry?.url;
    return href ? [String(href)] : [];
  });
}

export function platformOf(item: Offer): string {
  const name = String(item.platform ?? "").replace(/\s+/g, " ").trim();
  if (name) return name;

  const urls = [
    ...linkUrls(item.providers), item.official_url, item.terms_url,
    ...linkUrls(item.models), ...linkUrls(item.agents), item.docs_url, itemUrl(item),
  ];
  let fallback = "";
  for (const url of urls) {
    if (!url) continue;
    const label = platformFromUrl(url);
    if (!label) continue;
    fallback ||= label;
    if (!Object.hasOwn(SOURCE_HOSTS, hostnameOf(url))) return label;
  }
  return fallback || "其他";
}

const providerVenue = /\b(api|apis|gateway|router|inference|studio|cloud|nim|endpoint|endpoints)\b|开放平台|网关|路由/;
const agentVenue = /(?:^| )(code|coder|cli|ide|desktop|agent)$|代码编辑器|编程 agent|编码 agent|coding agent|\bide\b|\bcli\b|\bdesktop\b/;

function normalizeVenue(name: unknown): string {
  return normalize(name)
    .replace(/[（(][^）)]*[）)]/g, " ")
    .replace(/\b\d+(?:\.\d+)+\b/g, " ")
    .replace(/[/|、+]+/g, " ")
    .replace(/\s+/g, " ").trim();
}

function nameLooksLikeAgent(name: unknown): boolean {
  const venue = normalizeVenue(name);
  if (!venue || Object.hasOwn(FORCE_PROVIDER, venue)) return false;
  if (Object.hasOwn(AGENT_VENUES, venue)) return true;
  if (providerVenue.test(venue)) return false;
  const words = venue.split(" ");
  return Object.hasOwn(AGENT_VENUES, words[0]) || agentVenue.test(venue) ||
    /^[a-z0-9][a-z0-9-]{1,22}code$/.test(words.at(-1) ?? "");
}

function leadIsCodingTool(lead: string): boolean {
  const name = normalizeVenue(lead);
  if (name.startsWith("claude code")) return true;
  return name.split(" ")[0] !== "claude" && nameLooksLikeAgent(name);
}

export function categoryOf(item: Offer): CatalogKind {
  const explicit = normalize(item.category ?? item.kind);
  if (explicit === "agent" || explicit === "agents") return "agents";
  if (explicit === "provider" || explicit === "providers") return "providers";

  const platform = platformOf(item);
  if (Object.hasOwn(FORCE_PROVIDER, normalizeVenue(platform))) return "providers";
  const platformAgent = nameLooksLikeAgent(platform);
  const title = String(item.title ?? "");
  const lead = title.trim().match(/^([^:：]{1,48})[:：]/)?.[1] ?? "";
  const product = String(item.product ?? "");
  const text = normalize(title + " " + product);
  const apiCredit = /api\s*额度|api credits|每月 api|api key/.test(text);
  if (apiCredit && !platformAgent && !leadIsCodingTool(lead) && !text.includes("code review")) return "providers";
  if (platformAgent || nameLooksLikeAgent(lead) || nameLooksLikeAgent(product.split(/\s*[·•]\s*/)[0])) return "agents";

  const inAppAgent = asList(item.agents).length && !asList(item.providers).length &&
    /代码编辑器|编程\s*agent|编码\s*agent|coding agent|终端编程|桌面编程|\bcli\b|\bide\b/.test(normalize(text + " " + platform));
  return inAppAgent ? "agents" : "providers";
}

export function goUrl(item: Offer): string {
  const direct = itemUrl(item);
  const host = hostnameOf(direct);
  if (host && !Object.hasOwn(SOURCE_HOSTS, host)) return direct;
  for (const list of [item.providers, item.agents, item.models]) {
    const href = linkUrls(list)[0];
    if (href) return href;
  }
  return direct;
}
