# Turning on live bus positions

The app view has a built-in live-bus layer. It stays hidden until `docs/config.js` gets a
`busFeedUrl`, the same pattern as the photo feature: with no value, the map behaves exactly
as before.

Live positions come from the RTS bus tracker (Clever Devices BusTime at riderts.app). That
API needs an access key and blocks browser calls, so a small proxy holds the key and adds
CORS. The proxy ships in this repo as a Supabase Edge Function:
`supabase/functions/live-buses/index.ts`.

## 1. Get a BusTime API key from RTS

There is no self-serve signup. Ask RTS for developer API access to their BusTime feed:
call 352-334-2600 or use the contact form at go-rts.com, and say you want an API key for
the public real-time feed (getvehicles / getroutes) for a civic project. City staff at
CityCamp may be able to shortcut this.

## 2. Deploy the proxy (one person, about 5 minutes)

Install the Supabase CLI, log in, then from the repo root:

```
supabase link --project-ref osipwdxooggemqlbatus
supabase secrets set BUSTIME_KEY=the-key-rts-gave-you
supabase functions deploy live-buses --no-verify-jwt
```

The deploy prints a URL like
`https://osipwdxooggemqlbatus.supabase.co/functions/v1/live-buses`.

## 3. Point the map at it

In `docs/config.js` set:

```js
busFeedUrl: "https://osipwdxooggemqlbatus.supabase.co/functions/v1/live-buses",
```

Commit and push. When GitHub Pages republishes, buses appear as blue route-numbered tags
that refresh every 10 seconds (orange when the feed reports a delay), and they follow the
route selector. Polling pauses when the tab is hidden.

## Notes

- The API key lives only in the Supabase secret. Never put it in `docs/`, the repo, or
  anywhere the browser can see.
- The function caches the route list for 10 minutes and responses for 5 seconds, which
  keeps the load on the RTS feed small.
- Kill switch: blank `busFeedUrl` in `docs/config.js` and push.
