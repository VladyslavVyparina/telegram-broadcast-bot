# Specification: platform bot `bot_public`

## 1. Purpose

`bot_public` is a separate Telegram bot. It is not a second copy of the main bot inside the same process.

Through it, a user creates their own bot with the same autopost, content, and broadcast behavior as `bot/`.

`bot/` is the owner’s own bot. It does not sell copies.

## 2. Languages

- Arabic by default
- English
- `/start` asks for a language, and the menu has a language button
- Every platform string exists in both languages

## 3. User path

### 3.1 First open

A welcome that names the person, says they can create a private autopost bot with the same features as the main bot, and offers a monthly subscription.

Buttons:

- Create an autopost bot
- My bots
- Language

### 3.2 Creating a bot

1. The user presses Create.
2. The bot tells them to create a bot in BotFather and copy the token.
3. They pay in Telegram Stars. The default is 100 stars for one month. The platform owner can change both numbers.
4. After payment they send the token.
5. The platform calls `getMe`, stores the bot, and starts a copy of the main feature set with its own database.
6. The user receives the `@username` of their bot.

### 3.3 When the subscription ends

- After one month (30 days, changeable by an admin) the copy stops.
- People who open the copy can no longer use it.
- Under My bots the owner sees an expired status and a Renew button. Paying again extends the term and starts the copy.

The client conversation mentioned both “one month of work” and “pay every two months”. Confirm whether one payment buys 30 or 60 days before you treat the default as final.

A renewal while the subscription is still active adds days to the current end date. The currency is Telegram Stars (XTR).

### 3.4 Reminder

One day before the end, the owner gets a message in Arabic and English with a renew button.

## 4. Payment defaults

| Setting | Default | Who changes it |
|---|---|---|
| Price in stars | 100 | Platform owners only |
| Term | 30 days | Platform owners only |

## 5. Platform administration

### Who is an admin

The same Telegram user ids as the owner bot. Store them in the environment. This repository does not list live account ids.

### Rights

| Action | Ordinary user | Admin in `bot_admins` | The owner ids |
|---|---|---|---|
| Create or renew a bot with Stars | yes | yes | yes |
| Platform analytics | no | no | yes |
| Change price or term | no | no | yes |

### Analytics

- Bots created, active, and expired
- Revenue today and in total, in stars
- Recent purchases: who, how many stars, for how many days, which bot
- A notice to the platform owners on every purchase

## 6. Layout

```
BOT_automatical/
├── bot/              owner feature set, also the code each copy runs
├── bot_public/       platform: payment, creation, analytics
└── data/clones/      one database per copy
```

One process, `bot_public.main`, polls the platform and every active copy. Each copy has its own `BOT_TOKEN`, its own database, and `admin_id` equal to the copy’s owner. The copy runs the `bot/` package. Payment lives only on the platform.

## 7. Screens

| Screen | Contents |
|---|---|
| Language | Arabic or English |
| Home | Greeting and the three buttons |
| Create | Instructions, then payment, then the token |
| My bots | List, status, days left, renew |
| Admin | Statistics, recent purchases, price and term |

## 8. Out of scope for `bot_public`

- The full admin panel of the owner bot (autopost, content). That is inside the copy.
- Payment inside a copy. There is none.

## 9. Build order

1. This specification
2. Rewrite `bot_public` as the platform plus Stars
3. Start copies through `ChildManager`
4. Admin analytics and purchase notices
5. The one-day reminder
6. Deploy on the VPS and run `python3 -m bot_public.main`

## 10. Open questions for the client

1. Is one payment 30 days or 60?
2. May one user own several copies?
3. Is a free trial required, for example three days?
