# tinyshop

A small online shop's backend: accounts, carts, coupons, tax, shipping, checkout and payments.
It's the sample codebase for guided project P3. The code is made up, but it's written the way
real shop code is, so the questions you ask about it are the ones you'd ask at a new job.

## Layout

- `tinyshop/auth.py`: passwords, logins and sessions
- `tinyshop/cart.py`, `coupons.py`: the cart and discount codes
- `tinyshop/tax.py`, `shipping.py`: what an order costs
- `tinyshop/checkout.py`, `payments.py`, `inventory.py`: placing and refunding orders
- `tinyshop/emails.py`: receipts
- `tinyshop/routes.py`: the HTTP handlers
- `tinyshop/utils/`: retries and money formatting
