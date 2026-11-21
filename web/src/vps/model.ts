import { beijingTime, textOf } from "../shared/text";

interface Link {
  url?: string;
  label?: string;
}
interface Spec {
  label?: string;
  value?: string;
}
export interface Conditions {
  card_required?: boolean | null;
  card_notes?: string;
  region_limits?: string;
  idle_reclaim?: string;
  deadline?: string;
  deadline_note?: string;
}
interface Post extends Link {
  time_beijing?: string;
  author?: string;
}
export interface FreeOffer {
  id?: string;
  provider?: string;
  type?: string;
  type_label?: string;
  official_url?: string;
  specs?: (Spec | null)[];
  free_conditions?: Conditions | null;
  posts?: (Post | null)[];
  notes?: string;
}
export interface StockPlan {
  key?: string;
  display_name?: string;
  stock?: string;
  limited?: boolean;
  config?: string;
  specs?: (Spec | null)[];
  price?: string;
  last_restock?: string;
  order_urls?: (Link | null)[];
}
export interface Vendor {
  id?: string;
  name?: string;
  checked_at_beijing?: string;
  official_url?: string;
  sources?: ({ name?: string; url?: string } | null)[];
  plans?: (StockPlan | null)[];
}
interface SalePlan extends Link {
  name?: string;
  price?: string;
  specs?: string;
}
export interface OfficialSale {
  provider?: string;
  status?: string;
  status_label?: string;
  status_kind?: string;
  orderable_now?: boolean;
  sale_hub?: string;
  summary?: string;
  sources?: ({ title?: string; url?: string } | null)[];
  plans?: (SalePlan | null)[];
}
export interface Lead extends Link {
  source?: string;
  note?: string;
}

export interface VpsData {
  schema_version?: number;
  sample?: boolean | string;
  updated_at_beijing?: string;
  scanned_at_beijing?: { stock?: string; black_friday?: string; free_vps?: string };
  free_vps?: (FreeOffer | null)[];
  stock?: { providers?: (Vendor | null)[]; source_notes?: string[] };
  black_friday?: { official?: (OfficialSale | null)[]; leads?: (Lead | null)[]; date_note?: string };
}

export function updatedLine(data: VpsData) {
  const scans = data.scanned_at_beijing;
  const time = textOf(data.updated_at_beijing) || textOf(scans?.black_friday || scans?.stock || scans?.free_vps);
  return time ? "最后更新 " + beijingTime(time) : "最后更新时间未知";
}
