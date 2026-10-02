# Verbatim relay payloads

A deep-search child reports its findings twice: a git push to `sourcing/web_results/`, and a
text relay into the orchestrating session. Where the push never happened, the relay is the only
copy, and the rows in `sourcing/relay_web/` were typed out of a message.

This directory holds those messages exactly as they arrived, so the transcription can be
checked against its source. Each file is one instalment from one batch; the rows are in the
same shape as `sourcing/web_results/`.

They matter because the relay turned out to be the last line of defence rather than a
redundancy. Twelve children were stopped by a seven-day usage limit three minutes after
dispatch on 2026-10-02, and when they resumed, several reported through the relay and were
archived before they managed a push. Seven instalments - 278 rows across five batches - arrived
after the run had already been declared finished, in the notification queue; without this
directory they would have existed only in one session's inbox.
