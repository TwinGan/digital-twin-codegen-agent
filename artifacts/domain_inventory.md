# Domain Knowledge Extraction

## Overview
The analysis is based on two documents:
- **Historical Market Data PRD** (full functional specification, including module descriptions, data sources, validation rules, job orchestration, error handling, and access options).
- **Market Data API Documentation** (two REST endpoints for triggering PCAP export and validation jobs).

The domain focuses on a pipeline that downloads, validates, and distributes binary historical tick data (PCAP) from an exchange’s network feeds, primarily for quantitative back-testing and strategy development.

---

## Domain Entities

| Entity              | Description | Source |
|---------------------|-------------|--------|
| **Feed**            | A logical channel from which market data is captured. Defined as A Feed and B Feed for redundancy. Each has a specific Corvil channel name (e.g., `v4-DC1-AFEED-LMENet-Inside`, `v4-DC1-BFEED-LMENet-Inside`). | PRD §4.2 (Data source module), API |
| **Message Code**    | Identifier for a subset of messages within a feed. L2 data uses `FEED_A_CORE_L2_DC1` / `FEED_B_CORE_L2_DC1`, L3 uses `FEED_A_CORE_L3_DC1` / `FEED_B_CORE_L3_DC1`. | PRD §4.2 (Data source module) |
| **Business Day**    | A trading day, defined as any weekday that is not a UK public holiday. The holiday calendar is maintained manually and differs year to year. | PRD §4.2 (Data source module) |
| **PCAP Dataset**    | A raw packet capture file retrieved from the Corvil platform, containing market data for one business day, for a specific feed and message code. | PRD §1.2, §4.2 |
| **PCAP File**       | The downloaded artifact, named according to convention `LMEFTCAD_yyyymmdd.zip` (e.g., “CA” = metal abbreviation). | PRD §4.2 (Job execution module) |
| **Validation Result** | The outcome of multi-level checks on a PCAP file: file-level (size), protocol-level (Ethernet, VLAN, IP, UDP), packet-level (size, payload, message type distribution, market state events). | PRD §4.2 (Data validation module) |
| **Market State Event** | A specific message type within the PCAP used to derive contract-level trading state transitions (e.g., opening, continuous, closing). These are extracted and stored for dashboard visualisation. | PRD §4.2 (Data validation module, Data Observability Module) |
| **Job**             | A scheduled or on-demand execution of a processing step: download, validate, upload, archive/purge. Triggered via cron or HTTP API. | PRD §4.2 (Job execution module), API |
| **Storage Layer**   | PV (Persistent Volume) for PCAP files; internal database for metadata (e.g., trading states, job records). | PRD §4.2 (Data storage module, Job execution module) |
| **Grafana Dashboard** | Visualises trading state metrics, market state transitions, and pipeline health. | PRD §4.2 (Data Observability Module) |
| **Notification**    | Email alerts sent to technical or business teams for failures (download, validation, upload, other exceptions). | PRD §4.2 (Data Notification Module) |

---

## Commands / User Actions

### External End-User
1. **Purchase Data** – Register/log in to LME Data Services (managed by DataBP), select datasets, pay, and receive access credentials to HKEX Data Marketplace (preferred) or create an SFTP account (rejected).  
   _Source: PRD §7 (Information Architecture)_

2. **Download Data** – From the marketplace or SFTP, end-user downloads the provided daily PCAP files.  
   _Source: PRD §7, §5.2 (Usability)_

### Internal Operations / Automation
3. **Trigger PCAP Export Job** – `GET /pcap/export?feed={feed}&messageCodes={codes}&businessDay={day}`. Returns 200 (job triggered) or 500.  
   _Source: API docs_

4. **Trigger Validation Job** – `GET /pcap/validation?feed={feed}&businessDay={day}`. (messageCodes parameter not used). Returns 200 or 500.  
   _Source: API docs_

5. **Cron-driven Download Task** – Scheduled to run after the business day ends (next day) to retrieve PCAP data from Corvil for A/B feeds and L2/L3 codes.  
   _Source: PRD §4.2 (Job execution module)_

6. **Cron-driven Validation Task** – Runs after download completes (max 1 hour delay).  
   _Source: PRD §4.2 (Job execution module)_

7. **Cron-driven Upload Task** – Runs after successful validation to transfer files to the distribution platform.  
   _Source: PRD §4.2 (Job execution module)_

8. **Cron-driven Archive/Purge Task** – Manages lifecycle of PCAP files on PV storage (once a day).  
   _Source: PRD §4.2 (Job execution module)_

