# v12.10.33 P0/P1 Migration Candidate Worksheet

- **schema_mutation**: `none`
- **migration_created**: `False`
- **alembic_versions_mutated**: `False`
- **candidate_count**: `20`
- **P0**: `16`
- **P1**: `4`
- **PASS**: `18`
- **PASS_WITH_REVIEW_NOTES**: `1`
- **REVIEW**: `1`

## Summary table

| Class | Priority | Score | Table | Domain | Status | Columns | Notes |
|---|---|---:|---|---|---|---:|---|
| PASS | P0 | 89 | `spine_connector_runs` | connectors | active_candidate | 14 | ready for human column review |
| PASS | P0 | 89 | `spine_dossier_assertions` | dossier | active_candidate | 18 | ready for human column review |
| PASS | P0 | 89 | `spine_raw_artifacts` | evidence | active_candidate | 18 | ready for human column review |
| PASS | P0 | 89 | `spine_observations` | identity | active_candidate | 20 | ready for human column review |
| PASS | P0 | 89 | `spine_seeds` | identity | active_candidate | 14 | ready for human column review |
| PASS | P0 | 89 | `spine_subjects` | identity | active_candidate | 6 | ready for human column review |
| PASS | P0 | 89 | `spine_validation_events` | identity | active_candidate | 12 | ready for human column review |
| PASS | P0 | 85 | `retention_runs` | connectors | active_candidate | 6 | ready for human column review |
| PASS | P0 | 85 | `workbench_jobs` | connectors | active_candidate | 14 | ready for human column review |
| PASS | P0 | 85 | `identity_columns` | identity | active_candidate | 8 | ready for human column review |
| PASS | P0 | 85 | `identity_edges` | identity | active_candidate | 10 | ready for human column review |
| PASS | P0 | 85 | `identity_graphs` | identity | active_candidate | 4 | ready for human column review |
| PASS | P0 | 85 | `identity_merge_candidates` | identity | active_candidate | 12 | ready for human column review |
| PASS | P0 | 85 | `identity_nodes` | identity | active_candidate | 9 | ready for human column review |
| PASS | P0 | 85 | `spine_contradictions` | identity | active_candidate | 12 | ready for human column review |
| PASS | P0 | 85 | `policy_gate_events` | policy | active_candidate | 7 | ready for human column review |
| PASS | P1 | 70 | `connector_runs` | connectors | active_candidate | 10 | ready for human column review |
| PASS | P1 | 70 | `all_tab_identity_cols` | identity | active_candidate | 73 | ready for human column review |
| PASS_WITH_REVIEW_NOTES | P1 | 65 | `media_profile_enrichments` | connectors | active_candidate | 9 | WARNINGS: possible indirect/rename coverage exists |
| REVIEW | P1 | 60 | `employee` | uncategorized | active_candidate | 0 | BLOCKERS: no SQLAlchemy column hints extracted |

## Candidate details

### `spine_connector_runs`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:487` (__tablename__)
- `src/socmint/database.py:766` (__tablename__)

#### Extracted block 1: class `SpineConnectorRun` lines 486-496

