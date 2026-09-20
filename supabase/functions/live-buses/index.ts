// Live bus positions proxy for ShadeMap.
//
// Why this exists: the RTS bus tracker (Clever Devices BusTime at riderts.app)
// requires an API key and sends no CORS headers, so the browser can never call
// it directly and the key must never appear in client code. This function holds
// the key as a Supabase secret, adds CORS, and flattens the response.
//
// Deploy (see LIVE_BUSES.md):
//   supabase secrets set BUSTIME_KEY=yourkey
//   supabase functions deploy live-buses --no-verify-jwt
//
// Client contract:
//   GET {function-url}/vehicles          -> {"vehicles": [...]} for every route
//   GET {function-url}/vehicles?rt=15    -> one route
// Vehicle fields passed through: vid, rt, lat, lon, hdg, des, dly, tmstmp.

const BASE = "https://riderts.app/bustime/api/v3";
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Cache-Control": "public, max-age=5",
  "Content-Type": "application/json",
};

let routeCache: { ids: string[]; at: number } | null = null;

async function busTime(path: string, params: Record<string, string>, key: string) {
  const qs = new URLSearchParams({ key, format: "json", locale: "en", ...params });
  const r = await fetch(`${BASE}/${path}?${qs}`);
  if (!r.ok) throw new Error(`bustime ${path} ${r.status}`);
  const body = await r.json();
  return body["bustime-response"] ?? {};
}

async function allRouteIds(key: string): Promise<string[]> {
  if (routeCache && Date.now() - routeCache.at < 10 * 60 * 1000) return routeCache.ids;
  const res = await busTime("getroutes", {}, key);
  const ids = (res.routes ?? []).map((r: { rt: string }) => String(r.rt));
  routeCache = { ids, at: Date.now() };
  return ids;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  const key = Deno.env.get("BUSTIME_KEY");
  if (!key) {
    return new Response(JSON.stringify({ error: "BUSTIME_KEY secret not set" }),
      { status: 503, headers: CORS });
  }
  try {
    const url = new URL(req.url);
    const rtParam = url.searchParams.get("rt");
    const ids = rtParam
      ? rtParam.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 30)
      : await allRouteIds(key);

    // BusTime accepts at most 10 routes per getvehicles call
    const chunks: string[][] = [];
    for (let i = 0; i < ids.length; i += 10) chunks.push(ids.slice(i, i + 10));

    const vehicles: unknown[] = [];
    for (const chunk of chunks) {
      const res = await busTime("getvehicles", { rt: chunk.join(",") }, key);
      for (const v of res.vehicle ?? []) {
        vehicles.push({
          vid: v.vid, rt: v.rt, lat: v.lat, lon: v.lon,
          hdg: v.hdg, des: v.des, dly: !!v.dly, tmstmp: v.tmstmp,
        });
      }
      // "no service scheduled" style errors are normal off-hours, not failures
    }
    return new Response(JSON.stringify({ vehicles }), { headers: CORS });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 502, headers: CORS });
  }
});
