import { useEffect } from "react";
import { parseRouteHash, sectionUrl } from "../routes";
import { PageFooter, PageHeader } from "../shared/ui";
import { VpsContent } from "./content";
import { updatedLine, type VpsData } from "./model";
import "./styles.css";

export function VpsPage({ data }: { data: VpsData }) {
  useEffect(() => {
    const followHash = () => {
      const route = parseRouteHash(window.location.hash);
      if (route.page === "agent" || route.page === "provider") {
        window.location.replace(sectionUrl(route.page, route.slug, "vps"));
      } else if (route.slug) {
        document.getElementById(route.slug)?.scrollIntoView();
      }
    };
    followHash();
    window.addEventListener("hashchange", followHash);
    return () => window.removeEventListener("hashchange", followHash);
  }, []);

  return (
    <div className="app">
      <div className="chrome"><PageHeader page="vps" stats={updatedLine(data)} /></div>
      <div className="layout">
        <main className="detail"><VpsContent data={data} /></main>
        <PageFooter page="vps" />
      </div>
    </div>
  );
}
