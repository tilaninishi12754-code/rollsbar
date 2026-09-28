# Deployment checklist

## Before deploy
- [ ] Current production backup exists
- [ ] Database backup exists
- [ ] Git commit identifies exact change
- [ ] Staging matches intended release
- [ ] No secrets committed

## Regression on staging
- [ ] Home/catalog
- [ ] Search
- [ ] Product detail
- [ ] Simple product add-to-cart
- [ ] Variable product selection
- [ ] Quantity changes
- [ ] Mobile sticky cart
- [ ] Cart
- [ ] Checkout fields
- [ ] Delivery/pickup
- [ ] Delivery zone/minimum-order logic
- [ ] Legal pages
- [ ] Reviews
- [ ] Vacancies
- [ ] Email/Telegram notifications
- [ ] Mobile viewport
- [ ] Desktop viewport

## After deploy
- [ ] Smoke test front end
- [ ] Smoke test wp-admin
- [ ] Create test order
- [ ] Verify logs/errors
- [ ] Record deployed commit
