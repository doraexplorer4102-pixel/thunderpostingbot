# Thunder Button Bot

Custom Telegram Channel Manager for Trade With Thunder.

Posts colored inline buttons into the channel and schedules posts.
Deployed on Railway (worker) from GitHub.

## Required environment variables (set in Railway → Variables)
- `BOT_TOKEN`     – the bot's token from @BotFather (this bot only)
- `DATABASE_URL`  – copy the value from the Postgres service's DATABASE_URL
                    variable and paste it here (internal one, not PUBLIC)

## Channel config (already set in bot.py)
- Channel ID : -1002478427301
- Owner ID   : 8919616891
- Username   : @THUNDERVIPSIGNALS
- Timezone   : Asia/Kolkata
