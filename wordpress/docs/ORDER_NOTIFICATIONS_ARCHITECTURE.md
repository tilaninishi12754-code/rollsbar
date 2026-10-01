# Rolls Bar — Orders / Email / Telegram Architecture

Date: 2026-10-01
Status: PRE-STAGING IMPLEMENTED / RUNTIME VERIFICATION PENDING

## Goal

After checkout, the operator must receive an order that is easy to fulfil without depending on code or external AI tools.

## Source of truth

- WooCommerce owns orders, order status, transactional email and Additional Checkout Fields persistence.
- Rolls Bar Core reads additional values through WooCommerce's official `CheckoutFields` service.
- Telegram is supplemental only.
- No customer/order data is duplicated into a custom database.

## Additional checkout fields

Registered field IDs:

- `rollsbar/entrance`
- `rollsbar/door-code`
- `rollsbar/floor`
- `rollsbar/apartment-office`

All use `location = order`.

WooCommerce Store API / Checkout Block persists those values to the order.

Rolls Bar Core does **not** manually re-save the same fields.

## Email

WooCommerce core is the owner of the transactional **New order** email.

Current WooCommerce core renders Checkout Block additional order fields in transactional emails. Therefore Rolls Bar Core intentionally does not add a duplicate `woocommerce_email_order_meta_fields` implementation.

Staging must verify:
- New order admin email is enabled.
- Correct recipient is configured.
- SMTP/deliverability is working.
- The four non-empty Rolls Bar address fields appear once, not twice.
- Test email/order is received.

If WooCommerce core behavior changes in a later major version, re-check before adding any custom email renderer.

## wp-admin

WooCommerce already understands Store API additional checkout fields.

Rolls Bar Core additionally renders a compact operator summary after the shipping address:

- fulfilment/shipping method;
- non-empty entrance / door code / floor / apartment-office;
- Telegram notification state.

This summary is convenience UI only. It is not another storage layer.

## Telegram

### Default privacy mode

Telegram notification intentionally excludes:
- customer name;
- phone;
- street/address;
- entrance/door/floor/apartment.

Default message contains:
- order number;
- order total;
- item quantity;
- fulfilment method;
- order status;
- direct wp-admin order URL.

Personal data can only be enabled later through the explicit `rollsbar_telegram_include_personal_data` filter after a separate business/privacy decision.

### Secrets

Never commit these values:

- `ROLLSBAR_TELEGRAM_BOT_TOKEN`
- `ROLLSBAR_TELEGRAM_CHAT_ID`

Accepted sources:
1. constants defined outside Git, e.g. server-managed `wp-config.php`;
2. environment variables;
3. deliberate runtime filters.

They are not editable in the ordinary customer admin screen and are never printed back to the user.

### Queue

A Telegram HTTP request must not delay the checkout response.

Flow:

`Checkout Block → WooCommerce order → woocommerce_store_api_checkout_order_processed → Action Scheduler → Telegram API`

Action group: `rollsbar`

Action hook: `rollsbar_send_order_notifications`

Fallback:
- classic checkout hook queues the same job if checkout implementation changes;
- WP-Cron is used only if Action Scheduler APIs are unexpectedly unavailable.

### Idempotency / retries

Order meta records notification state:
- `_rollsbar_telegram_status`
- `_rollsbar_telegram_attempts`
- `_rollsbar_telegram_sent_at`
- `_rollsbar_telegram_last_error`

Status:
- `not_configured`
- `queued`
- `sent`
- `failed`

Already queued/sent orders are not queued a second time.

Failed delivery is retried up to 3 attempts, with a delayed retry.

Errors are sent to WooCommerce logger under source `rollsbar-core`. Bot token/chat ID are never logged.

## Client admin

`Rolls Bar → Основное` shows:
- WooCommerce email: native/active architecture;
- Telegram: configured / not configured;
- link to Scheduled Actions.

The client sees integration health, but not integration secrets.

## Staging Gate B tests

Before production:

1. Place Checkout Block test order.
2. Confirm order exists in WooCommerce / HPOS.
3. Confirm all four optional fields persist when filled.
4. Confirm empty optional fields do not show noise.
5. Confirm order summary in wp-admin.
6. Confirm New Order email is delivered.
7. Confirm additional fields appear once in email.
8. Configure test Telegram bot/chat outside Git.
9. Place another order.
10. Confirm checkout response is not blocked by Telegram request.
11. Confirm Action Scheduler action appears and finishes.
12. Confirm Telegram message contains no PII by default.
13. Temporarily simulate Telegram failure and confirm visible failed/retry state.
14. Confirm order can still be fulfilled if Telegram is down.
15. Review WooCommerce > Status > Logs and Scheduled Actions.

## Hard rules

- Email remains primary native transaction notification.
- Telegram outage must never block order creation.
- Telegram is not the canonical order database.
- No secret may enter Git.
- No PII in Telegram by default.
- Do not add duplicate additional-field storage.
- Do not duplicate WooCommerce email rendering unless a verified future regression requires it.
