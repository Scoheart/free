import { asList, clipText, normalize, redactSecrets } from "../shared/text";

export type ClaimStatus = "" | "success" | "failed" | "needs-user";

export interface OfferLink {
  name?: string;
  action_url?: string;
  url?: string;
}

export interface GuideStep {
  step: string;
  detail: string;
  url: string;
  note: string;
}

type GuideInput = string | Partial<GuideStep> | null;

export interface Offer {
  id?: string;
  title?: string;
  name?: string;
  model?: string | null;
  product?: string;
  platform?: string;
  category?: string | null;
  kind?: string;
  summary?: string;
  free_terms?: string;
  desc?: string;
  description?: string;
  deadline?: string | null;
  expires_at?: string;
  expire_at?: string;
  expires?: string;
  expired?: boolean;
  is_expired?: boolean;
  superseded?: boolean;
  is_superseded?: boolean;
  superseded_by?: string | boolean | null;
  supersededBy?: string | boolean | null;
  url?: string;
  link?: string;
  source_url?: string;
  official_url?: string;
  terms_url?: string;
  docs_url?: string;
  providers?: (OfferLink | null)[];
  agents?: (OfferLink | null)[];
  models?: (OfferLink | null)[];
  claim_guide?: GuideInput[];
  claim_steps?: GuideInput[] | string;
  auto_claim?: { status?: string; note?: string; at?: string } | null;
}

export function titleOf(item: Offer): string {
  return String(item.title || item.name || item.model || "未命名");
}

export function itemUrl(item: Offer): string {
  return String(item.url || item.link || item.source_url || "");
}

export function deadlineOf(item: Offer): string {
  return item.deadline || item.expires_at || item.expire_at || item.expires || "";
}

export function deadlineMs(item: Offer): number {
  const time = Date.parse(deadlineOf(item));
  return Number.isNaN(time) ? Infinity : time;
}

export function isExpired(item: Offer, now: number): boolean {
  return item.expired === true || item.is_expired === true || deadlineMs(item) < now;
}

export function isSuperseded(item: Offer): boolean {
  if (item.superseded === true || item.is_superseded === true) return true;
  const replacedBy = item.superseded_by ?? item.supersededBy;
  return replacedBy != null && replacedBy !== false && String(replacedBy).trim() !== "";
}

export function autoClaimView(item: Offer): { kind: Exclude<ClaimStatus, "">; label: string; note: string; at: string } | null {
  const claim = item.auto_claim;
  if (!claim || typeof claim !== "object" || Array.isArray(claim)) return null;
  const status = normalize(claim.status);
  const note = clipText(redactSecrets(claim.note), 240);
  const at = clipText(redactSecrets(claim.at), 48);
  if (status === "success") return { kind: "success", label: "已自动领取", note, at };
  if (status === "failed") return { kind: "failed", label: "自动申请失败", note, at };
  if (status === "needs_user") return { kind: "needs-user", label: "需要你本人操作", note, at };
  return null;
}

export function summaryStatus(offers: readonly Offer[]): ClaimStatus {
  let status: ClaimStatus = "";
  for (const offer of offers) {
    const kind = autoClaimView(offer)?.kind;
    if (kind === "success") return kind;
    if (kind === "needs-user" || (!status && kind === "failed")) status = kind;
  }
  return status;
}

export const statusLabels: Record<ClaimStatus, string> = {
  "": "", success: "有已自动领取", "needs-user": "有需要本人操作", failed: "有自动申请失败",
};

function guideFromValue(entry: GuideInput): GuideStep | null {
  if (entry == null) return null;
  if (typeof entry === "string") {
    const detail = redactSecrets(entry).replace(/\s+/g, " ").trim();
    return detail ? { step: "", detail, url: "", note: "" } : null;
  }
  if (typeof entry !== "object" || Array.isArray(entry)) return null;
  const step = redactSecrets(entry.step).replace(/\s+/g, " ").trim();
  const detail = redactSecrets(entry.detail).trim();
  const note = redactSecrets(entry.note).replace(/\s+/g, " ").trim();
  const url = redactSecrets(entry.url).trim();
  return step || detail || note || url ? { step, detail, url, note } : null;
}

export function claimGuideOf(item: Offer): GuideStep[] {
  const guide = asList(item.claim_guide).map(guideFromValue).filter((step) => step !== null);
  if (guide.length) return guide;

  const raw = item.claim_steps;
  if (typeof raw !== "string") return asList(raw).map(guideFromValue).filter((step) => step !== null);
  if (!raw.trim()) return [];
  const lines = raw.trim().split(/\r?\n+/);
  const parts = lines.length === 1 ? raw.split(/[；;]+/) : lines;
  return parts.map((part) => part.replace(/\s+/g, " ").trim()
    .replace(/^如何领取[:：]\s*/, "").replace(/^\d+\s*[.、)]\s*/, ""))
    .filter(Boolean).map((detail) => ({ step: "", detail: redactSecrets(detail), url: "", note: "" }));
}

const deadlineDate = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", year: "numeric", month: "long", day: "numeric",
});
const deadlineTime = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

export function fmtDeadlineBJ(iso: string): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return "";
  return deadlineDate.format(time) + " " + deadlineTime.format(time) + "（北京时间）";
}
