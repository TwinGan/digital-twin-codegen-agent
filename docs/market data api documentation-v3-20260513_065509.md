market data api documentation

CPT QA Knowledge Base

Exported on 2026-05-13 06:55:09

# Table of Contents {#table-of-contents .TOC-Heading}

1 background [3](#background)

2 api [4](#api)

2.1 Request Parameters [4](#request-parameters)

2.2 Response [4](#response)

2.3 Example [4](#example)

2.4 Request Parameters [4](#request-parameters-1)

2.5 Response [4](#response-1)

2.6 Example [5](#example-1)

# background

In preparation for the Hackathon project, the Temper team wants to
create a simulation based on market data. Therefore, they would
appreciate the availability of corresponding API documentation.

# api

1.  GET http://localhost:8080/pcap/export

## Request Parameters

  ---------------------------------------------------------------------------
  Parameter      Type     Required   Description
  -------------- -------- ---------- ----------------------------------------
  feed           String   Yes        Feed name (e.g. LME-A-realtime)

  messageCodes   String   No         Comma-separated message codes

  businessDay    String   No         Business day (format depends on backend)
  ---------------------------------------------------------------------------

## Response

  -----------------------------------------------------------------------
  Status      Description
  ----------- -----------------------------------------------------------
  200 OK      Job triggered successfully (returns null)

  500         Job failed
  -----------------------------------------------------------------------

## Example

+-------------------------------------------------------------------------+
| > GET                                                                   |
| > /pcap/export?feed=LME-A-realtime&messageCodes=LME_A_TEST1,LME_A_TEST2 |
+=========================================================================+

2\. GET
[http://localhost:8080/pcap/validation](http://localhost:8080/pcap/export)

## Request Parameters

  -------------------------------------------------------------------------
  Parameter           Type     Required     Description
  ------------------- -------- ------------ -------------------------------
  feed                String   Yes          Feed name

  messageCodes        String   No           Not currently used in logic

  businessDay         String   No           Business day
  -------------------------------------------------------------------------

## Response

  -----------------------------------------------------------------------
  Status      Description
  ----------- -----------------------------------------------------------
  200 OK      Job triggered successfully (null returned)

  500         Validation job failed
  -----------------------------------------------------------------------

## Example 

+----------------------------------------------------------------------+
| > GET /pcap/validation?feed=LME-A-realtime&businessDay=20260413      |
+======================================================================+