---

## System Events / Outputs

- **Job Triggered** – HTTP 200 (null body).  
- **Job Failed** – HTTP 500.  
- **Download Failure Alert** – Email to tech team.  
- **Validation Failure Alerts**  
  - Empty file on public holiday → normal (no alert).  
  - Empty file on non-holiday → exception, email to business team.  
  - PCAP file validation failure → email to tech team.  
- **Upload Failure Alert** – Email to tech team.  
- **Other Exception Alerts** – Email to tech team.  
- **Grafana Dashboard Updates** – Reflects trading state aggregates, contract-level state transitions, pipeline health. (Observability module)  
- **Market State Events Recorded** – Stored in internal DB for chart generation.  

---

## Entity States (Inferred from Document Intent)

| Entity        | States / Condition                                          | Source / Assumption |
|---------------|-------------------------------------------------------------|---------------------|
| **PCAP File** | `not_downloaded`, `downloaded`, `validated`, `uploaded`, `archived` (implicit lifecycle from pipeline steps) | PRD module dependencies |
| **Job**       | `triggered` (API returns 200), `running`, `succeeded`, `failed` (inferred from email alerts and dependency chain) | API & Notification module |
| **Validation**| `pass` or `fail` (with subtypes: `file_level_fail`, `protocol_fail`, `packet_fail`, `empty_on_holiday`, `empty_on_nonholiday`) | PRD validation & notification modules |
| **Feed**      | `available` / `unavailable` (implied by dependency on upstream Corvil) | PRD §5.1 |

_Note: The PRD does not explicitly define state machines; these are extrapolated from the described processing order and error handling._

---

## State Transitions (Sequential Pipeline)

1. `not_downloaded → downloaded` after successful cron HTTP API call to Corvil or manual export trigger.  
2. `downloaded → validated_pass` after validation task succeeds (file-level, protocol, packet checks pass).  
3. `downloaded → validated_fail` if any check fails → email alert.  
4. `validated_pass → uploaded` after upload task succeeds.  
5. `uploaded → archived` after archiver/purge task moves file to archive storage.  
6. Any step may transition to a failed job state requiring operator intervention.

**Dependency chain**: Data Upload depends on Validation success; Validation depends on Download completion; Download depends on upstream data availability.  
_Source: PRD §4.4 (Dependencies)_

---

## Validation Rules

All rules apply to each PCAP file after download.

| Level            | Rule                                                                 | Source |
|------------------|----------------------------------------------------------------------|--------|
| **File-level**   | PCAP file size must fall within an “expected operational range” (exact boundaries not given). | PRD §4.2 |
| **Protocol-level** | Ethernet header must be present and compliant.                    | PRD §4.2 |
|                  | VLAN tagging must be valid according to network specification.       | PRD §4.2 |
|                  | IPv4 header must be well-formed.                                     | PRD §4.2 |
|                  | UDP protocol structure must be correct.                              | PRD §4.2 |
| **Packet-level** | Packet size must be consistent with expected length.                 | PRD §4.2 |
|                  | Message payload integrity must pass checksum or other verification.  | PRD §4.2 |
|                  | MessageType distribution within the file must be analysed (no specific thresholds given). | PRD §4.2 |
|                  | Market State Message Types must be identifiable (to derive trading states). | PRD §4.2 |
| **Empty file**   | On public holidays → treated as normal (no error).                   | PRD §4.2 (Notification) |
|                  | On non-holidays → exception → alert to business team.                | PRD §4.2 (Notification) |

---

## Error Cases

| Error                                 | Consequence                                                   | Who is alerted    | Source |
|---------------------------------------|---------------------------------------------------------------|-------------------|--------|
| Download job failure                  | Email to tech team for investigation.                         | Technical team    | PRD §4.2 (Notification) |
| Validation failure – PCAP file invalid| Email to tech team for troubleshooting.                       | Technical team    | PRD §4.2 |
| Validation failure – empty file on non-holiday | Email to business team to verify expectations.         | Business team     | PRD §4.2 |
| Validation failure – empty file on holiday | No alert (considered normal).                              | None              | PRD §4.2 |
| Upload failure                        | Email to tech team for issue investigation.                   | Technical team    | PRD §4.2 |
| Other exceptions                      | Email to tech team for issue investigation.                   | Technical team    | PRD §4.2 |
| API call fails                        | HTTP 500; no specific body returned.                          | Caller            | API docs |

