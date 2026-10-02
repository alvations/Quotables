# Relay copies of deep-search results

Children on the `batch_wNNN` deep-search batches return their findings twice: a git push to
`sourcing/web_results/`, and a text relay into the orchestrating session. The git push is
authoritative, and `sourcing/web_results/` is the verbatim record the pipeline reads.

This directory holds the relay copy for a batch that reported through the relay before it
managed to push. It exists because the relay turned out not to be redundant: `batch_d14`
(composers) reported 26 rows through the relay and never pushed at all, so those rows lived
only in one session's inbox until they were written down. The same risk applies here, and the
findings are expensive to reproduce - `batch_w003` alone traced sixteen Lincoln quotations to
their real origins, which is the kind of result that should not depend on a container staying
alive.

Where a batch later pushes to `sourcing/web_results/`, that file is the one to use and the
relay copy here is superseded; it is kept rather than deleted so the audit trail shows what
was reported and when. Rows are in the same shape as `sourcing/web_results/`: a corpus line
`id`, a `status` of sourced / misattributed / unverified, the `sources` assigned, the
`evidence` read, and the `queries` run.
