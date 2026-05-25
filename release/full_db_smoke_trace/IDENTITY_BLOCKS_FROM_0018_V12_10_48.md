# v12.10.48 Identity Blocks

## `all_tab_identity_cols`

- found: `True`
- start_line: `307`
- end_line: `382`

```python
0307:     op.create_table(
0308:         "all_tab_identity_cols",
0309:         sa.Column("owner", sa.String()),  # TODO: confirm type
0310:         sa.Column("mview_name", sa.String()),  # TODO: confirm type
0311:         sa.Column("container_name", sa.String()),  # TODO: confirm type
0312:         sa.Column("query", sa.String()),  # TODO: confirm type
0313:         sa.Column("query_len", sa.String()),  # TODO: confirm type
0314:         sa.Column("updatable", sa.String()),  # TODO: confirm type
0315:         sa.Column("update_log", sa.String()),  # TODO: confirm type
0316:         sa.Column("master_rollback_seg", sa.String()),  # TODO: confirm type
0317:         sa.Column("master_link", sa.String()),  # TODO: confirm type
0318:         sa.Column("rewrite_enabled", sa.String()),  # TODO: confirm type
0319:         sa.Column("rewrite_capability", sa.String()),  # TODO: confirm type
0320:         sa.Column("refresh_mode", sa.String()),  # TODO: confirm type
0321:         sa.Column("refresh_method", sa.String()),  # TODO: confirm type
0322:         sa.Column("build_mode", sa.String()),  # TODO: confirm type
0323:         sa.Column("fast_refreshable", sa.String()),  # TODO: confirm type
0324:         sa.Column("last_refresh_type", sa.String()),  # TODO: confirm type
0325:         sa.Column("last_refresh_date", sa.Date()),  # TODO: confirm type/nullability/default
0326:         sa.Column("last_refresh_end_time", sa.Date()),  # TODO: confirm type/nullability/default
0327:         sa.Column("staleness", sa.String()),  # TODO: confirm type
0328:         sa.Column("after_fast_refresh", sa.String()),  # TODO: confirm type
0329:         sa.Column("unknown_prebuilt", sa.String()),  # TODO: confirm type
0330:         sa.Column("unknown_plsql_func", sa.String()),  # TODO: confirm type
0331:         sa.Column("unknown_external_table", sa.String()),  # TODO: confirm type
0332:         sa.Column("unknown_consider_fresh", sa.String()),  # TODO: confirm type
0333:         sa.Column("unknown_import", sa.String()),  # TODO: confirm type
0334:         sa.Column("unknown_trusted_fd", sa.String()),  # TODO: confirm type
0335:         sa.Column("compile_state", sa.String()),  # TODO: confirm type
0336:         sa.Column("use_no_index", sa.String()),  # TODO: confirm type
0337:         sa.Column("stale_since", sa.Date()),  # TODO: confirm type/nullability/default
0338:         sa.Column("num_pct_tables", sa.String()),  # TODO: confirm type
0339:         sa.Column("num_fresh_pct_regions", sa.String()),  # TODO: confirm type
0340:         sa.Column("num_stale_pct_regions", sa.String()),  # TODO: confirm type
0341:         sa.Column("segment_created", sa.String()),  # TODO: confirm type
0342:         sa.Column("evaluation_edition", sa.String()),  # TODO: confirm type
0343:         sa.Column("unusable_before", sa.String()),  # TODO: confirm type
0344:         sa.Column("unusable_beginning", sa.String()),  # TODO: confirm type
0345:         sa.Column("default_collation", sa.String()),  # TODO: confirm type
0346:         sa.Column("on_query_computation", sa.String()),  # TODO: confirm type
0347:         sa.Column("auto", sa.String()),  # TODO: confirm type
0348:         sa.Column("table_name", sa.String()),  # TODO: confirm type
0349:         sa.Column("column_name", sa.String()),  # TODO: confirm type
0350:         sa.Column("generation_type", sa.String()),  # TODO: confirm type
0351:         sa.Column("sequence_name", sa.String()),  # TODO: confirm type
0352:         sa.Column("identity_options", sa.String()),  # TODO: confirm type
0353:         sa.Column("data_type", sa.String()),  # TODO: confirm type
0354:         sa.Column("data_type_mod", sa.String()),  # TODO: confirm type
0355:         sa.Column("data_type_owner", sa.String()),  # TODO: confirm type
0356:         sa.Column("data_length", sa.String()),  # TODO: confirm type
0357:         sa.Column("data_precision", sa.String()),  # TODO: confirm type
0358:         sa.Column("data_scale", sa.String()),  # TODO: confirm type
0359:         sa.Column("nullable", sa.String()),  # TODO: confirm type
0360:         sa.Column("column_id", sa.String()),  # TODO: confirm type
0361:         sa.Column("default_length", sa.String()),  # TODO: confirm type
0362:         sa.Column("data_default", sa.String()),  # TODO: confirm type
0363:         sa.Column("num_distinct", sa.String()),  # TODO: confirm type
0364:         sa.Column("low_value", sa.String()),  # TODO: confirm type
0365:         sa.Column("high_value", sa.String()),  # TODO: confirm type
0366:         sa.Column("density", sa.String()),  # TODO: confirm type
0367:         sa.Column("num_nulls", sa.String()),  # TODO: confirm type
0368:         sa.Column("num_buckets", sa.String()),  # TODO: confirm type
0369:         sa.Column("last_analyzed", sa.Date()),  # TODO: confirm type/nullability/default
0370:         sa.Column("sample_size", sa.String()),  # TODO: confirm type
0371:         sa.Column("character_set_name", sa.String()),  # TODO: confirm type
0372:         sa.Column("char_col_decl_length", sa.String()),  # TODO: confirm type
0373:         sa.Column("global_stats", sa.String()),  # TODO: confirm type
0374:         sa.Column("user_stats", sa.String()),  # TODO: confirm type
0375:         sa.Column("avg_col_len", sa.String()),  # TODO: confirm type
0376:         sa.Column("char_length", sa.String()),  # TODO: confirm type
0377:         sa.Column("char_used", sa.String()),  # TODO: confirm type
0378:         sa.Column("v80_fmt_image", sa.String()),  # TODO: confirm type
0379:         sa.Column("data_upgraded", sa.String()),  # TODO: confirm type
0380:         sa.Column("hidden_column", sa.String()),  # TODO: confirm type
0381:         sa.Column("virtual_column", sa.String()),  # TODO: confirm type
0382:     )
```

## `identity_columns`

- found: `True`
- start_line: `171`
- end_line: `181`

```python
0171:     op.create_table(
0172:         "identity_columns",
0173:         sa.Column("object_id", sa.Integer()),  # TODO: confirm type/nullability/default
0174:         sa.Column("name", sa.String()),  # TODO: confirm type
0175:         sa.Column("column_id", sa.Integer()),  # TODO: confirm type/nullability/default
0176:         sa.Column("is_identity", sa.Boolean()),  # TODO: confirm type/nullability/default
0177:         sa.Column("seed_value", sa.Numeric()),  # TODO: confirm precision/scale
0178:         sa.Column("increment_value", sa.Numeric()),  # TODO: confirm precision/scale
0179:         sa.Column("last_value", sa.Numeric()),  # TODO: confirm precision/scale
0180:         sa.Column("is_not_for_replication", sa.Boolean()),  # TODO: confirm type/nullability/default
0181:     )
```