---

## Invariants

1. **Download time window** – All data retrieved from Corvil corresponds to UK Time `[00:00:00 – 23:59:59]` of the specified business day.  
2. **Download scheduling** – The cron download job must start on the **next calendar day** after the business day, never on the same day.  
3. **Feed and code existence** – Only two feeds (A/B) and four message codes (L2_A, L3_A, L2_B, L3_B) are valid; downloads must be per feed and per code.  
4. **File naming** – Every delivered file must follow `LMEFTCAD_yyyymmdd.zip` (with metal abbreviation).  
5. **Pipeline order** – Validation cannot proceed before download; upload cannot proceed before validation.  
6. **Upstream dependency** – All data originates from the Corvil platform; no alternative source is defined.  
7. **Business day definition** – A business day is any weekday that is not a UK public holiday, maintained manually.  
8. **PCAP consistency** – The API download result must be identical to what the Corvil web interface would produce.  
9. **Alert sensitivity** – Empty files on holidays are not treated as errors; only non-holiday empties are exceptions.  

---

## Example Scenarios

### Scenario 1: Regular daily processing
- **Given** 2026-05-13 is a weekday (Wednesday) and not a UK holiday.  
- **When** the next day (14th) the cron download job runs for feed A, L2 code.  
- **Then** a PCAP file is downloaded from `10.140.13.107` channel `v4-DC1-AFEED-LMENet-Inside` with multicast group `224.0.240.13`.  
- **And** the file is saved as, e.g., `LMEFTcad_20260513.zip`.  
- **And** validation passes (file size, headers, packet checks, market state events found).  
- **And** the file is uploaded to the HKEX Data Marketplace.  
- **And** Grafana updates with trading state transitions for that day.

### Scenario 2: Public holiday empty file
- **Given** 2026-12-25 is a UK public holiday.  
- **When** the download job runs on 2026-12-26.  
- **Then** the retrieved PCAP file is empty.  
- **And** validation sees empty file and holiday → no alert.  
- **And** the pipeline marks the day as processed (no data record generated).

### Scenario 3: Non-holiday empty file
- **Given** 2026-07-15 is a regular business day.  
- **When** the download job runs on 2026-07-16 but the file is empty.  
- **Then** validation marks it as exception → email sent to business team: “please verify whether the result meets expectations”.  
- **And** the file is not uploaded.

### Scenario 4: Manual API export trigger
- **Given** an internal user (e.g., Temper team) calls `GET /pcap/export?feed=LME-A-realtime&messageCodes=LME_A_TEST1&businessDay=20260413`.  
- **When** the call reaches the service.  
- **Then** HTTP 200 (null) is returned, and the download job is queued.  
- **If** the job fails internally, later alerts are sent per the notification rules.

---

## Open Questions / Assumptions

1. **Feed Parameter Mapping** – The API uses feed names like `LME-A-realtime`, while the PRD defines Corvil channels as `v4-DC1-AFEED-LMENet-Inside`. The exact mapping is not documented.  
2. **messageCodes Parameter in Validation API** – Stated as “not currently used in logic”; future use is undefined.  
3. **Validation Thresholds** – “Expected operational range” for file size and MessageType distribution criteria are not quantified – these are likely empirical and require operational data.  
4. **Manual Holiday Calendar** – How the business day list is “maintained manually” (configuration file, database entry) is not described.  
5. **Data Upload Platform** – Marked “TBC”; could be HKEX Data Marketplace or third-party. Final integration details pending.  
6. **Email Templates** – Marked as “TBC”; exact content and thresholds for trigger are not defined.  
7. **Grafana Charts** – Final prototype for “trading state dashboards” is TBC; no specific metrics or visualisation details given.  
8. **Data Record Module** – Mentioned as P1 priority but no functional description; likely stores job metadata and market state events, but not fully specified.  
9. **Job State Machine** – The PRD does not provide explicit states for jobs (e.g., queued, running, success, failure). The API suggests asynchronous triggering; states above are inferred from sequential dependencies and alerts.  
10. **Security Profiles** – Only a high-level statement that InfoSec will assess before production; no concrete rules yet.  

---

## Summary
The extracted domain knowledge is fully drawn from the provided documents. It covers the complete data pipeline, validation logic, notification flows, API contracts, and business day conventions. Several operational details remain incomplete (marked as TBC in the PRD) and are flagged as open questions. No entities, states, or rules have been added beyond what the documents explicitly state or directly imply through dependency chains and error handling descriptions.