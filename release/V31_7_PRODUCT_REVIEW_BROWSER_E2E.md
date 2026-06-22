# v31.7 — Product Review and Browser E2E

The product-review checkpoint, route inventory, browser contract, and headless Chrome E2E runner are implemented.

The production WSGI application now registers the complete v31 publication route chain. The browser E2E runs against `src.socmint.wsgi:app` and no longer repairs missing routes during the test.

Ten browser checks cover the publication workspace, product-review page, workflow APIs, and ready checkpoint.

Final focused, regression, full-suite, lint, browser, CI, and verification gates are required on the production-wiring head.
