Historical market data PRD

CPT QA Knowledge Base

Exported on 2026-05-13 06:56:44

# Table of Contents {#table-of-contents .TOC-Heading}

1 [3](#section)

2 Document Overview [4](#document-overview)

2.1 1.1 Product Name [4](#product-name)

2.2 1.2 Purpose [4](#purpose)

2.3 1.3 Background [4](#background)

2.4 1.4 Target Audience [4](#target-audience)

2.5 1.5 Version & Update Record [4](#version-update-record)

3 Product Positioning [5](#product-positioning)

3.1 2.1 Core Value [5](#core-value)

3.2 2.2 Product Positioning [5](#product-positioning-1)

3.3 2.3 Business Objectives [5](#business-objectives)

4 User & Scenarios [6](#user-scenarios)

4.1 3.1 User Persona [6](#user-persona)

4.2 3.2 Core User Scenarios [6](#core-user-scenarios)

4.3 3.3 Edge Scenarios [6](#edge-scenarios)

5 Functional Requirements [7](#functional-requirements)

5.1 4.1 Functional Module Division [7](#functional-module-division)

5.2 4.2 Detailed Functional Description
[7](#detailed-functional-description)

5.2.1 Data source module [7](#data-source-module)

5.2.2 Data validation module [9](#data-validation-module)

5.2.3 Data upload module [9](#data-upload-module)

5.2.4 Job execution module [9](#job-execution-module)

5.2.5 Data storage module [10](#data-storage-module)

5.2.6 Data Observability Module [10](#data-observability-module)

5.2.7 Data Notification Module [10](#data-notification-module)

5.3 4.3 Priority of Functions [11](#priority-of-functions)

5.4 4.4 Dependencies Between Functions
[11](#dependencies-between-functions)

6 Non-Functional Requirements [12](#non-functional-requirements)

6.1 5.1 Performance Requirements [12](#performance-requirements)

6.2 5.2 Usability Requirements [12](#usability-requirements)

6.3 5.3 Security Requirements [12](#security-requirements)

6.4 5.4 Compatibility Requirements [12](#compatibility-requirements)

7 Information Architecture [13](#information-architecture)

8 Milestone & Deliverables [14](#milestone-deliverables)

9 Appendix [15](#appendix)

# 

- [Document Overview](#document-overview)

  - [1.1 Product Name](#product-name)

  - [1.2 Purpose](#purpose)

  - [1.3 Background](#background)

  - [1.4 Target Audience](#target-audience)

  - [1.5 Version & Update Record](#version-update-record)

- [Product Positioning](#product-positioning)

  - [2.1 Core Value](#core-value)

  - [2.2 Product Positioning](#product-positioning-1)

  - [2.3 Business Objectives](#business-objectives)

- [User & Scenarios](#user-scenarios)

  - [3.1 User Persona](#user-persona)

  - [3.2 Core User Scenarios](#core-user-scenarios)

  - [3.3 Edge Scenarios](#edge-scenarios)

- [Functional Requirements](#functional-requirements)

  - [4.1 Functional Module Division](#functional-module-division)

  - [4.2 Detailed Functional
    Description](#detailed-functional-description)

  - [4.3 Priority of Functions](#priority-of-functions)

  - [4.4 Dependencies Between
    Functions](#dependencies-between-functions)

- [Non-Functional Requirements](#non-functional-requirements)

  - [5.1 Performance Requirements](#performance-requirements)

  - [5.2 Usability Requirements](#usability-requirements)

  - [5.3 Security Requirements](#security-requirements)

  - [5.4 Compatibility Requirements](#compatibility-requirements)

- [Information Architecture](#information-architecture)

- [Milestone & Deliverables](#milestone-deliverables)

- [Appendix](#appendix)

# Document Overview

## 1.1 Product Name 

historical market data 

## 1.2 Purpose 

Based on the proposed historical market data product framework, this
document aims to formalize the technical specifications and delivery
standards of the product features to support alignment with business
stakeholders and to guide subsequent development, testing, and
client-facing implementation. 

## 1.3 Background 

At present, the LME historical market data delivery
process remains request-based, with data typically extracted and
provided in spreadsheet format by business teams. Additionally, market
participants seeking tick data -- whether market‑by‑order (Level 3) or
market‑depth data (Level 2 with up to 15 levels of depth) -- can only
obtain it through the third‑party
distributor QuantHouse (formerly Iress), rather than directly from the
LME. Providing such datasets directly is considered a core capability
for modern exchanges. 

Another dataset that is gaining significant traction is PCAP (Packet
Capture), which delivers the full stream of network‑level data packets,
offering a highly granular view of all message traffic. 

This approach is increasingly unable to meet the evolving needs of
market participants, particularly given the non-binary structure of the
delivered data, which does not support algorithmic strategy back testing
or order-level execution modelling. 

To address this limitation, the proposed Historical Market Data product
will provide exchange-native binary datasets --- including Level 2 and
Level 3 order book information --- made available on a daily basis for
self-service download by clients, thereby enabling simulation-driven
quantitative research and execution strategy development. 

## 1.4 Target Audience 

Intended end users 

The primary end users of this product are external clients, with a
particular focus on algorithmic trading practitioners and quantitative
strategy developers. 

Document audience 

This document is intended for internal technical and business teams
involved in the development, validation, and operational delivery of the
Historical Market Data product. 

## 1.5 Version & Update Record 

V1-2026.3.10-Cecilia Luo 

#  Product Positioning

## 2.1 Core Value 

The proposed product addresses the current lack
of binary-formatted historical tick market data available directly from
the LME for professional client-side development, while
also establishing a new commercial data offering capable of generating
incremental revenue for the LME. 

## 2.2 Product Positioning 

The product will be delivered as a standalone, lightweight data
offering, enabling clients to independently access and integrate
historical market data into their downstream quantitative development
workflows. 

## 2.3 Business Objectives 

Financial benefits 

- The project will deliver several historical datasets, starting with
  PCAP, aiming to deliver all the initial datasets by end of 2026. These
  are estimated to contribute incremental revenue of US\$0.13m in 2027,
  increasing to US\$0.63m in 2030. 

<!-- -->

- The initial cost savings would start from 2026 when the LME starts
  being less reliant to QuantHouse, as the new datasets are created; it
  will be fully phased out from 2027. This would save US\$5,000 in 2026
  and US\$10,000 p.a. from 2027. 

<!-- -->

- Benefits will be tracked by the number of participants purchasing the
  datasets at a monthly basis. Initial feedback will also
  be monitored to ensure it meets customers' requirements. 

Non-financial benefits 

- This is a core capability provided by exchanges. Peer exchanges
  provide prospective clients with limited sets of historical tick data
  (usually three months) to support back testing and market evaluation.
  Establishing this capability would align the LME with industry
  standards and help attract new trading participants.  

<!-- -->

- Improved customer or user experience when the datasets are going to be
  uploaded in the data marketplace. Using a data marketplace would also
  enable the LME to tailor data offerings to different audiences and
  needs. 

#  User & Scenarios

## 3.1 User Persona 

Designed for latency-sensitive quantitative trading firms, \
  electronic execution strategy developers, and market microstructure
research teams requiring packet-level historical market replay for
strategy development and model training. 

## 3.2 Core User Scenarios 

Reconstruct exchange-native limit order book dynamics and simulate
order-level interaction with the matching engine to train
latency-sensitive execution models and queue-aware trading strategies. 

## 3.3 Edge Scenarios 

Historical PCAP data represents captured network-level dissemination of
market data and may not reflect deterministic matching engine state
without client-side reconstruction, latency modelling, and
venue-specific interaction logic. 

#  Functional Requirements

## 4.1 Functional Module Division 

 

![](media/image1.png){width="5.9006944444444445in"
height="3.2380118110236222in"}

data download module, data upload module(TBC), job execution module,
data storage module, data record module, data observabiliy module, data
notification module 

## 4.2 Detailed Functional Description 

### Data source module 

Download two types of PCAP data from Corvil platform via API.  The
file need to download by feed(A Feed and B Feed) and by message
code (L2/L3 message in  Feed A and  Feed B) 

+-----------+-----------------------------+----------------+-----------------+-------------+
| **Type**  | **Channel**                 | **Source IP**  | **Download time | **Remark**  |
|           |                             |                | window**        |             |
+-----------+-----------------------------+----------------+-----------------+-------------+
| **A       | A Feed:                     | 10.140.13.107  | UK Time         |             |
| Feed**    | v4-DC1-AFEED-LMENet-Inside  |                |                 |             |
|           |                             |                | \[00:00:00 --   |             |
|           |                             |                | 23:59:59\]      |             |
|           |                             |                |                 |             |
|           |                             |                | of business     |             |
|           |                             |                | day.            |             |
+-----------+-----------------------------+----------------+-----------------+-------------+
| **B       | B Feed: v4-DC1-             | 10.140.13.107  | UK Time         |             |
| Feed**    | BFEED-LMENet-Inside         |                |                 |             |
|           |                             |                | \[00:00:00 --   |             |
|           |                             |                | 23:59:59\]      |             |
|           |                             |                |                 |             |
|           |                             |                | of business     |             |
|           |                             |                | day.            |             |
+-----------+-----------------------------+----------------+-----------------+-------------+

Business day definition: skip UK holiday and weekend, maintain it
manually, different from each year. 

The final downloaded output must be consistent with the download result
produced via the web interface.  

 ![](media/image2.png){width="5.9006944444444445in"
height="3.1435444006999127in"}

Download by message code for L2 and L3 data 

+-----------+-------------------------------+---------------------+---------------+-------------+-------------+
| **Type**  | **Channel**                   | **Message Code**    | **Source      | **Download  | **Remark**  |
|           |                               |                     | IP**          | time        |             |
|           |                               |                     |               | window**    |             |
+-----------+-------------------------------+---------------------+---------------+-------------+-------------+
| L2 data   | A Feed:                       | FEED_A_CORE_L2_DC1  | 224.0.240.13  | UK Time     |             |
| in A      | v4-DC1-AFEED-LMENet-Inside    |                     |               |             |             |
| Feed      |                               |                     |               | \[00:00:00  |             |
|           |                               |                     |               | --          |             |
|           |                               |                     |               | 23:59:59\]  |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               | of business |             |
|           |                               |                     |               | day.        |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               |             |             |
+-----------+-------------------------------+---------------------+---------------+-------------+-------------+
| L3 data   | A Feed:                       | FEED_A_CORE_L3_DC1  | 224.0.240.15  | UK Time     |             |
| in A      | v4-DC1-AFEED-LMENet-Inside    |                     |               |             |             |
| Feed      |                               |                     |               | \[00:00:00  |             |
|           |                               |                     |               | --          |             |
|           |                               |                     |               | 23:59:59\]  |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               | of business |             |
|           |                               |                     |               | day.        |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               |             |             |
+-----------+-------------------------------+---------------------+---------------+-------------+-------------+
| L2 data   | B Feed: v4-DC1-               | FEED_B_CORE_L2_DC1  | 224.0.241.13  | UK Time     |             |
| in B      | BFEED-LMENet-Inside           |                     |               |             |             |
| Feed      |                               |                     |               | \[00:00:00  |             |
|           |                               |                     |               | --          |             |
|           |                               |                     |               | 23:59:59\]  |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               | of business |             |
|           |                               |                     |               | day.        |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               |             |             |
+-----------+-------------------------------+---------------------+---------------+-------------+-------------+
| L3 data   | B Feed: v4-DC1-               | FEED_B_CORE_L3_DC1  | 224.0.241.15  | UK Time     |             |
| in B      | BFEED-LMENet-Inside           |                     |               |             |             |
| Feed      |                               |                     |               | \[00:00:00  |             |
|           |                               |                     |               | --          |             |
|           |                               |                     |               | 23:59:59\]  |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               | of business |             |
|           |                               |                     |               | day.        |             |
|           |                               |                     |               |             |             |
|           |                               |                     |               |             |             |
+-----------+-------------------------------+---------------------+---------------+-------------+-------------+

All retrieved datasets are subject to downstream validation procedures
prior to further processing. 

### Data validation module 

Post-download validation is performed at multiple levels to ensure data
integrity and protocol consistency. 

#### File-Level Validation 

Verify PCAP file size falls within the expected operational range 

#### Protocol-Level Validation 

Validate network stack compliance, including: 

- Ethernet Header 

<!-- -->

- VLAN Tagging 

<!-- -->

- IPv4 Header 

<!-- -->

- UDP Protocol Structure 

#### Packet-Level Validation 

Packet-level inspection includes: 

- Packet size verification 

<!-- -->

- Message payload integrity check 

<!-- -->

- MessageType distribution analysis within each PCAP file 

<!-- -->

- Identification of **Market State Message Types** 

Detected market state events are used to derive contract-level trading
state transitions, which are subsequently recorded in the internal
database to support downstream analytics and visualization (e.g.,
trading state chart generation). 

### Data upload module 

Validated PCAP datasets stored are uploaded to a designated downstream
distribution platform *(TBC)* for client-facing access. 

### Job execution module 

Scheduled task execution is managed via **Cron-based job
orchestration**, supporting the following automated workflows: 

- **Data Download Task** \
    Periodic retrieval of PCAP datasets followed by validation(UK Time
  \[00:00:00 -- 23:59:59\] of business day, so the download job start
  time should be the next day, not the same day. )

<!-- -->

- **Data Archive / Purge Task** \
    Lifecycle management of PCAP files stored within the PV layer,
  including scheduled archival and data purge. (once a day)

- **Data Validate Task** \
    Daily validate PCAP datasets from PV storage  (once a day. After the
  download job finished(expect to leave maximum 1 hour for downloading
  file) )

<!-- -->

- **Data Upload Task** \
    Daily extraction of validated PCAP datasets and transfer to the
  designated client distribution platform  (once a day. After validate
  job finished)

- **Time taken for data to be received by end user**\
    The data will be provided by HKEX (or 3rd party data marketplace)
  and we will follow their requirements

- **File naming convention** 

> **LMEFTCAD_yyyymmdd.zip**
>
> -- LME: Prefix
>
> -- FT: Abbreviation for Full Tick
>
> -- CA: Abbreviation for the metal
>
> -- D: Daily file indicator
>
> -- yyyymmdd: day of the dataset

### Data storage module 

The **PV Layer** serves as the primary storage repository for validated
PCAP-format historical datasets. 

### Data Observability Module 

Operational monitoring and internal observability are supported
via **Grafana-based dashboards**, enabling: 

- Aggregation of trading state metrics across time intervals 

<!-- -->

- Visualization of contract-level market state transitions 

<!-- -->

- Monitoring of data processing pipeline health 

This facilitates real-time internal oversight of historical data
processing and delivery quality. 

TBC: the final deliverable graph/chart prototype?

### Data Notification Module 

 Download Failure Alert\
An email notification will be sent to the technical team for issue
investigation.

Validation Failure Alert

- Empty file

  - On public holidays: treated as a normal empty file

  - On non-holidays: treated as an exception\
    An email notification will be sent to the business team to promptly
    verify whether the result meets expectations.

- PCAP file validation failure\
  An email notification will be sent to the technical team for
  troubleshooting.

Upload Failure Alert\
An email notification will be sent to the technical team for issue
investigation.

Other Exception Alerts\
An email notification will be sent to the technical team for issue
investigation.

TBC: the email template and content need to be further discussed.

## 4.3 Priority of Functions 

  ------------------------------------------------------ ----------------
  functions                                              priority 

  Data source module                                     P0 

  Data download module                                   P0 

  Data validation module                                 P0 

  Data upload module                                     P0 

  Job execution module                                   P0 

  Data storage module                                    P0 

  Data record module                                     P1 

  Data observability module                              P1 
  ------------------------------------------------------ ----------------

  

## 4.4 Dependencies Between Functions 

The execution of individual processing modules follows a defined
dependency hierarchy as outlined below: 

- The **Data Upload Module** is dependent on the successful completion
  of the **Data Validation Module**. 

<!-- -->

- The **Data Validation Module** requires the prior execution of
  the **Data Download Module**. 

<!-- -->

- The **Data Download Module** is contingent upon the availability of
  upstream data sources. 

<!-- -->

- The **Data Record Module** relies on the normal operation of the **Job
  Execution Module** to capture and persist processing metadata. 

<!-- -->

- The **Data Observability Module** depends on the availability of
  persisted records generated by the **Data Record Module**. 

  

#  Non-Functional Requirements

## 5.1 Performance Requirements 

The availability of upstream market data is dependent on the Corvil
platform as the primary data source. 

Within the Historical Market Data processing pipeline, internal system
components are designed to maintain an availability target
of **99.99%**, excluding upstream data source outages beyond the
system's operational control. 

## 5.2 Usability Requirements 

Authorized users will be able to download historical market data on a
daily basis from the designated distribution platform.

The key business point of contacts from HKEX are Gallant Nien and Bing
Li. High level of their internal structure is the following:

![](media/image3.jpeg){width="5.9006944444444445in"
height="2.7162839020122487in"}

## 5.3 Security Requirements 

Prior to production deployment, the system will undergo a comprehensive
security assessment conducted by the Information Security (InfoSec)
function. 

## 5.4 Compatibility Requirements 

The download functionality does not impose specific requirements on
client-side infrastructure or device environments. 

#  Information Architecture

 

**Option 1: Access Data via the HKEX Portal** (**preferred** option)

1.  End-users would need to register/log-in to LME Data Services
    (managed by DataBP) 

2.  End-users would select the historical data they are interested in
    purchasing. 

3.  After payment has been received, the end-user is provided with a
    log-in for the HKEX Data Marketplace \[need to confirm what the
    relation of the end-user would be with HKEX\]  

4.  End-users can download the requested files through the marketplace 

**Option 2: Access Data via Secure SFTP** (**rejected** option as part
of Discovery)

1.  End-users would need to register/log-in to LME Data Services
    (managed by DataBP) 

2.  End-users would select the historical data they are interested in
    purchasing. 

3.  After payment has been received, the end-user is provided
    with access to the SFTP folder  

4.  End-users can download the requested files via SFTP 

**There may be also options to look at 3rd party data marketpalces.**

# Milestone & Deliverables

Business-driven requirement changes are subject to prior technical
feasibility validation, as scope adjustments may introduce potential
delays to the implementation timeline. 

In addition, any delays in platform-side decision-making or
communication related to the data upload and distribution infrastructure
may affect downstream integration milestones and pose a risk to
scheduled product delivery. 

+-----------+---------------------------------------------------------------+
| Timeline  | Task                                                          |
+-----------+---------------------------------------------------------------+
| By March  | 1.  PCAP file download& validation​​                            |
|           |                                                               |
|           | 2.  SOP and Tech design documentation​                         |
|           |                                                               |
|           | 3.  Setup OpenShift in testing environment                    |
+-----------+---------------------------------------------------------------+
| By April  | 1.  Cron Job for scheduled download and upload ​               |
|           |                                                               |
|           | 2.  DB storage for metadata management  ​                      |
|           |                                                               |
|           | 3.  PV storage for PCAP file  ​                                |
+-----------+---------------------------------------------------------------+
| By May    | 1.  Upload data to platform (subject to further               |
|           |     discussion with IOE team offering Data platform)​          |
|           |                                                               |
|           | 2.  Infosec & SIT & UAT                                       |
+-----------+---------------------------------------------------------------+
| By June   | 1.  Deploy on OpenShift in Prod environment​                   |
|           |                                                               |
|           | 2.  Live verification​                                         |
|           |                                                               |
|           | 3.  Sign off and go live                                      |
+-----------+---------------------------------------------------------------+
| By July   | 1.  Generate trading status dashboards and analytical charts  |
|           |     in Grafana ​                                               |
+-----------+---------------------------------------------------------------+

  

# Appendix

11.1 Related Documents 

11.2 Contact Information 

11.3 Other Notes 
