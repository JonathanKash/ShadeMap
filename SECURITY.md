# Security posture and audit notes

Last audited: September 20, 2026, after the rider photo feature went live.

## Attack surface

The site is static (GitHub Pages). The only components that accept input from
the public are the two Supabase endpoints used by the photo feature, reached
with the public anon key in `docs/config.js`:

1. `POST /storage/v1/object/stop-photos/{uuid}.jpg` (photo upload)
2. `POST /rest/v1/stop_reports` (report row insert)

Everything else is read-only static content.

## Controls in place (verified by live adversarial probes, all passing)

- Row level security on `stop_reports`: anon can insert only pending rows
  (`approved = false` enforced by policy, and the `approved` column is not
  grantable on insert), and can select only approved rows. Update and delete
  are denied (verified 401). Pending submissions are invisible to the public.
- Storage: uploads restricted to `^[0-9a-f-]{36}\.jpg$` names (no path
  traversal, no vanity names), JPEG mime only, 5 MB cap, no overwrite
  (upsert refused), no bucket listing.
- Nothing publishes without a human: an admin approves each photo in the
  dashboard before it renders anywhere.
- Cross-site scripting: user-controlled strings (photo notes, captions) are
  HTML-escaped in both front ends (`esc()` in `docs/report.js` and
  `docs/app.html`) before any `innerHTML`. A stored XSS payload was inserted
  as a probe and confirmed to stay pending and unrendered.
- Supply chain: Leaflet is loaded from unpkg with subresource integrity
  hashes pinned in `app.html`, so a compromised CDN cannot alter the script.
- Secrets: the repository and its full git history contain no private keys
  (scanned). The anon key is public by design and is limited by the policies
  above. The management access token used for one-time setup has been
  revoked and its local file deleted. The `service_role` key has never been
  in the repo and must never be.
- Transport: GitHub Pages serves HSTS; all data and tile sources are HTTPS.

## Accepted residual risks

- **Storage flooding.** Anyone can upload UUID-named JPEGs up to 5 MB until
  the free tier's storage quota fills. Client-side cooldown is advisory only.
  Impact: the upload feature stops accepting photos; the map itself is
  unaffected. Kill switch: blank the two values in `docs/config.js` and push,
  which hides the feature entirely. Watch usage in the Supabase dashboard.
- **Pending-queue spam.** Anyone can insert pending rows. They are invisible
  to the public and cost the reviewer time, not the site correctness.
- **GitHub Pages sets no CSP header** (Pages cannot set custom headers). The
  escaping discipline above is the XSS control.

## Reviewer guidance

Approve only photos that show a bus stop with no recognizable faces, no
license plates, and an inoffensive note. When in doubt, reject. Takedown
requests arrive through the GitHub issue tracker (see
`docs/disclosures.html`).

## Reporting a vulnerability

Open an issue at https://github.com/JonathanKash/ShadeMap/issues. For
anything sensitive, use GitHub's private vulnerability reporting on the
repository instead of a public issue.
