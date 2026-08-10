<h1 align="center"><img src="https://cdn.project-mei.xyz/68747470733a2f2f696d6167652e6d79616e696d656c6973742e6e65742f75692f666b4c4954614a546566616678464b5047527a6e676751555f6954556c644e4a4474784c665943647730695336656a53454548425f4a4d6c6831314c66714c33-v97ofuq7U43I.png"></h1>
<div align="center">
 <a href="https://github.com/raidensakura"><img src="https://img.shields.io/badge/raiden--cogs-by%20Raiden-d11df9"></a>
 <a href="https://github.com/Cog-Creators/Red-DiscordBot"><img src="https://img.shields.io/badge/Red%20DiscordBot-V3-red.svg"></a>
 <a href="[https://github.com/raidensakura](https://github.com/python/black)"><img src="https://img.shields.io/badge/code%20style-black-1c1c1c.svg"></a>
 <a href="https://dsc.gg/transience/"><img src="https://discord.com/api/guilds/616969119685935162/widget.png"></a><br>
 <a href="https://ko-fi.com/P5P6D65UW"><img src="https://storage.ko-fi.com/cdn/brandasset/kofi_button_red.png" style="height: 25px;"></a>
</div>
<br>
<p align="center"><b>MemberCard</b> - Generates a welcome image with Pillow when a member joins, featuring their avatar, username, join date, and roles. Supports multiple card themes, and includes a command to view any member's card on demand.</p>

<h2 align="center">Themes</h2>

| Theme | Description |
| --- | --- |
| `classic` (default) | An ID-badge style card with a barcode and ID number footer. |
| `laevatain` | A full-art profile card over a fixed backdrop, with a stat panel and status quote box. |
| `fangyi` | Same full-art layout as `laevatain`, over a different backdrop with a green trim. |
| `yvonne` | Same full-art layout, over a different backdrop with a pink trim. |

`[p]membercard theme` sets which theme is used for both your welcome card and `[p]membercard view`. Defaults to `classic` until you set one.

Welcome cards are **off by default** — enable them with `[p]membercard toggle`.

<h2 align="center">Commands</h2>

| Command | Description |
| --- | --- |
| `[p]membercard view [member]` | View your own or another member's ID card. |
| `[p]membercard theme [theme]` | View or set your personal card theme, used by `view`. |
| `[p]membercard toggle` | Toggle whether a card is posted when a member joins. Off by default. Requires Manage Server. |
| `[p]membercard channel [channel]` | Set the channel welcome cards are posted in. Leave blank to reset to the server's system channel. Requires Manage Server. |
| `[p]membercard testwelcome [member]` | Preview the welcome message as it would appear on join. Bot owner only. |

`[p]mcard` also works as a shorthand alias for `[p]membercard`.

<h2 align="center">Installation</h2>

```ini
[p]load downloader
[p]repo add raiden-cogs https://github.com/raidensakura/raiden-cogs/
[p]cog install raiden-cogs membercard
[p]load membercard
```

Fonts used in the generated card are [Barlow](https://fonts.google.com/specimen/Barlow) and [Barlow Condensed](https://fonts.google.com/specimen/Barlow+Condensed), licensed under the SIL Open Font License (see `fonts/OFL.txt`).
