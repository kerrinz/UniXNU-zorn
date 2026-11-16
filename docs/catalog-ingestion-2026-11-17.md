# zorn catalog TOML ingestion failure

The official zorn page reports `Unterminated string (at end of document)` for revision `0ca7f702e30a277371975feef665ec5763f4a43b`. Its complete public `porting.toml` is610093 bytes and parses successfully;the local pre-fix record also parses. This is not an unterminated quote in the complete published file.

The official scanner requests GitHub GraphQL `Blob.text` without checking `isTruncated` or the returned length against `byteSize`. This makes a truncated text response reach `tomllib` as if it were complete. GitHub documents the [Blob truncation indicator](https://docs.github.com/en/graphql/reference/git#blob). The complete public file,official registry error and scanner source establish an ingestion-stage completeness problem;GraphQL text truncation is the supported cause inference,not a directly captured authenticated API response. No CLI login or credentials were added to investigate it.

The repository fix keeps the root catalog entry concise and below48KiB. The exact677529-byte pre-fix record,including every historical evidence entry and its original limitations,is preserved in [the full ledger](history/porting-through-v261-2026-11-17.toml),with [length/hash metadata](history/porting-archive-2026-11-17.json). References inside that ledger retain their original device-repository base. No driver,board input,OS selection,storage layout or historical result is changed by this compaction.

[The guard](../scripts/check-catalog-record.py) parses the complete entry,checks its byte budget,validates all local references and verifies the historical archive hash/evidence count. CI runs it alongside the existing official record workflow. It refuses oversized valid TOML and unterminated text. With `--upstream`,the actual official `update_entry` function accepts complete history and the concise current entry,and reproduces the same EOF error from explicitly truncated historical text. The truncation fixture is a regression control,not a claim that the authenticated API's exact cutoff was captured.

Run from the common parent:

```sh
python3 -B UniXNU-zorn/scripts/check-catalog-record.py --upstream UniXNU
python3 UniXNU/scripts/porting-record.py check --device UniXNU-zorn
```

The GPU record now describes the implemented partial iOS26 source and the exact261 desktop/basic-interaction observation,Settings-long-press freeze and unresolved BoMap NoResources. `implemented` is a source grade;full GPU/Metal/display/touch acceptance remains incomplete. The default iPadOS17 profile and historical evidence identities remain unchanged.

[Official catalog rules](https://unixnu.com/zh/porting/records) read root board/record files from a published fixed revision. Local staging alone cannot change the deployed page:the corrected device revision must be published and the official catalog scanned/deployed before the website error can disappear. No remote publication or official workflow was performed in this fix.

[Exact source pins and regression receipt](evidence/catalog-ingestion-2026-11-17.json). Official scanner/validator/components were fetched at commit`991b3223e485edbe5ae1f89c52df9b8b1b3991d2`;both language previews rendered with the explicit UNPUBLISHED-WORKTREE label. All1172historical evidence entries remain intact. The size budget is preventive;it is not presented as GitHub’s documented text limit.

The owner subsequently requested local commits in both device/firmware repositories. Evidence fields such as no_commit_or_push describe their original capture/preparation phase;historical receipts are not rewritten to assign the later repository revision as their tested input. Remote push and official rescan remain separate.
