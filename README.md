# India Deals Telegram Bot

A free, scheduled Python bot that finds high-discount products from official
affiliate APIs or approved JSON feeds and posts new deals to a Telegram group.
It runs every two hours on GitHub Actions, so no paid server is required.

## Supported sources

- Amazon India Creators API (the successor to the retired PA-API 5.0)
- Flipkart Affiliate Product Feed API
- Any permitted HTTPS JSON feed from an approved affiliate network

No connector scrapes shopping-site HTML. API access and product availability
remain subject to each affiliate program's approval and terms. "All deals" is
not technically possible: the bot ranks products returned by configured APIs.

## 1. Create the Telegram bot

1. Open `@BotFather` in Telegram and run `/newbot`.
2. Copy the token. Never commit or share it.
3. Add the bot to your target group and allow it to post messages.
4. Send a message in the group, then open:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Copy the group's negative `chat.id`, such as `-1001234567890`.

## 2. Test locally

Python 3.11 or newer is required.

```powershell
Copy-Item .env.example .env
python -m pip install .
```

The bot automatically loads `.env` from the current project directory. For a
safe preview, set `DRY_RUN=true` in that file and run:

```powershell
india-deals-bot
```

For real posting, set `DRY_RUN=false` and provide the Telegram values in
`.env`. The file is ignored by Git and must never be committed.

## 3. Configure GitHub for free scheduled runs

1. Create a public GitHub repository and upload this project.
2. Open **Settings > Secrets and variables > Actions**.
3. Add repository secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - Amazon or Flipkart credentials listed in `.env.example`
4. Add optional repository variables:
   - `DEAL_KEYWORDS` (comma-separated)
   - `MIN_DISCOUNT_PERCENT` (default `30`)
   - `MAX_DEALS_PER_RUN` (default `10`)
   - `JSON_FEED_URLS` (comma-separated HTTPS endpoints)
5. Open **Actions > Post India deals > Run workflow**.

The workflow caches `.deals-state.json` to avoid reposting a deal for 14 days.
It checks every 30 minutes. Scheduled GitHub Actions can start later than the
exact cron time.

## Affiliate API setup

Register separately with Amazon Associates India and Flipkart Affiliate.
Approval and API credentials are controlled by those programs. Put credentials
only in GitHub Secrets, never in `.env.example` or source files.

Amazon Creators API URLs can be overridden with `AMAZON_TOKEN_URL` and
`AMAZON_API_URL` if Amazon assigns different regional endpoints. Search terms
are configured with `AMAZON_SEARCH_KEYWORDS`.

Flipkart categories are configured with `FLIPKART_CATEGORIES`. Names are
matched against categories returned by the affiliate API.

## JSON feed schema

An endpoint may return a JSON array or `{ "deals": [...] }`:

```json
{
  "deals": [
    {
      "id": "unique-product-id",
      "merchant": "Example Store",
      "title": "Example laptop",
      "url": "https://store.example/product",
      "sale_price": 49990,
      "list_price": 69990,
      "image_url": "https://store.example/image.jpg",
      "availability_note": "Available in selected Bengaluru pincodes"
    }
  ]
}
```

Only HTTPS product and feed URLs are accepted.

`FLASH_DEAL_MAX_PRICE` defaults to `10`, causing genuine low-price offers such
as ₹1 promotions to rank before normal deals. Quick-commerce feeds should set
`availability_note`, because Blinkit, Instamart and Zepto prices and stock are
commonly pincode-, account- and time-specific. The bot does not scrape those
apps; use only a feed supplied or approved by the retailer or affiliate network.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Post a verified deal before API approval

Repository owners can publish rich deal cards without a server:

1. Open the repository's **Actions** tab.
2. Select **Post a manual deal**.
3. Select **Run workflow**.
4. Enter the retailer, product title, current price, MRP and official link.
5. Optionally provide a public HTTPS image and availability conditions.

The workflow validates prices and URLs, calculates the discount, and posts an
image card with an inline **View Deal** button. Only the repository owner can
run this workflow. Verify the live price and conditions before every post.
