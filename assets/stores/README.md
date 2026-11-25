# Store badges

Official badges, used unchanged, downloaded on 2026-11-23:

- `app-store-en.svg`, `app-store-sv.svg`: "Download on the App Store", black, from Apple's marketing tools
  (https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us and `.../sv-se`).
- `google-play-en.png`, `google-play-sv.png`: "Get it on Google Play", from Google's badge page
  (https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png and `sv_...`).

The badges are trademarks of Apple Inc. and Google LLC. Both companies require that a badge is shown unchanged and links to the app's own store page.
Until the apps are published the page shows the badges as plain images under a "Coming soon" caption, with no link (`STORE` in `index.html`).
When an app is live, set its address in `STORE` and the badge becomes the link. Check Apple's and Google's current badge guidelines before the first release.
