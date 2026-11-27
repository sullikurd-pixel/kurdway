# KURDWAY 0.4.0 local preview

Customer login accepts only example.com test addresses. The six-digit code is written to the owner's private local test-mail/latest.txt file, not delivered by email. Codes are single-use, expire in five minutes and have limited attempts. Customer sessions expire in one hour. The owner console can suspend customer accounts and revoke sessions. Customer login cannot grant administrator privileges. Activity history covers successful customer logins and owner suspension/restoration actions.

Do not deploy this preview publicly. Real email verification, production authentication, HTTPS, MFA, durable rate limiting, audit retention, payment processing, and integration tests remain required. Browser-local drafts are not yet separated by customer account. Premium flags do not represent paid subscriptions.

Update with git pull --ff-only and restart com.kurdway.local via launchctl kickstart -k. Verify /api/health, /admin and /account. Use synthetic test data only.
