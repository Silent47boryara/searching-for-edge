# BOS: research results

Research snapshot: 13–14 October 2026. Package prepared on 16 October 2026.

This is an archive of diagnostic laboratories, not a trading strategy or a production release.

- [Research summary](RESEARCH_SUMMARY.md)
- [Open questions](OPEN_QUESTIONS.md)
- [Implementation audit](audit_2026-10-13/REPORT.md)
- [BOS quality and replay of corrections](quality_2026-10-13/RESULT.md)
- [Literature](quality_2026-10-13/LITERATURE.md)
- [Collectors individually and in combination](collectors_2026-10-14/RESULT.md)
- [Interactive market map](dashboard/README.md)

## Reproducibility and scope

The folders contain protocols, scripts, calculated tables, checks, and manifests with hashes. The scripts depend on external local sources in bot_project_v2 and the earlier LAB_attrib_p1; those sources are not included. The archive therefore supports inspection of the saved results, but does not promise a complete rerun from a clean clone. Absolute paths in scripts and manifests are historical research paths and require configuration on another machine. Each manifest describes its source laboratory; it is not a hash of this entire commit.

Large derived replay tables and minute prices are included for verification. The production bot_v2.py, raw feeds, secrets, and the bot's runtime logs are excluded. candidate_core.py and candidate_helpers.py are isolated research modules, not replacements for the production bot. The corrections have not been deployed.

The long history had already been examined. Chronological checks are not a new independent holdout. A failure to find significant improvement does not establish the absence of every possible effect.

## Language and source integrity

The research reports, summaries, and interactive map are available in English. Verbatim bot messages in the archived peak CSVs, exact extracted source modules, and historical diagnostic transcripts retain their original wording. These are evidence artifacts, not untranslated research conclusions. Translation does not change the numerical data, model definitions, or findings. Existing source/output hashes describe the original research artifacts; they are not checksums of the translated documents or interface.
