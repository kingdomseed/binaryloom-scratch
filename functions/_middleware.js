// Private shares open only with ?k=<key>, which is swapped for a cookie scoped
// to the share's path. Only SHA-256 hashes of keys are deployed; scratch.py
// keeps the keys outside this tree.
import shares from "../private.json";

const hashes = new Map(shares.map((s) => [s.slug, s.keyHash]));
const HIDDEN = new Set(["private.json", "functions"]);
const MONTH = 60 * 60 * 24 * 30;

async function sha256(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function notFound() {
  return new Response("Not found", {
    status: 404,
    headers: { "cache-control": "no-store", "x-robots-tag": "noindex" },
  });
}

function cookie(request, name) {
  for (const part of (request.headers.get("cookie") || "").split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return null;
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const first = decodeURIComponent(url.pathname.split("/")[1] || "");
  if (HIDDEN.has(first)) return notFound();
  const expected = hashes.get(first);
  if (!expected) return context.next();

  const name = `scratch_${first}`;
  const given = url.searchParams.get("k");
  if (given !== null) {
    if ((await sha256(given)) !== expected) return notFound();
    url.searchParams.delete("k");
    // Cookie path /slug matches /slug and /slug/..., but not /slug-other.
    const path = url.pathname === `/${first}` ? `/${first}/` : url.pathname;
    return new Response(null, {
      status: 302,
      headers: {
        location: path + url.search,
        "set-cookie": `${name}=${given}; Path=/${first}; Max-Age=${MONTH}; HttpOnly; Secure; SameSite=Lax`,
        "cache-control": "no-store",
        "referrer-policy": "no-referrer",
      },
    });
  }

  const held = cookie(context.request, name);
  if (!held || (await sha256(held)) !== expected) return notFound();
  const response = await context.next();
  const out = new Response(response.body, response);
  out.headers.set("cache-control", "private, no-store");
  out.headers.set("x-robots-tag", "noindex");
  out.headers.set("referrer-policy", "no-referrer");
  return out;
}
