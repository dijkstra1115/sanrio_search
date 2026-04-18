async page => {
  const ignoredHosts = new Set([
    "google.com",
    "www.google.com",
    "accounts.google.com",
    "support.google.com",
  ]);

  try {
    await page.waitForURL(/google\..*\/search\?/, { timeout: 15000 });
  } catch {
  }

  try {
    await page.waitForLoadState("domcontentloaded", { timeout: 5000 });
  } catch {
  }

  await page.waitForFunction(() => {
    const links = [...document.querySelectorAll("a[href]")];
    return links.some(link => {
      const href = link.getAttribute("href") || "";
      return /^https?:\/\//i.test(href) && (link.textContent || "").trim();
    });
  }, { timeout: 20000 });

  const candidates = await page.locator("a[href]").evaluateAll((links, hosts) => {
    const isVisible = link => {
      const rect = link.getBoundingClientRect();
      const style = window.getComputedStyle(link);
      const text = (link.textContent || "").trim();
      return !!text && rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    };

    return links.map(link => {
      try {
        const url = new URL(link.href);
        return {
          href: url.href,
          host: url.hostname.toLowerCase(),
          text: (link.textContent || "").trim(),
          visible: isVisible(link),
        };
      } catch {
        return null;
      }
    }).filter(Boolean).filter(link => link.visible && !hosts.includes(link.host));
  }, [...ignoredHosts]);

  const official = candidates.find(link => link.host === "sanrio.co.jp" || link.host === "www.sanrio.co.jp");
  const officialSubdomain = candidates.find(link => link.host.endsWith(".sanrio.co.jp"));
  const fallback = candidates.find(link => link.host.endsWith(".jp"));
  const match = official || officialSubdomain || fallback;

  if (!match) {
    throw new Error("No preferred Sanrio or .jp URL found in Google Lens results");
  }

  return {
    matched_url: match.href,
    matched_host: match.host,
    matched_text: match.text,
    matched_rule: official ? "sanrio-official" : officialSubdomain ? "sanrio-subdomain" : "jp",
  };
}