```python
0486: class SpineConnectorRun(Base):
0487:     __tablename__ = "spine_connector_runs"
0488:     id = Column(Integer, primary_key=True)
0489:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0490:     connector_key = Column(String, nullable=False)
0491:     seed_id = Column(Integer, ForeignKey("spine_seeds.id"), nullable=True)
0492:     status = Column(String, nullable=False)
0493:     raw_result_json = Column(Text, nullable=False)
0494:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0495: 
0496: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `connector_key` — `String, nullable=False` — TODO: confirm type/nullability/default
- `seed_id` — `Integer, ForeignKey("spine_seeds.id"` — TODO: confirm FK target and migration order
- `status` — `String, nullable=False` — TODO: confirm type/nullability/default
- `raw_result_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineConnectorRun` lines 765-775

```python
0765: class SpineConnectorRun(Base):
0766:     __tablename__ = "spine_connector_runs"
0767:     id = Column(Integer, primary_key=True)
0768:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0769:     connector_key = Column(String, nullable=False)
0770:     seed_id = Column(Integer, ForeignKey("spine_seeds.id"), nullable=True)
0771:     status = Column(String, nullable=False)
0772:     raw_result_json = Column(Text, nullable=False)
0773:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0774: 
0775: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `connector_key` — `String, nullable=False` — TODO: confirm type/nullability/default
- `seed_id` — `Integer, ForeignKey("spine_seeds.id"` — TODO: confirm FK target and migration order
- `status` — `String, nullable=False` — TODO: confirm type/nullability/default
- `raw_result_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_dossier_assertions`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `dossier`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:525` (__tablename__)
- `src/socmint/database.py:804` (__tablename__)

#### Extracted block 1: class `SpineDossierAssertion` lines 524-536

```python
0524: class SpineDossierAssertion(Base):
0525:     __tablename__ = "spine_dossier_assertions"
0526:     id = Column(Integer, primary_key=True)
0527:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0528:     assertion_type = Column(String, nullable=False)
0529:     normalized_value = Column(Text, nullable=True)
0530:     confidence = Column(String, nullable=False, default="0.5")
0531:     validation_state = Column(String, nullable=False, default="unreviewed")
0532:     payload_json = Column(Text, nullable=False)
0533:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0534:     updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0535: 
0536: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `assertion_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `validation_state` — `String, nullable=False, default="unreviewed"` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `updated_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineDossierAssertion` lines 803-815

```python
0803: class SpineDossierAssertion(Base):
0804:     __tablename__ = "spine_dossier_assertions"
0805:     id = Column(Integer, primary_key=True)
0806:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0807:     assertion_type = Column(String, nullable=False)
0808:     normalized_value = Column(Text, nullable=True)
0809:     confidence = Column(String, nullable=False, default="0.5")
0810:     validation_state = Column(String, nullable=False, default="unreviewed")
0811:     payload_json = Column(Text, nullable=False)
0812:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0813:     updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0814: 
0815: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `assertion_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `validation_state` — `String, nullable=False, default="unreviewed"` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `updated_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_raw_artifacts`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `evidence`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:498` (__tablename__)
- `src/socmint/database.py:777` (__tablename__)

#### Extracted block 1: class `SpineRawArtifact` lines 497-509

```python
0497: class SpineRawArtifact(Base):
0498:     __tablename__ = "spine_raw_artifacts"
0499:     id = Column(Integer, primary_key=True)
0500:     run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
0501:     kind = Column(String, nullable=False)
0502:     path = Column(Text, nullable=False)
0503:     sha256 = Column(String, nullable=False)
0504:     mime_type = Column(String, nullable=True)
0505:     size_bytes = Column(Integer, nullable=True)
0506:     meta_json = Column(Text, nullable=True)
0507:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0508: 
0509: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `run_id` — `Integer, ForeignKey("spine_connector_runs.id"` — TODO: confirm FK target and migration order
- `kind` — `String, nullable=False` — TODO: confirm type/nullability/default
- `path` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `sha256` — `String, nullable=False` — TODO: confirm type/nullability/default
- `mime_type` — `String, nullable=True` — TODO: confirm type/nullability/default
- `size_bytes` — `Integer, nullable=True` — TODO: confirm type/nullability/default
- `meta_json` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineRawArtifact` lines 776-788

```python
0776: class SpineRawArtifact(Base):
0777:     __tablename__ = "spine_raw_artifacts"
0778:     id = Column(Integer, primary_key=True)
0779:     run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
0780:     kind = Column(String, nullable=False)
0781:     path = Column(Text, nullable=False)
0782:     sha256 = Column(String, nullable=False)
0783:     mime_type = Column(String, nullable=True)
0784:     size_bytes = Column(Integer, nullable=True)
0785:     meta_json = Column(Text, nullable=True)
0786:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0787: 
0788: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `run_id` — `Integer, ForeignKey("spine_connector_runs.id"` — TODO: confirm FK target and migration order
- `kind` — `String, nullable=False` — TODO: confirm type/nullability/default
- `path` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `sha256` — `String, nullable=False` — TODO: confirm type/nullability/default
- `mime_type` — `String, nullable=True` — TODO: confirm type/nullability/default
- `size_bytes` — `Integer, nullable=True` — TODO: confirm type/nullability/default
- `meta_json` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_observations`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:511` (__tablename__)
- `src/socmint/database.py:790` (__tablename__)

#### Extracted block 1: class `SpineObservation` lines 510-523

```python
0510: class SpineObservation(Base):
0511:     __tablename__ = "spine_observations"
0512:     id = Column(Integer, primary_key=True)
0513:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0514:     run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
0515:     observation_type = Column(String, nullable=False)
0516:     normalized_value = Column(Text, nullable=True)
0517:     confidence = Column(String, nullable=False, default="0.5")
0518:     source_ref = Column(Text, nullable=True)
0519:     evidence_ref = Column(Text, nullable=True)
0520:     payload_json = Column(Text, nullable=False)
0521:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0522: 
0523: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `run_id` — `Integer, ForeignKey("spine_connector_runs.id"` — TODO: confirm FK target and migration order
- `observation_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `source_ref` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `evidence_ref` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineObservation` lines 789-802

```python
0789: class SpineObservation(Base):
0790:     __tablename__ = "spine_observations"
0791:     id = Column(Integer, primary_key=True)
0792:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0793:     run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
0794:     observation_type = Column(String, nullable=False)
0795:     normalized_value = Column(Text, nullable=True)
0796:     confidence = Column(String, nullable=False, default="0.5")
0797:     source_ref = Column(Text, nullable=True)
0798:     evidence_ref = Column(Text, nullable=True)
0799:     payload_json = Column(Text, nullable=False)
0800:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0801: 
0802: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `run_id` — `Integer, ForeignKey("spine_connector_runs.id"` — TODO: confirm FK target and migration order
- `observation_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `source_ref` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `evidence_ref` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_seeds`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:476` (__tablename__)
- `src/socmint/database.py:755` (__tablename__)

#### Extracted block 1: class `SpineSeed` lines 475-485

```python
0475: class SpineSeed(Base):
0476:     __tablename__ = "spine_seeds"
0477:     id = Column(Integer, primary_key=True)
0478:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0479:     seed_type = Column(String, nullable=False)
0480:     raw_value = Column(Text, nullable=False)
0481:     normalized_value = Column(Text, nullable=False)
0482:     pii_hash = Column(String, nullable=False)
0483:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0484: 
0485: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `seed_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `raw_value` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `pii_hash` — `String, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineSeed` lines 754-764

```python
0754: class SpineSeed(Base):
0755:     __tablename__ = "spine_seeds"
0756:     id = Column(Integer, primary_key=True)
0757:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
0758:     seed_type = Column(String, nullable=False)
0759:     raw_value = Column(Text, nullable=False)
0760:     normalized_value = Column(Text, nullable=False)
0761:     pii_hash = Column(String, nullable=False)
0762:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0763: 
0764: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `seed_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `raw_value` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `pii_hash` — `String, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_subjects`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:469` (__tablename__)
- `src/socmint/database.py:748` (__tablename__)

#### Extracted block 1: class `SpineSubject` lines 468-474

```python
0468: class SpineSubject(Base):
0469:     __tablename__ = "spine_subjects"
0470:     id = Column(Integer, primary_key=True)
0471:     label = Column(String, nullable=True)
0472:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0473: 
0474: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `label` — `String, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineSubject` lines 747-753

```python
0747: class SpineSubject(Base):
0748:     __tablename__ = "spine_subjects"
0749:     id = Column(Integer, primary_key=True)
0750:     label = Column(String, nullable=True)
0751:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0752: 
0753: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `label` — `String, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_validation_events`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `scripts/write_spine_files.py:538` (__tablename__)
- `src/socmint/database.py:817` (__tablename__)

#### Extracted block 1: class `SpineValidationEvent` lines 537-697

```python
0537: class SpineValidationEvent(Base):
0538:     __tablename__ = "spine_validation_events"
0539:     id = Column(Integer, primary_key=True)
0540:     assertion_id = Column(
0541:         Integer,
0542:         ForeignKey("spine_dossier_assertions.id"),
0543:         nullable=False,
0544:     )
0545:     actor = Column(String, nullable=True)
0546:     action = Column(String, nullable=False)
0547:     note = Column(Text, nullable=True)
0548:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0549: 
0550: 
0551: def _detach_all(session, items):
0552:     for item in items:
0553:         session.expunge(item)
0554:     return items
0555: 
0556: 
0557: def create_spine_subject(label=None):
0558:     ensure_configured()
0559:     session = Session()
0560:     try:
0561:         subject = SpineSubject(label=label)
0562:         session.add(subject)
0563:         session.commit()
0564:         session.refresh(subject)
0565:         return subject.id
0566:     finally:
0567:         session.close()
0568: 
0569: 
0570: def get_spine_subject(subject_id):
0571:     ensure_configured()
0572:     session = Session()
0573:     try:
0574:         subject = session.query(SpineSubject).filter_by(id=subject_id).first()
0575:         if subject:
0576:             session.expunge(subject)
0577:         return subject
0578:     finally:
0579:         session.close()
0580: 
0581: 
0582: def list_spine_subjects(limit=100):
0583:     ensure_configured()
0584:     session = Session()
0585:     try:
0586:         items = session.query(SpineSubject).order_by(
0587:             SpineSubject.created_at.desc()
0588:         ).limit(limit).all()
0589:         return _detach_all(session, items)
0590:     finally:
0591:         session.close()
0592: 
0593: 
0594: def add_spine_seed(subject_id, seed_type, raw_value, normalized_value, pii_hash):
0595:     ensure_configured()
0596:     session = Session()
0597:     try:
0598:         existing = session.query(SpineSeed).filter_by(
0599:             subject_id=subject_id,
0600:             seed_type=seed_type,
0601:             pii_hash=pii_hash,
0602:         ).first()
0603:         if existing:
0604:             return existing.id
0605:         seed = SpineSeed(
0606:             subject_id=subject_id,
0607:             seed_type=seed_type,
0608:             raw_value=raw_value,
0609:             normalized_value=normalized_value,
0610:             pii_hash=pii_hash,
0611:         )
0612:         session.add(seed)
0613:         session.commit()
0614:         session.refresh(seed)
0615:         return seed.id
0616:     finally:
0617:         session.close()
0618: 
0619: 
0620: def list_spine_seeds(subject_id):
0621:     ensure_configured()
0622:     session = Session()
0623:     try:
0624:         items = session.query(SpineSeed).filter_by(
0625:             subject_id=subject_id
0626:         ).order_by(SpineSeed.id.asc()).all()
0627:         return _detach_all(session, items)
0628:     finally:
0629:         session.close()
0630: 
0631: 
0632: def create_spine_connector_run(
0633:     subject_id,
0634:     connector_key,
0635:     seed_id,
0636:     status,
0637:     raw_result,
0638: ):
0639:     ensure_configured()
0640:     session = Session()
0641:     try:
0642:         run = SpineConnectorRun(
0643:             subject_id=subject_id,
0644:             connector_key=connector_key,
0645:             seed_id=seed_id,
0646:             status=status,
0647:             raw_result_json=json.dumps(raw_result),
0648:         )
0649:         session.add(run)
0650:         session.commit()
0651:         session.refresh(run)
0652:         return run.id
0653:     finally:
0654:         session.close()
0655: 
0656: 
0657: def list_spine_connector_runs(subject_id=None, limit=100):
0658:     ensure_configured()
0659:     session = Session()
0660:     try:
0661:         query = session.query(SpineConnectorRun)
0662:         if subject_id is not None:
0663:             query = query.filter_by(subject_id=subject_id)
0664:         items = query.order_by(
0665:             SpineConnectorRun.created_at.desc()
0666:         ).limit(limit).all()
0667:         return _detach_all(session, items)
0668:     finally:
0669:         session.close()
0670: 
0671: 
0672: def create_spine_raw_artifact(
0673:     run_id,
0674:     kind,
0675:     path,
0676:     sha256,
0677:     mime_type=None,
0678:     size_bytes=None,
0679:     meta=None,
0680: ):
0681:     ensure_configured()
0682:     session = Session()
0683:     try:
0684:         artifact = SpineRawArtifact(
0685:             run_id=run_id,
0686:             kind=kind,
0687:             path=path,
0688:             sha256=sha256,
0689:             mime_type=mime_type,
0690:             size_bytes=size_bytes,
0691:             meta_json=json.dumps(meta or {}),
0692:         )
0693:         session.add(artifact)
0694:         session.commit()
0695:         session.refresh(artifact)
0696:         return artifact.id
0697:     finally:
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `assertion_id` — `Integer, ForeignKey("spine_dossier_assertions.id"` — TODO: confirm FK target and migration order
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `action` — `String, nullable=False` — TODO: confirm type/nullability/default
- `note` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default


#### Extracted block 2: class `SpineValidationEvent` lines 816-829

```python
0816: class SpineValidationEvent(Base):
0817:     __tablename__ = "spine_validation_events"
0818:     id = Column(Integer, primary_key=True)
0819:     assertion_id = Column(
0820:         Integer,
0821:         ForeignKey("spine_dossier_assertions.id"),
0822:         nullable=False,
0823:     )
0824:     actor = Column(String, nullable=True)
0825:     action = Column(String, nullable=False)
0826:     note = Column(Text, nullable=True)
0827:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0828: 
0829: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `assertion_id` — `Integer, ForeignKey("spine_dossier_assertions.id"` — TODO: confirm FK target and migration order
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `action` — `String, nullable=False` — TODO: confirm type/nullability/default
- `note` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `retention_runs`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1928` (__tablename__)

#### Extracted block 1: class `RetentionRun` lines 1927-2087

```python
1927: class RetentionRun(Base):
1928:     __tablename__ = "retention_runs"
1929:     id = Column(Integer, primary_key=True)
1930:     mode = Column(String, nullable=False)
1931:     status = Column(String, nullable=False)
1932:     result_json = Column(Text, nullable=False)
1933:     actor = Column(String, nullable=True)
1934:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1935: 
1936: 
1937: def create_workbench_job(
1938:     subject_id,
1939:     job_type,
1940:     status,
1941:     priority,
1942:     payload,
1943:     actor=None,
1944: ):
1945:     ensure_configured()
1946:     session = Session()
1947:     try:
1948:         item = WorkbenchJob(
1949:             subject_id=subject_id,
1950:             job_type=job_type,
1951:             status=status,
1952:             priority=priority,
1953:             payload_json=json.dumps(payload or {}),
1954:             actor=actor,
1955:         )
1956:         session.add(item)
1957:         session.commit()
1958:         session.refresh(item)
1959:         return item.id
1960:     finally:
1961:         session.close()
1962: 
1963: 
1964: def get_workbench_job(job_id):
1965:     ensure_configured()
1966:     session = Session()
1967:     try:
1968:         item = session.query(WorkbenchJob).filter_by(id=job_id).first()
1969:         if item:
1970:             session.expunge(item)
1971:         return item
1972:     finally:
1973:         session.close()
1974: 
1975: 
1976: def get_next_queued_workbench_job():
1977:     ensure_configured()
1978:     session = Session()
1979:     try:
1980:         item = (
1981:             session.query(WorkbenchJob)
1982:             .filter_by(status="queued")
1983:             .order_by(WorkbenchJob.priority.asc(), WorkbenchJob.created_at.asc())
1984:             .first()
1985:         )
1986:         if item:
1987:             session.expunge(item)
1988:         return item
1989:     finally:
1990:         session.close()
1991: 
1992: 
1993: def list_workbench_jobs(limit=100):
1994:     ensure_configured()
1995:     session = Session()
1996:     try:
1997:         items = (
1998:             session.query(WorkbenchJob)
1999:             .order_by(WorkbenchJob.created_at.desc())
2000:             .limit(limit)
2001:             .all()
2002:         )
2003:         return _detach_all(session, items)
2004:     finally:
2005:         session.close()
2006: 
2007: 
2008: def update_workbench_job(
2009:     job_id,
2010:     status=None,
2011:     result=None,
2012:     error=None,
2013:     started_at=None,
2014:     finished_at=None,
2015: ):
2016:     ensure_configured()
2017:     session = Session()
2018:     try:
2019:         item = session.query(WorkbenchJob).filter_by(id=job_id).first()
2020:         if not item:
2021:             return None
2022: 
2023:         if status is not None:
2024:             item.status = status
2025:         if result is not None:
2026:             item.result_json = json.dumps(result)
2027:         if error is not None:
2028:             item.error = error
2029:         if started_at is not None:
2030:             item.started_at = started_at
2031:         if finished_at is not None:
2032:             item.finished_at = finished_at
2033: 
2034:         if status == "running":
2035:             item.attempts += 1
2036: 
2037:         item.updated_at = utc_now()
2038:         session.commit()
2039:         return item.id
2040:     finally:
2041:         session.close()
2042: 
2043: 
2044: def record_policy_gate_event(action, allowed, reasons, payload, actor=None):
2045:     ensure_configured()
2046:     session = Session()
2047:     try:
2048:         item = PolicyGateEvent(
2049:             action=action,
2050:             allowed=1 if allowed else 0,
2051:             reasons_json=json.dumps(reasons),
2052:             payload_json=json.dumps(payload or {}),
2053:             actor=actor,
2054:         )
2055:         session.add(item)
2056:         session.commit()
2057:         session.refresh(item)
2058:         return item.id
2059:     finally:
2060:         session.close()
2061: 
2062: 
2063: def list_policy_gate_events(limit=100):
2064:     ensure_configured()
2065:     session = Session()
2066:     try:
2067:         items = (
2068:             session.query(PolicyGateEvent)
2069:             .order_by(PolicyGateEvent.created_at.desc())
2070:             .limit(limit)
2071:             .all()
2072:         )
2073:         return _detach_all(session, items)
2074:     finally:
2075:         session.close()
2076: 
2077: 
2078: def create_retention_run(mode, status, result, actor=None):
2079:     ensure_configured()
2080:     session = Session()
2081:     try:
2082:         item = RetentionRun(
2083:             mode=mode,
2084:             status=status,
2085:             result_json=json.dumps(result),
2086:             actor=actor,
2087:         )
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `mode` — `String, nullable=False` — TODO: confirm type/nullability/default
- `status` — `String, nullable=False` — TODO: confirm type/nullability/default
- `result_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `workbench_jobs`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1899` (__tablename__)

#### Extracted block 1: class `WorkbenchJob` lines 1898-1915

```python
1898: class WorkbenchJob(Base):
1899:     __tablename__ = "workbench_jobs"
1900:     id = Column(Integer, primary_key=True)
1901:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
1902:     job_type = Column(String, nullable=False)
1903:     status = Column(String, nullable=False, default="queued")
1904:     priority = Column(Integer, nullable=False, default=100)
1905:     attempts = Column(Integer, nullable=False, default=0)
1906:     payload_json = Column(Text, nullable=False)
1907:     result_json = Column(Text, nullable=True)
1908:     error = Column(Text, nullable=True)
1909:     actor = Column(String, nullable=True)
1910:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1911:     updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1912:     started_at = Column(DateTime(timezone=True), nullable=True)
1913:     finished_at = Column(DateTime(timezone=True), nullable=True)
1914: 
1915: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `job_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `status` — `String, nullable=False, default="queued"` — TODO: confirm type/nullability/default
- `priority` — `Integer, nullable=False, default=100` — TODO: confirm type/nullability/default
- `attempts` — `Integer, nullable=False, default=0` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `result_json` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `error` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `updated_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `started_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `finished_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `identity_columns`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py:248` (Table())

#### Extracted block 1: class `NumericSqlVariant` lines 231-262

```python
0231: class NumericSqlVariant(TypeDecorator):
0232:     r"""This type casts sql_variant columns in the identity_columns view
0233:     to numeric. This is required because:
0234: 
0235:     * pyodbc does not support sql_variant
0236:     * pymssql under python 2 return the byte representation of the number,
0237:       int 1 is returned as "\x01\x00\x00\x00". On python 3 it returns the
0238:       correct value as string.
0239:     """
0240: 
0241:     impl = Unicode
0242:     cache_ok = True
0243: 
0244:     def column_expression(self, colexpr):
0245:         return cast(colexpr, Numeric(38, 0))
0246: 
0247: 
0248: identity_columns = Table(
0249:     "identity_columns",
0250:     ischema,
0251:     Column("object_id", Integer),
0252:     Column("name", CoerceUnicode),
0253:     Column("column_id", Integer),
0254:     Column("is_identity", Boolean),
0255:     Column("seed_value", NumericSqlVariant),
0256:     Column("increment_value", NumericSqlVariant),
0257:     Column("last_value", NumericSqlVariant),
0258:     Column("is_not_for_replication", Boolean),
0259:     schema="sys",
0260: )
0261: 
0262: 
```

Column hints:
- `object_id` — `Integer` — TODO: confirm type/nullability/default
- `name` — `CoerceUnicode` — TODO: confirm type/nullability/default
- `column_id` — `Integer` — TODO: confirm type/nullability/default
- `is_identity` — `Boolean` — TODO: confirm type/nullability/default
- `seed_value` — `NumericSqlVariant` — TODO: confirm type/nullability/default
- `increment_value` — `NumericSqlVariant` — TODO: confirm type/nullability/default
- `last_value` — `NumericSqlVariant` — TODO: confirm type/nullability/default
- `is_not_for_replication` — `Boolean` — TODO: confirm type/nullability/default

### `identity_edges`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1397` (__tablename__)

#### Extracted block 1: class `IdentityEdge` lines 1396-1409

```python
1396: class IdentityEdge(Base):
1397:     __tablename__ = "identity_edges"
1398:     id = Column(Integer, primary_key=True)
1399:     graph_id = Column(Integer, ForeignKey("identity_graphs.id"), nullable=False)
1400:     from_node_id = Column(Integer, ForeignKey("identity_nodes.id"), nullable=False)
1401:     to_node_id = Column(Integer, ForeignKey("identity_nodes.id"), nullable=False)
1402:     edge_type = Column(String, nullable=False)
1403:     confidence = Column(String, nullable=False, default="0.5")
1404:     evidence_ref = Column(Text, nullable=True)
1405:     validation_state = Column(String, nullable=False, default="unreviewed")
1406:     payload_json = Column(Text, nullable=False)
1407:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1408: 
1409: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `graph_id` — `Integer, ForeignKey("identity_graphs.id"` — TODO: confirm FK target and migration order
- `from_node_id` — `Integer, ForeignKey("identity_nodes.id"` — TODO: confirm FK target and migration order
- `to_node_id` — `Integer, ForeignKey("identity_nodes.id"` — TODO: confirm FK target and migration order
- `edge_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `evidence_ref` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `validation_state` — `String, nullable=False, default="unreviewed"` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `identity_graphs`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1376` (__tablename__)

#### Extracted block 1: class `IdentityGraph` lines 1375-1382

```python
1375: class IdentityGraph(Base):
1376:     __tablename__ = "identity_graphs"
1377:     id = Column(Integer, primary_key=True)
1378:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
1379:     label = Column(String, nullable=True)
1380:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1381: 
1382: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `label` — `String, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `identity_merge_candidates`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1411` (__tablename__)

#### Extracted block 1: class `IdentityMergeCandidate` lines 1410-1570

```python
1410: class IdentityMergeCandidate(Base):
1411:     __tablename__ = "identity_merge_candidates"
1412:     id = Column(Integer, primary_key=True)
1413:     graph_id = Column(Integer, ForeignKey("identity_graphs.id"), nullable=False)
1414:     entity_type = Column(String, nullable=False)
1415:     normalized_value = Column(Text, nullable=False)
1416:     node_ids_json = Column(Text, nullable=False)
1417:     confidence = Column(String, nullable=False, default="0.5")
1418:     state = Column(String, nullable=False, default="unreviewed")
1419:     reason = Column(Text, nullable=True)
1420:     actor = Column(String, nullable=True)
1421:     note = Column(Text, nullable=True)
1422:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1423:     updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1424: 
1425: 
1426: def create_identity_graph(subject_id, label=None):
1427:     ensure_configured()
1428:     session = Session()
1429:     try:
1430:         graph = IdentityGraph(subject_id=subject_id, label=label)
1431:         session.add(graph)
1432:         session.commit()
1433:         session.refresh(graph)
1434:         return graph.id
1435:     finally:
1436:         session.close()
1437: 
1438: 
1439: def get_identity_graph(graph_id):
1440:     ensure_configured()
1441:     session = Session()
1442:     try:
1443:         item = session.query(IdentityGraph).filter_by(id=graph_id).first()
1444:         if item:
1445:             session.expunge(item)
1446:         return item
1447:     finally:
1448:         session.close()
1449: 
1450: 
1451: def get_latest_identity_graph(subject_id):
1452:     ensure_configured()
1453:     session = Session()
1454:     try:
1455:         item = (
1456:             session.query(IdentityGraph)
1457:             .filter_by(subject_id=subject_id)
1458:             .order_by(IdentityGraph.created_at.desc())
1459:             .first()
1460:         )
1461:         if item:
1462:             session.expunge(item)
1463:         return item
1464:     finally:
1465:         session.close()
1466: 
1467: 
1468: def upsert_identity_node(
1469:     graph_id,
1470:     entity_type,
1471:     normalized_value,
1472:     display_value,
1473:     confidence,
1474:     payload,
1475: ):
1476:     ensure_configured()
1477:     session = Session()
1478:     try:
1479:         item = (
1480:             session.query(IdentityNode)
1481:             .filter_by(
1482:                 graph_id=graph_id,
1483:                 entity_type=entity_type,
1484:                 normalized_value=normalized_value,
1485:             )
1486:             .first()
1487:         )
1488:         if not item:
1489:             item = IdentityNode(
1490:                 graph_id=graph_id,
1491:                 entity_type=entity_type,
1492:                 normalized_value=normalized_value,
1493:                 display_value=display_value,
1494:                 confidence=confidence,
1495:                 payload_json=json.dumps(payload),
1496:             )
1497:             session.add(item)
1498:         session.commit()
1499:         session.refresh(item)
1500:         return item.id
1501:     finally:
1502:         session.close()
1503: 
1504: 
1505: def list_identity_nodes(graph_id):
1506:     ensure_configured()
1507:     session = Session()
1508:     try:
1509:         items = (
1510:             session.query(IdentityNode)
1511:             .filter_by(graph_id=graph_id)
1512:             .order_by(IdentityNode.id.asc())
1513:             .all()
1514:         )
1515:         return _detach_all(session, items)
1516:     finally:
1517:         session.close()
1518: 
1519: 
1520: def upsert_identity_edge(
1521:     graph_id,
1522:     from_node_id,
1523:     to_node_id,
1524:     edge_type,
1525:     confidence,
1526:     evidence_ref,
1527:     payload,
1528: ):
1529:     ensure_configured()
1530:     session = Session()
1531:     try:
1532:         item = (
1533:             session.query(IdentityEdge)
1534:             .filter_by(
1535:                 graph_id=graph_id,
1536:                 from_node_id=from_node_id,
1537:                 to_node_id=to_node_id,
1538:                 edge_type=edge_type,
1539:             )
1540:             .first()
1541:         )
1542:         if not item:
1543:             item = IdentityEdge(
1544:                 graph_id=graph_id,
1545:                 from_node_id=from_node_id,
1546:                 to_node_id=to_node_id,
1547:                 edge_type=edge_type,
1548:                 confidence=confidence,
1549:                 evidence_ref=evidence_ref,
1550:                 payload_json=json.dumps(payload),
1551:             )
1552:             session.add(item)
1553:         session.commit()
1554:         session.refresh(item)
1555:         return item.id
1556:     finally:
1557:         session.close()
1558: 
1559: 
1560: def list_identity_edges(graph_id):
1561:     ensure_configured()
1562:     session = Session()
1563:     try:
1564:         items = (
1565:             session.query(IdentityEdge)
1566:             .filter_by(graph_id=graph_id)
1567:             .order_by(IdentityEdge.id.asc())
1568:             .all()
1569:         )
1570:         return _detach_all(session, items)
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `graph_id` — `Integer, ForeignKey("identity_graphs.id"` — TODO: confirm FK target and migration order
- `entity_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `node_ids_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `state` — `String, nullable=False, default="unreviewed"` — TODO: confirm type/nullability/default
- `reason` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `note` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `updated_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `identity_nodes`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1384` (__tablename__)

#### Extracted block 1: class `IdentityNode` lines 1383-1395

```python
1383: class IdentityNode(Base):
1384:     __tablename__ = "identity_nodes"
1385:     id = Column(Integer, primary_key=True)
1386:     graph_id = Column(Integer, ForeignKey("identity_graphs.id"), nullable=False)
1387:     entity_type = Column(String, nullable=False)
1388:     normalized_value = Column(Text, nullable=False)
1389:     display_value = Column(Text, nullable=True)
1390:     confidence = Column(String, nullable=False, default="0.5")
1391:     validation_state = Column(String, nullable=False, default="unreviewed")
1392:     payload_json = Column(Text, nullable=False)
1393:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1394: 
1395: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `graph_id` — `Integer, ForeignKey("identity_graphs.id"` — TODO: confirm FK target and migration order
- `entity_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `normalized_value` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `display_value` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `confidence` — `String, nullable=False, default="0.5"` — TODO: confirm type/nullability/default
- `validation_state` — `String, nullable=False, default="unreviewed"` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `spine_contradictions`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1742` (__tablename__)

#### Extracted block 1: class `SpineContradiction` lines 1741-1855

```python
1741: class SpineContradiction(Base):
1742:     __tablename__ = "spine_contradictions"
1743:     id = Column(Integer, primary_key=True)
1744:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
1745:     conflict_type = Column(String, nullable=False)
1746:     severity = Column(String, nullable=False, default="medium")
1747:     status = Column(String, nullable=False, default="open")
1748:     assertion_ids_json = Column(Text, nullable=False)
1749:     summary = Column(Text, nullable=False)
1750:     payload_json = Column(Text, nullable=False)
1751:     actor = Column(String, nullable=True)
1752:     note = Column(Text, nullable=True)
1753:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1754:     updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1755: 
1756: 
1757: def clear_spine_contradictions(subject_id):
1758:     ensure_configured()
1759:     session = Session()
1760:     try:
1761:         session.query(SpineContradiction).filter_by(
1762:             subject_id=subject_id
1763:         ).delete()
1764:         session.commit()
1765:     finally:
1766:         session.close()
1767: 
1768: 
1769: def create_spine_contradiction(
1770:     subject_id,
1771:     conflict_type,
1772:     severity,
1773:     status,
1774:     assertion_ids,
1775:     summary,
1776:     payload,
1777: ):
1778:     ensure_configured()
1779:     session = Session()
1780:     try:
1781:         item = SpineContradiction(
1782:             subject_id=subject_id,
1783:             conflict_type=conflict_type,
1784:             severity=severity,
1785:             status=status,
1786:             assertion_ids_json=json.dumps(assertion_ids),
1787:             summary=summary,
1788:             payload_json=json.dumps(payload),
1789:         )
1790:         session.add(item)
1791:         session.commit()
1792:         session.refresh(item)
1793:         return item.id
1794:     finally:
1795:         session.close()
1796: 
1797: 
1798: def list_spine_contradictions(subject_id, limit=1000):
1799:     ensure_configured()
1800:     session = Session()
1801:     try:
1802:         items = (
1803:             session.query(SpineContradiction)
1804:             .filter_by(subject_id=subject_id)
1805:             .order_by(SpineContradiction.severity.desc())
1806:             .limit(limit)
1807:             .all()
1808:         )
1809:         return _detach_all(session, items)
1810:     finally:
1811:         session.close()
1812: 
1813: 
1814: def get_spine_contradiction(contradiction_id):
1815:     ensure_configured()
1816:     session = Session()
1817:     try:
1818:         item = (
1819:             session.query(SpineContradiction)
1820:             .filter_by(id=contradiction_id)
1821:             .first()
1822:         )
1823:         if item:
1824:             session.expunge(item)
1825:         return item
1826:     finally:
1827:         session.close()
1828: 
1829: 
1830: def update_spine_contradiction(
1831:     contradiction_id,
1832:     status,
1833:     actor=None,
1834:     note=None,
1835: ):
1836:     ensure_configured()
1837:     session = Session()
1838:     try:
1839:         item = (
1840:             session.query(SpineContradiction)
1841:             .filter_by(id=contradiction_id)
1842:             .first()
1843:         )
1844:         if not item:
1845:             return None
1846:         item.status = status
1847:         item.actor = actor
1848:         item.note = note
1849:         item.updated_at = utc_now()
1850:         session.commit()
1851:         return item.id
1852:     finally:
1853:         session.close()
1854: 
1855: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `conflict_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `severity` — `String, nullable=False, default="medium"` — TODO: confirm type/nullability/default
- `status` — `String, nullable=False, default="open"` — TODO: confirm type/nullability/default
- `assertion_ids_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `summary` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `note` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default
- `updated_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `policy_gate_events`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `policy`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:1917` (__tablename__)

#### Extracted block 1: class `PolicyGateEvent` lines 1916-1926

```python
1916: class PolicyGateEvent(Base):
1917:     __tablename__ = "policy_gate_events"
1918:     id = Column(Integer, primary_key=True)
1919:     action = Column(String, nullable=False)
1920:     allowed = Column(Integer, nullable=False)
1921:     reasons_json = Column(Text, nullable=False)
1922:     payload_json = Column(Text, nullable=False)
1923:     actor = Column(String, nullable=True)
1924:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1925: 
1926: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `action` — `String, nullable=False` — TODO: confirm type/nullability/default
- `allowed` — `Integer, nullable=False` — TODO: confirm type/nullability/default
- `reasons_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `actor` — `String, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `connector_runs`

- classification: `PASS`
- priority: `P1` / `70`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `src/socmint/database.py:120` (__tablename__)

#### Extracted block 1: class `ConnectorRun` lines 119-132

```python
0119: class ConnectorRun(Base):
0120:     __tablename__ = "connector_runs"
0121:     id = Column(Integer, primary_key=True)
0122:     target_id = Column(Integer, ForeignKey("targets.id"), nullable=True)
0123:     target_value = Column(String, nullable=False)
0124:     target_type = Column(String, nullable=False)
0125:     connector = Column(String, nullable=False)
0126:     status = Column(String, nullable=False)
0127:     command = Column(Text, nullable=True)
0128:     raw_result = Column(Text, nullable=False)
0129:     error = Column(Text, nullable=True)
0130:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
0131: 
0132: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `target_id` — `Integer, ForeignKey("targets.id"` — TODO: confirm FK target and migration order
- `target_value` — `String, nullable=False` — TODO: confirm type/nullability/default
- `target_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `connector` — `String, nullable=False` — TODO: confirm type/nullability/default
- `status` — `String, nullable=False` — TODO: confirm type/nullability/default
- `command` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `raw_result` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `error` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `all_tab_identity_cols`

- classification: `PASS`
- priority: `P1` / `70`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py:228` (Table())

#### Extracted block 1: context `None` lines 183-273

```python
0183: 
0184: all_mviews = Table(
0185:     "all_mviews" + DB_LINK_PLACEHOLDER,
0186:     dictionary_meta,
0187:     Column("owner", VARCHAR2(128), nullable=False),
0188:     Column("mview_name", VARCHAR2(128), nullable=False),
0189:     Column("container_name", VARCHAR2(128), nullable=False),
0190:     Column("query", LONG),
0191:     Column("query_len", NUMBER(38)),
0192:     Column("updatable", VARCHAR2(1)),
0193:     Column("update_log", VARCHAR2(128)),
0194:     Column("master_rollback_seg", VARCHAR2(128)),
0195:     Column("master_link", VARCHAR2(128)),
0196:     Column("rewrite_enabled", VARCHAR2(1)),
0197:     Column("rewrite_capability", VARCHAR2(9)),
0198:     Column("refresh_mode", VARCHAR2(6)),
0199:     Column("refresh_method", VARCHAR2(8)),
0200:     Column("build_mode", VARCHAR2(9)),
0201:     Column("fast_refreshable", VARCHAR2(18)),
0202:     Column("last_refresh_type", VARCHAR2(8)),
0203:     Column("last_refresh_date", DATE),
0204:     Column("last_refresh_end_time", DATE),
0205:     Column("staleness", VARCHAR2(19)),
0206:     Column("after_fast_refresh", VARCHAR2(19)),
0207:     Column("unknown_prebuilt", VARCHAR2(1)),
0208:     Column("unknown_plsql_func", VARCHAR2(1)),
0209:     Column("unknown_external_table", VARCHAR2(1)),
0210:     Column("unknown_consider_fresh", VARCHAR2(1)),
0211:     Column("unknown_import", VARCHAR2(1)),
0212:     Column("unknown_trusted_fd", VARCHAR2(1)),
0213:     Column("compile_state", VARCHAR2(19)),
0214:     Column("use_no_index", VARCHAR2(1)),
0215:     Column("stale_since", DATE),
0216:     Column("num_pct_tables", NUMBER),
0217:     Column("num_fresh_pct_regions", NUMBER),
0218:     Column("num_stale_pct_regions", NUMBER),
0219:     Column("segment_created", VARCHAR2(3)),
0220:     Column("evaluation_edition", VARCHAR2(128)),
0221:     Column("unusable_before", VARCHAR2(128)),
0222:     Column("unusable_beginning", VARCHAR2(128)),
0223:     Column("default_collation", VARCHAR2(100)),
0224:     Column("on_query_computation", VARCHAR2(1)),
0225:     Column("auto", VARCHAR2(3)),
0226: ).alias("a_mviews")
0227: 
0228: all_tab_identity_cols = Table(
0229:     "all_tab_identity_cols" + DB_LINK_PLACEHOLDER,
0230:     dictionary_meta,
0231:     Column("owner", VARCHAR2(128), nullable=False),
0232:     Column("table_name", VARCHAR2(128), nullable=False),
0233:     Column("column_name", VARCHAR2(128), nullable=False),
0234:     Column("generation_type", VARCHAR2(10)),
0235:     Column("sequence_name", VARCHAR2(128), nullable=False),
0236:     Column("identity_options", VARCHAR2(298)),
0237: ).alias("a_tab_identity_cols")
0238: 
0239: all_tab_cols = Table(
0240:     "all_tab_cols" + DB_LINK_PLACEHOLDER,
0241:     dictionary_meta,
0242:     Column("owner", VARCHAR2(128), nullable=False),
0243:     Column("table_name", VARCHAR2(128), nullable=False),
0244:     Column("column_name", VARCHAR2(128), nullable=False),
0245:     Column("data_type", VARCHAR2(128)),
0246:     Column("data_type_mod", VARCHAR2(3)),
0247:     Column("data_type_owner", VARCHAR2(128)),
0248:     Column("data_length", NUMBER, nullable=False),
0249:     Column("data_precision", NUMBER),
0250:     Column("data_scale", NUMBER),
0251:     Column("nullable", VARCHAR2(1)),
0252:     Column("column_id", NUMBER),
0253:     Column("default_length", NUMBER),
0254:     Column("data_default", LONG),
0255:     Column("num_distinct", NUMBER),
0256:     Column("low_value", RAW(1000)),
0257:     Column("high_value", RAW(1000)),
0258:     Column("density", NUMBER),
0259:     Column("num_nulls", NUMBER),
0260:     Column("num_buckets", NUMBER),
0261:     Column("last_analyzed", DATE),
0262:     Column("sample_size", NUMBER),
0263:     Column("character_set_name", VARCHAR2(44)),
0264:     Column("char_col_decl_length", NUMBER),
0265:     Column("global_stats", VARCHAR2(3)),
0266:     Column("user_stats", VARCHAR2(3)),
0267:     Column("avg_col_len", NUMBER),
0268:     Column("char_length", NUMBER),
0269:     Column("char_used", VARCHAR2(1)),
0270:     Column("v80_fmt_image", VARCHAR2(3)),
0271:     Column("data_upgraded", VARCHAR2(3)),
0272:     Column("hidden_column", VARCHAR2(3)),
0273:     Column("virtual_column", VARCHAR2(3)),
```

Column hints:
- `owner` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `mview_name` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `container_name` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `query` — `LONG` — TODO: confirm type/nullability/default
- `query_len` — `NUMBER(38` — TODO: confirm type/nullability/default
- `updatable` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `update_log` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `master_rollback_seg` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `master_link` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `rewrite_enabled` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `rewrite_capability` — `VARCHAR2(9` — TODO: confirm type/nullability/default
- `refresh_mode` — `VARCHAR2(6` — TODO: confirm type/nullability/default
- `refresh_method` — `VARCHAR2(8` — TODO: confirm type/nullability/default
- `build_mode` — `VARCHAR2(9` — TODO: confirm type/nullability/default
- `fast_refreshable` — `VARCHAR2(18` — TODO: confirm type/nullability/default
- `last_refresh_type` — `VARCHAR2(8` — TODO: confirm type/nullability/default
- `last_refresh_date` — `DATE` — TODO: confirm type/nullability/default
- `last_refresh_end_time` — `DATE` — TODO: confirm type/nullability/default
- `staleness` — `VARCHAR2(19` — TODO: confirm type/nullability/default
- `after_fast_refresh` — `VARCHAR2(19` — TODO: confirm type/nullability/default
- `unknown_prebuilt` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `unknown_plsql_func` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `unknown_external_table` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `unknown_consider_fresh` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `unknown_import` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `unknown_trusted_fd` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `compile_state` — `VARCHAR2(19` — TODO: confirm type/nullability/default
- `use_no_index` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `stale_since` — `DATE` — TODO: confirm type/nullability/default
- `num_pct_tables` — `NUMBER` — TODO: confirm type/nullability/default
- `num_fresh_pct_regions` — `NUMBER` — TODO: confirm type/nullability/default
- `num_stale_pct_regions` — `NUMBER` — TODO: confirm type/nullability/default
- `segment_created` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `evaluation_edition` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `unusable_before` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `unusable_beginning` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `default_collation` — `VARCHAR2(100` — TODO: confirm type/nullability/default
- `on_query_computation` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `auto` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `table_name` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `column_name` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `generation_type` — `VARCHAR2(10` — TODO: confirm type/nullability/default
- `sequence_name` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `identity_options` — `VARCHAR2(298` — TODO: confirm type/nullability/default
- `data_type` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `data_type_mod` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `data_type_owner` — `VARCHAR2(128` — TODO: confirm type/nullability/default
- `data_length` — `NUMBER, nullable=False` — TODO: confirm type/nullability/default
- `data_precision` — `NUMBER` — TODO: confirm type/nullability/default
- `data_scale` — `NUMBER` — TODO: confirm type/nullability/default
- `nullable` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `column_id` — `NUMBER` — TODO: confirm type/nullability/default
- `default_length` — `NUMBER` — TODO: confirm type/nullability/default
- `data_default` — `LONG` — TODO: confirm type/nullability/default
- `num_distinct` — `NUMBER` — TODO: confirm type/nullability/default
- `low_value` — `RAW(1000` — TODO: confirm type/nullability/default
- `high_value` — `RAW(1000` — TODO: confirm type/nullability/default
- `density` — `NUMBER` — TODO: confirm type/nullability/default
- `num_nulls` — `NUMBER` — TODO: confirm type/nullability/default
- `num_buckets` — `NUMBER` — TODO: confirm type/nullability/default
- `last_analyzed` — `DATE` — TODO: confirm type/nullability/default
- `sample_size` — `NUMBER` — TODO: confirm type/nullability/default
- `character_set_name` — `VARCHAR2(44` — TODO: confirm type/nullability/default
- `char_col_decl_length` — `NUMBER` — TODO: confirm type/nullability/default
- `global_stats` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `user_stats` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `avg_col_len` — `NUMBER` — TODO: confirm type/nullability/default
- `char_length` — `NUMBER` — TODO: confirm type/nullability/default
- `char_used` — `VARCHAR2(1` — TODO: confirm type/nullability/default
- `v80_fmt_image` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `data_upgraded` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `hidden_column` — `VARCHAR2(3` — TODO: confirm type/nullability/default
- `virtual_column` — `VARCHAR2(3` — TODO: confirm type/nullability/default

### `media_profile_enrichments`

- classification: `PASS_WITH_REVIEW_NOTES`
- priority: `P1` / `65`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `human_review_for_rename_or_indirect_coverage`

Sources:
- `src/socmint/database.py:1650` (__tablename__)

Possible indirect/rename coverage:
- `profiles` — normalized substring/pluralization similarity (medium)
- `media` — normalized substring/pluralization similarity (medium)

#### Extracted block 1: class `MediaProfileEnrichment` lines 1649-1740

```python
1649: class MediaProfileEnrichment(Base):
1650:     __tablename__ = "media_profile_enrichments"
1651:     id = Column(Integer, primary_key=True)
1652:     subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
1653:     observation_id = Column(Integer, ForeignKey("spine_observations.id"), nullable=True)
1654:     enrichment_type = Column(String, nullable=False)
1655:     status = Column(String, nullable=False)
1656:     source_value = Column(Text, nullable=True)
1657:     artifact_ref = Column(Text, nullable=True)
1658:     payload_json = Column(Text, nullable=False)
1659:     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
1660: 
1661: 
1662: def create_media_profile_enrichment(
1663:     subject_id,
1664:     observation_id,
1665:     enrichment_type,
1666:     status,
1667:     source_value,
1668:     artifact_ref,
1669:     payload,
1670: ):
1671:     ensure_configured()
1672:     session = Session()
1673:     try:
1674:         item = MediaProfileEnrichment(
1675:             subject_id=subject_id,
1676:             observation_id=observation_id,
1677:             enrichment_type=enrichment_type,
1678:             status=status,
1679:             source_value=source_value,
1680:             artifact_ref=artifact_ref,
1681:             payload_json=json.dumps(payload),
1682:         )
1683:         session.add(item)
1684:         session.commit()
1685:         session.refresh(item)
1686:         return item.id
1687:     finally:
1688:         session.close()
1689: 
1690: 
1691: def list_media_profile_enrichments(subject_id, limit=1000):
1692:     ensure_configured()
1693:     session = Session()
1694:     try:
1695:         items = (
1696:             session.query(MediaProfileEnrichment)
1697:             .filter_by(subject_id=subject_id)
1698:             .order_by(MediaProfileEnrichment.created_at.desc())
1699:             .limit(limit)
1700:             .all()
1701:         )
1702:         return _detach_all(session, items)
1703:     finally:
1704:         session.close()
1705: 
1706: 
1707: def get_media_profile_enrichment(enrichment_id):
1708:     ensure_configured()
1709:     session = Session()
1710:     try:
1711:         item = (
1712:             session.query(MediaProfileEnrichment)
1713:             .filter_by(id=enrichment_id)
1714:             .first()
1715:         )
1716:         if item:
1717:             session.expunge(item)
1718:         return item
1719:     finally:
1720:         session.close()
1721: 
1722: 
1723: def update_media_profile_enrichment_payload(enrichment_id, payload):
1724:     ensure_configured()
1725:     session = Session()
1726:     try:
1727:         item = (
1728:             session.query(MediaProfileEnrichment)
1729:             .filter_by(id=enrichment_id)
1730:             .first()
1731:         )
1732:         if not item:
1733:             return None
1734:         item.payload_json = json.dumps(payload)
1735:         session.commit()
1736:         return item.id
1737:     finally:
1738:         session.close()
1739: 
1740: 
```

Column hints:
- `id` — `Integer, primary_key=True` — TODO: confirm primary key
- `subject_id` — `Integer, ForeignKey("spine_subjects.id"` — TODO: confirm FK target and migration order
- `observation_id` — `Integer, ForeignKey("spine_observations.id"` — TODO: confirm FK target and migration order
- `enrichment_type` — `String, nullable=False` — TODO: confirm type/nullability/default
- `status` — `String, nullable=False` — TODO: confirm type/nullability/default
- `source_value` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `artifact_ref` — `Text, nullable=True` — TODO: confirm type/nullability/default
- `payload_json` — `Text, nullable=False` — TODO: confirm type/nullability/default
- `created_at` — `DateTime(timezone=True` — TODO: confirm timezone/default

### `employee`

- classification: `REVIEW`
- priority: `P1` / `60`
- domain: `uncategorized`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`

Sources:
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py:514` (__tablename__)
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py:542` (__tablename__)
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py:55` (__tablename__)
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py:379` (__tablename__)
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py:548` (__tablename__)
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py:564` (__tablename__)
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py:583` (__tablename__)

#### Extracted block 1: context `None` lines 469-559

```python
0469:     # automap base
0470:     Base = automap_base()
0471: 
0472:     engine = create_engine("sqlite:///mydatabase.db")
0473:     Base.prepare(autoload_with=engine, generate_relationship=_gen_relationship)
0474: 
0475: Many-to-Many relationships
0476: --------------------------
0477: 
0478: :mod:`.sqlalchemy.ext.automap` will generate many-to-many relationships, e.g.
0479: those which contain a ``secondary`` argument.  The process for producing these
0480: is as follows:
0481: 
0482: 1. A given :class:`_schema.Table` is examined for
0483:    :class:`_schema.ForeignKeyConstraint`
0484:    objects, before any mapped class has been assigned to it.
0485: 
0486: 2. If the table contains two and exactly two
0487:    :class:`_schema.ForeignKeyConstraint`
0488:    objects, and all columns within this table are members of these two
0489:    :class:`_schema.ForeignKeyConstraint` objects, the table is assumed to be a
0490:    "secondary" table, and will **not be mapped directly**.
0491: 
0492: 3. The two (or one, for self-referential) external tables to which the
0493:    :class:`_schema.Table`
0494:    refers to are matched to the classes to which they will be
0495:    mapped, if any.
0496: 
0497: 4. If mapped classes for both sides are located, a many-to-many bi-directional
0498:    :func:`_orm.relationship` / :func:`.backref`
0499:    pair is created between the two
0500:    classes.
0501: 
0502: 5. The override logic for many-to-many works the same as that of one-to-many/
0503:    many-to-one; the :func:`.generate_relationship` function is called upon
0504:    to generate the structures and existing attributes will be maintained.
0505: 
0506: Relationships with Inheritance
0507: ------------------------------
0508: 
0509: :mod:`.sqlalchemy.ext.automap` will not generate any relationships between
0510: two classes that are in an inheritance relationship.   That is, with two
0511: classes given as follows::
0512: 
0513:     class Employee(Base):
0514:         __tablename__ = "employee"
0515:         id = Column(Integer, primary_key=True)
0516:         type = Column(String(50))
0517:         __mapper_args__ = {
0518:             "polymorphic_identity": "employee",
0519:             "polymorphic_on": type,
0520:         }
0521: 
0522: 
0523:     class Engineer(Employee):
0524:         __tablename__ = "engineer"
0525:         id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
0526:         __mapper_args__ = {
0527:             "polymorphic_identity": "engineer",
0528:         }
0529: 
0530: The foreign key from ``Engineer`` to ``Employee`` is used not for a
0531: relationship, but to establish joined inheritance between the two classes.
0532: 
0533: Note that this means automap will not generate *any* relationships
0534: for foreign keys that link from a subclass to a superclass.  If a mapping
0535: has actual relationships from subclass to superclass as well, those
0536: need to be explicit.  Below, as we have two separate foreign keys
0537: from ``Engineer`` to ``Employee``, we need to set up both the relationship
0538: we want as well as the ``inherit_condition``, as these are not things
0539: SQLAlchemy can guess::
0540: 
0541:     class Employee(Base):
0542:         __tablename__ = "employee"
0543:         id = Column(Integer, primary_key=True)
0544:         type = Column(String(50))
0545: 
0546:         __mapper_args__ = {
0547:             "polymorphic_identity": "employee",
0548:             "polymorphic_on": type,
0549:         }
0550: 
0551: 
0552:     class Engineer(Employee):
0553:         __tablename__ = "engineer"
0554:         id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
0555:         favorite_employee_id = Column(Integer, ForeignKey("employee.id"))
0556: 
0557:         favorite_employee = relationship(
0558:             Employee, foreign_keys=favorite_employee_id
0559:         )
```

Column hints:
- none detected


#### Extracted block 2: context `None` lines 497-587

```python
0497: 4. If mapped classes for both sides are located, a many-to-many bi-directional
0498:    :func:`_orm.relationship` / :func:`.backref`
0499:    pair is created between the two
0500:    classes.
0501: 
0502: 5. The override logic for many-to-many works the same as that of one-to-many/
0503:    many-to-one; the :func:`.generate_relationship` function is called upon
0504:    to generate the structures and existing attributes will be maintained.
0505: 
0506: Relationships with Inheritance
0507: ------------------------------
0508: 
0509: :mod:`.sqlalchemy.ext.automap` will not generate any relationships between
0510: two classes that are in an inheritance relationship.   That is, with two
0511: classes given as follows::
0512: 
0513:     class Employee(Base):
0514:         __tablename__ = "employee"
0515:         id = Column(Integer, primary_key=True)
0516:         type = Column(String(50))
0517:         __mapper_args__ = {
0518:             "polymorphic_identity": "employee",
0519:             "polymorphic_on": type,
0520:         }
0521: 
0522: 
0523:     class Engineer(Employee):
0524:         __tablename__ = "engineer"
0525:         id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
0526:         __mapper_args__ = {
0527:             "polymorphic_identity": "engineer",
0528:         }
0529: 
0530: The foreign key from ``Engineer`` to ``Employee`` is used not for a
0531: relationship, but to establish joined inheritance between the two classes.
0532: 
0533: Note that this means automap will not generate *any* relationships
0534: for foreign keys that link from a subclass to a superclass.  If a mapping
0535: has actual relationships from subclass to superclass as well, those
0536: need to be explicit.  Below, as we have two separate foreign keys
0537: from ``Engineer`` to ``Employee``, we need to set up both the relationship
0538: we want as well as the ``inherit_condition``, as these are not things
0539: SQLAlchemy can guess::
0540: 
0541:     class Employee(Base):
0542:         __tablename__ = "employee"
0543:         id = Column(Integer, primary_key=True)
0544:         type = Column(String(50))
0545: 
0546:         __mapper_args__ = {
0547:             "polymorphic_identity": "employee",
0548:             "polymorphic_on": type,
0549:         }
0550: 
0551: 
0552:     class Engineer(Employee):
0553:         __tablename__ = "engineer"
0554:         id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
0555:         favorite_employee_id = Column(Integer, ForeignKey("employee.id"))
0556: 
0557:         favorite_employee = relationship(
0558:             Employee, foreign_keys=favorite_employee_id
0559:         )
0560: 
0561:         __mapper_args__ = {
0562:             "polymorphic_identity": "engineer",
0563:             "inherit_condition": id == Employee.id,
0564:         }
0565: 
0566: Handling Simple Naming Conflicts
0567: --------------------------------
0568: 
0569: In the case of naming conflicts during mapping, override any of
0570: :func:`.classname_for_table`, :func:`.name_for_scalar_relationship`,
0571: and :func:`.name_for_collection_relationship` as needed.  For example, if
0572: automap is attempting to name a many-to-one relationship the same as an
0573: existing column, an alternate convention can be conditionally selected.  Given
0574: a schema:
0575: 
0576: .. sourcecode:: sql
0577: 
0578:     CREATE TABLE table_a (
0579:         id INTEGER PRIMARY KEY
0580:     );
0581: 
0582:     CREATE TABLE table_b (
0583:         id INTEGER PRIMARY KEY,
0584:         table_a INTEGER,
0585:         FOREIGN KEY(table_a) REFERENCES table_a(id)
0586:     );
0587: 
```

Column hints:
- none detected


#### Extracted block 3: context `None` lines 10-100

```python
0010: """Public API functions and helpers for declarative."""
0011: from __future__ import annotations
0012: 
0013: import collections
0014: import contextlib
0015: from typing import Any
0016: from typing import Callable
0017: from typing import TYPE_CHECKING
0018: from typing import Union
0019: 
0020: from ... import exc as sa_exc
0021: from ...engine import Connection
0022: from ...engine import Engine
0023: from ...orm import exc as orm_exc
0024: from ...orm import relationships
0025: from ...orm.base import _mapper_or_none
0026: from ...orm.clsregistry import _resolver
0027: from ...orm.decl_base import _DeferredMapperConfig
0028: from ...orm.util import polymorphic_union
0029: from ...schema import Table
0030: from ...util import OrderedDict
0031: 
0032: if TYPE_CHECKING:
0033:     from ...sql.schema import MetaData
0034: 
0035: 
0036: class ConcreteBase:
0037:     """A helper class for 'concrete' declarative mappings.
0038: 
0039:     :class:`.ConcreteBase` will use the :func:`.polymorphic_union`
0040:     function automatically, against all tables mapped as a subclass
0041:     to this class.   The function is called via the
0042:     ``__declare_last__()`` function, which is essentially
0043:     a hook for the :meth:`.after_configured` event.
0044: 
0045:     :class:`.ConcreteBase` produces a mapped
0046:     table for the class itself.  Compare to :class:`.AbstractConcreteBase`,
0047:     which does not.
0048: 
0049:     Example::
0050: 
0051:         from sqlalchemy.ext.declarative import ConcreteBase
0052: 
0053: 
0054:         class Employee(ConcreteBase, Base):
0055:             __tablename__ = "employee"
0056:             employee_id = Column(Integer, primary_key=True)
0057:             name = Column(String(50))
0058:             __mapper_args__ = {
0059:                 "polymorphic_identity": "employee",
0060:                 "concrete": True,
0061:             }
0062: 
0063: 
0064:         class Manager(Employee):
0065:             __tablename__ = "manager"
0066:             employee_id = Column(Integer, primary_key=True)
0067:             name = Column(String(50))
0068:             manager_data = Column(String(40))
0069:             __mapper_args__ = {
0070:                 "polymorphic_identity": "manager",
0071:                 "concrete": True,
0072:             }
0073: 
0074:     The name of the discriminator column used by :func:`.polymorphic_union`
0075:     defaults to the name ``type``.  To suit the use case of a mapping where an
0076:     actual column in a mapped table is already named ``type``, the
0077:     discriminator name can be configured by setting the
0078:     ``_concrete_discriminator_name`` attribute::
0079: 
0080:         class Employee(ConcreteBase, Base):
0081:             _concrete_discriminator_name = "_concrete_discriminator"
0082: 
0083:     .. versionadded:: 1.3.19 Added the ``_concrete_discriminator_name``
0084:        attribute to :class:`_declarative.ConcreteBase` so that the
0085:        virtual discriminator column name can be customized.
0086: 
0087:     .. versionchanged:: 1.4.2 The ``_concrete_discriminator_name`` attribute
0088:        need only be placed on the basemost class to take correct effect for
0089:        all subclasses.   An explicit error message is now raised if the
0090:        mapped column names conflict with the discriminator name, whereas
0091:        in the 1.3.x series there would be some warnings and then a non-useful
0092:        query would be generated.
0093: 
0094:     .. seealso::
0095: 
0096:         :class:`.AbstractConcreteBase`
0097: 
0098:         :ref:`concrete_inheritance`
0099: 
0100: 
```

Column hints:
- none detected


#### Extracted block 4: class `declared_attr` lines 332-467

```python
0332: class declared_attr(interfaces._MappedAttribute[_T], _declared_attr_common):
0333:     """Mark a class-level method as representing the definition of
0334:     a mapped property or Declarative directive.
0335: 
0336:     :class:`_orm.declared_attr` is typically applied as a decorator to a class
0337:     level method, turning the attribute into a scalar-like property that can be
0338:     invoked from the uninstantiated class. The Declarative mapping process
0339:     looks for these :class:`_orm.declared_attr` callables as it scans classes,
0340:     and assumes any attribute marked with :class:`_orm.declared_attr` will be a
0341:     callable that will produce an object specific to the Declarative mapping or
0342:     table configuration.
0343: 
0344:     :class:`_orm.declared_attr` is usually applicable to
0345:     :ref:`mixins <orm_mixins_toplevel>`, to define relationships that are to be
0346:     applied to different implementors of the class. It may also be used to
0347:     define dynamically generated column expressions and other Declarative
0348:     attributes.
0349: 
0350:     Example::
0351: 
0352:         class ProvidesUserMixin:
0353:             "A mixin that adds a 'user' relationship to classes."
0354: 
0355:             user_id: Mapped[int] = mapped_column(ForeignKey("user_table.id"))
0356: 
0357:             @declared_attr
0358:             def user(cls) -> Mapped["User"]:
0359:                 return relationship("User")
0360: 
0361:     When used with Declarative directives such as ``__tablename__``, the
0362:     :meth:`_orm.declared_attr.directive` modifier may be used which indicates
0363:     to :pep:`484` typing tools that the given method is not dealing with
0364:     :class:`_orm.Mapped` attributes::
0365: 
0366:         class CreateTableName:
0367:             @declared_attr.directive
0368:             def __tablename__(cls) -> str:
0369:                 return cls.__name__.lower()
0370: 
0371:     :class:`_orm.declared_attr` can also be applied directly to mapped
0372:     classes, to allow for attributes that dynamically configure themselves
0373:     on subclasses when using mapped inheritance schemes.   Below
0374:     illustrates :class:`_orm.declared_attr` to create a dynamic scheme
0375:     for generating the :paramref:`_orm.Mapper.polymorphic_identity` parameter
0376:     for subclasses::
0377: 
0378:         class Employee(Base):
0379:             __tablename__ = "employee"
0380: 
0381:             id: Mapped[int] = mapped_column(primary_key=True)
0382:             type: Mapped[str] = mapped_column(String(50))
0383: 
0384:             @declared_attr.directive
0385:             def __mapper_args__(cls) -> Dict[str, Any]:
0386:                 if cls.__name__ == "Employee":
0387:                     return {
0388:                         "polymorphic_on": cls.type,
0389:                         "polymorphic_identity": "Employee",
0390:                     }
0391:                 else:
0392:                     return {"polymorphic_identity": cls.__name__}
0393: 
0394: 
0395:         class Engineer(Employee):
0396:             pass
0397: 
0398:     :class:`_orm.declared_attr` supports decorating functions that are
0399:     explicitly decorated with ``@classmethod``. This is never necessary from a
0400:     runtime perspective, however may be needed in order to support :pep:`484`
0401:     typing tools that don't otherwise recognize the decorated function as
0402:     having class-level behaviors for the ``cls`` parameter::
0403: 
0404:         class SomethingMixin:
0405:             x: Mapped[int]
0406:             y: Mapped[int]
0407: 
0408:             @declared_attr
0409:             @classmethod
0410:             def x_plus_y(cls) -> Mapped[int]:
0411:                 return column_property(cls.x + cls.y)
0412: 
0413:     .. versionadded:: 2.0 - :class:`_orm.declared_attr` can accommodate a
0414:        function decorated with ``@classmethod`` to help with :pep:`484`
0415:        integration where needed.
0416: 
0417: 
0418:     .. seealso::
0419: 
0420:         :ref:`orm_mixins_toplevel` - Declarative Mixin documentation with
0421:         background on use patterns for :class:`_orm.declared_attr`.
0422: 
0423:     """  # noqa: E501
0424: 
0425:     if typing.TYPE_CHECKING:
0426: 
0427:         def __init__(
0428:             self,
0429:             fn: _DeclaredAttrDecorated[_T],
0430:             cascading: bool = False,
0431:         ): ...
0432: 
0433:         def __set__(self, instance: Any, value: Any) -> None: ...
0434: 
0435:         def __delete__(self, instance: Any) -> None: ...
0436: 
0437:         # this is the Mapped[] API where at class descriptor get time we want
0438:         # the type checker to see InstrumentedAttribute[_T].   However the
0439:         # callable function prior to mapping in fact calls the given
0440:         # declarative function that does not return InstrumentedAttribute
0441:         @overload
0442:         def __get__(
0443:             self, instance: None, owner: Any
0444:         ) -> InstrumentedAttribute[_T]: ...
0445: 
0446:         @overload
0447:         def __get__(self, instance: object, owner: Any) -> _T: ...
0448: 
0449:         def __get__(
0450:             self, instance: Optional[object], owner: Any
0451:         ) -> Union[InstrumentedAttribute[_T], _T]: ...
0452: 
0453:     @hybridmethod
0454:     def _stateful(cls, **kw: Any) -> _stateful_declared_attr[_T]:
0455:         return _stateful_declared_attr(**kw)
0456: 
0457:     @hybridproperty
0458:     def directive(cls) -> _declared_directive[Any]:
0459:         # see mapping_api.rst for docstring
0460:         return _declared_directive  # type: ignore
0461: 
0462:     @hybridproperty
0463:     def cascading(cls) -> _stateful_declared_attr[_T]:
0464:         # see mapping_api.rst for docstring
0465:         return cls._stateful(cascading=True)
0466: 
0467: 
```

Column hints:
- none detected


#### Extracted block 5: context `None` lines 503-593

```python
0503:            referential integrity and will not be issuing its own CASCADE
0504:            operation for an update.  The unit of work process will
0505:            emit an UPDATE statement for the dependent columns during a
0506:            primary key change.
0507: 
0508:            .. seealso::
0509: 
0510:                :ref:`passive_updates` - description of a similar feature as
0511:                used with :func:`_orm.relationship`
0512: 
0513:                :paramref:`.mapper.passive_deletes` - supporting ON DELETE
0514:                CASCADE for joined-table inheritance mappers
0515: 
0516:         :param polymorphic_load: Specifies "polymorphic loading" behavior
0517:          for a subclass in an inheritance hierarchy (joined and single
0518:          table inheritance only).   Valid values are:
0519: 
0520:           * "'inline'" - specifies this class should be part of
0521:             the "with_polymorphic" mappers, e.g. its columns will be included
0522:             in a SELECT query against the base.
0523: 
0524:           * "'selectin'" - specifies that when instances of this class
0525:             are loaded, an additional SELECT will be emitted to retrieve
0526:             the columns specific to this subclass.  The SELECT uses
0527:             IN to fetch multiple subclasses at once.
0528: 
0529:          .. versionadded:: 1.2
0530: 
0531:          .. seealso::
0532: 
0533:             :ref:`with_polymorphic_mapper_config`
0534: 
0535:             :ref:`polymorphic_selectin`
0536: 
0537:         :param polymorphic_on: Specifies the column, attribute, or
0538:           SQL expression used to determine the target class for an
0539:           incoming row, when inheriting classes are present.
0540: 
0541:           May be specified as a string attribute name, or as a SQL
0542:           expression such as a :class:`_schema.Column` or in a Declarative
0543:           mapping a :func:`_orm.mapped_column` object.  It is typically
0544:           expected that the SQL expression corresponds to a column in the
0545:           base-most mapped :class:`.Table`::
0546: 
0547:             class Employee(Base):
0548:                 __tablename__ = "employee"
0549: 
0550:                 id: Mapped[int] = mapped_column(primary_key=True)
0551:                 discriminator: Mapped[str] = mapped_column(String(50))
0552: 
0553:                 __mapper_args__ = {
0554:                     "polymorphic_on": discriminator,
0555:                     "polymorphic_identity": "employee",
0556:                 }
0557: 
0558:           It may also be specified
0559:           as a SQL expression, as in this example where we
0560:           use the :func:`.case` construct to provide a conditional
0561:           approach::
0562: 
0563:             class Employee(Base):
0564:                 __tablename__ = "employee"
0565: 
0566:                 id: Mapped[int] = mapped_column(primary_key=True)
0567:                 discriminator: Mapped[str] = mapped_column(String(50))
0568: 
0569:                 __mapper_args__ = {
0570:                     "polymorphic_on": case(
0571:                         (discriminator == "EN", "engineer"),
0572:                         (discriminator == "MA", "manager"),
0573:                         else_="employee",
0574:                     ),
0575:                     "polymorphic_identity": "employee",
0576:                 }
0577: 
0578:           It may also refer to any attribute using its string name,
0579:           which is of particular use when using annotated column
0580:           configurations::
0581: 
0582:                 class Employee(Base):
0583:                     __tablename__ = "employee"
0584: 
0585:                     id: Mapped[int] = mapped_column(primary_key=True)
0586:                     discriminator: Mapped[str]
0587: 
0588:                     __mapper_args__ = {
0589:                         "polymorphic_on": "discriminator",
0590:                         "polymorphic_identity": "employee",
0591:                     }
0592: 
0593:           When setting ``polymorphic_on`` to reference an
```

Column hints:
- none detected


#### Extracted block 6: context `None` lines 519-609

```python
0519: 
0520:           * "'inline'" - specifies this class should be part of
0521:             the "with_polymorphic" mappers, e.g. its columns will be included
0522:             in a SELECT query against the base.
0523: 
0524:           * "'selectin'" - specifies that when instances of this class
0525:             are loaded, an additional SELECT will be emitted to retrieve
0526:             the columns specific to this subclass.  The SELECT uses
0527:             IN to fetch multiple subclasses at once.
0528: 
0529:          .. versionadded:: 1.2
0530: 
0531:          .. seealso::
0532: 
0533:             :ref:`with_polymorphic_mapper_config`
0534: 
0535:             :ref:`polymorphic_selectin`
0536: 
0537:         :param polymorphic_on: Specifies the column, attribute, or
0538:           SQL expression used to determine the target class for an
0539:           incoming row, when inheriting classes are present.
0540: 
0541:           May be specified as a string attribute name, or as a SQL
0542:           expression such as a :class:`_schema.Column` or in a Declarative
0543:           mapping a :func:`_orm.mapped_column` object.  It is typically
0544:           expected that the SQL expression corresponds to a column in the
0545:           base-most mapped :class:`.Table`::
0546: 
0547:             class Employee(Base):
0548:                 __tablename__ = "employee"
0549: 
0550:                 id: Mapped[int] = mapped_column(primary_key=True)
0551:                 discriminator: Mapped[str] = mapped_column(String(50))
0552: 
0553:                 __mapper_args__ = {
0554:                     "polymorphic_on": discriminator,
0555:                     "polymorphic_identity": "employee",
0556:                 }
0557: 
0558:           It may also be specified
0559:           as a SQL expression, as in this example where we
0560:           use the :func:`.case` construct to provide a conditional
0561:           approach::
0562: 
0563:             class Employee(Base):
0564:                 __tablename__ = "employee"
0565: 
0566:                 id: Mapped[int] = mapped_column(primary_key=True)
0567:                 discriminator: Mapped[str] = mapped_column(String(50))
0568: 
0569:                 __mapper_args__ = {
0570:                     "polymorphic_on": case(
0571:                         (discriminator == "EN", "engineer"),
0572:                         (discriminator == "MA", "manager"),
0573:                         else_="employee",
0574:                     ),
0575:                     "polymorphic_identity": "employee",
0576:                 }
0577: 
0578:           It may also refer to any attribute using its string name,
0579:           which is of particular use when using annotated column
0580:           configurations::
0581: 
0582:                 class Employee(Base):
0583:                     __tablename__ = "employee"
0584: 
0585:                     id: Mapped[int] = mapped_column(primary_key=True)
0586:                     discriminator: Mapped[str]
0587: 
0588:                     __mapper_args__ = {
0589:                         "polymorphic_on": "discriminator",
0590:                         "polymorphic_identity": "employee",
0591:                     }
0592: 
0593:           When setting ``polymorphic_on`` to reference an
0594:           attribute or expression that's not present in the
0595:           locally mapped :class:`_schema.Table`, yet the value
0596:           of the discriminator should be persisted to the database,
0597:           the value of the
0598:           discriminator is not automatically set on new
0599:           instances; this must be handled by the user,
0600:           either through manual means or via event listeners.
0601:           A typical approach to establishing such a listener
0602:           looks like::
0603: 
0604:                 from sqlalchemy import event
0605:                 from sqlalchemy.orm import object_mapper
0606: 
0607: 
0608:                 @event.listens_for(Employee, "init", propagate=True)
0609:                 def set_identity(instance, *arg, **kw):
```

Column hints:
- none detected


#### Extracted block 7: context `None` lines 538-628

```python
0538:           SQL expression used to determine the target class for an
0539:           incoming row, when inheriting classes are present.
0540: 
0541:           May be specified as a string attribute name, or as a SQL
0542:           expression such as a :class:`_schema.Column` or in a Declarative
0543:           mapping a :func:`_orm.mapped_column` object.  It is typically
0544:           expected that the SQL expression corresponds to a column in the
0545:           base-most mapped :class:`.Table`::
0546: 
0547:             class Employee(Base):
0548:                 __tablename__ = "employee"
0549: 
0550:                 id: Mapped[int] = mapped_column(primary_key=True)
0551:                 discriminator: Mapped[str] = mapped_column(String(50))
0552: 
0553:                 __mapper_args__ = {
0554:                     "polymorphic_on": discriminator,
0555:                     "polymorphic_identity": "employee",
0556:                 }
0557: 
0558:           It may also be specified
0559:           as a SQL expression, as in this example where we
0560:           use the :func:`.case` construct to provide a conditional
0561:           approach::
0562: 
0563:             class Employee(Base):
0564:                 __tablename__ = "employee"
0565: 
0566:                 id: Mapped[int] = mapped_column(primary_key=True)
0567:                 discriminator: Mapped[str] = mapped_column(String(50))
0568: 
0569:                 __mapper_args__ = {
0570:                     "polymorphic_on": case(
0571:                         (discriminator == "EN", "engineer"),
0572:                         (discriminator == "MA", "manager"),
0573:                         else_="employee",
0574:                     ),
0575:                     "polymorphic_identity": "employee",
0576:                 }
0577: 
0578:           It may also refer to any attribute using its string name,
0579:           which is of particular use when using annotated column
0580:           configurations::
0581: 
0582:                 class Employee(Base):
0583:                     __tablename__ = "employee"
0584: 
0585:                     id: Mapped[int] = mapped_column(primary_key=True)
0586:                     discriminator: Mapped[str]
0587: 
0588:                     __mapper_args__ = {
0589:                         "polymorphic_on": "discriminator",
0590:                         "polymorphic_identity": "employee",
0591:                     }
0592: 
0593:           When setting ``polymorphic_on`` to reference an
0594:           attribute or expression that's not present in the
0595:           locally mapped :class:`_schema.Table`, yet the value
0596:           of the discriminator should be persisted to the database,
0597:           the value of the
0598:           discriminator is not automatically set on new
0599:           instances; this must be handled by the user,
0600:           either through manual means or via event listeners.
0601:           A typical approach to establishing such a listener
0602:           looks like::
0603: 
0604:                 from sqlalchemy import event
0605:                 from sqlalchemy.orm import object_mapper
0606: 
0607: 
0608:                 @event.listens_for(Employee, "init", propagate=True)
0609:                 def set_identity(instance, *arg, **kw):
0610:                     mapper = object_mapper(instance)
0611:                     instance.discriminator = mapper.polymorphic_identity
0612: 
0613:           Where above, we assign the value of ``polymorphic_identity``
0614:           for the mapped class to the ``discriminator`` attribute,
0615:           thus persisting the value to the ``discriminator`` column
0616:           in the database.
0617: 
0618:           .. warning::
0619: 
0620:              Currently, **only one discriminator column may be set**, typically
0621:              on the base-most class in the hierarchy. "Cascading" polymorphic
0622:              columns are not yet supported.
0623: 
0624:           .. seealso::
0625: 
0626:             :ref:`inheritance_toplevel`
0627: 
0628:         :param polymorphic_identity: Specifies the value which
```

Column hints:
- none detected
